"""Paginated read-only facts; no contact fields or provider writes."""
from datetime import datetime, timezone
import httpx
from .errors import ApplicationError

PAGE = "pageInfo { hasNextPage endCursor }"
QUERIES = {
    "products": """query($after:String){products(first:100,after:$after){nodes{id title status
      variants(first:100){nodes{id title sku price inventoryQuantity} pageInfo{hasNextPage endCursor}}}
      pageInfo{hasNextPage endCursor}}}""",
    "customers": "query($after:String){customers(first:100,after:$after){nodes{id defaultAddress{city}} pageInfo{hasNextPage endCursor}}}",
    "orders": """query($after:String){orders(first:50,after:$after,sortKey:CREATED_AT){nodes{
      id createdAt updatedAt customer{id} displayFinancialStatus displayFulfillmentStatus
      totalPriceSet{shopMoney{amount currencyCode}}
      lineItems(first:100){nodes{id quantity variant{id}} pageInfo{hasNextPage endCursor}}
      fulfillments(first:250){ id deliveredAt fulfillmentLineItems(first:100){nodes{quantity lineItem{id}} pageInfo{hasNextPage endCursor}} }
      returns(first:100){nodes{id status} pageInfo{hasNextPage endCursor}}
      refunds{id refundLineItems(first:100){nodes{quantity lineItem{id}} pageInfo{hasNextPage endCursor}}}
    }pageInfo{hasNextPage endCursor}}}""",
}


async def read_facts(adapter):
    try:
        return await _read_facts(adapter)
    except httpx.TimeoutException:
        raise ApplicationError(504, "SOURCE_TIMEOUT", "Shopify facts timed out; existing evidence was retained.") from None
    except httpx.RequestError:
        raise ApplicationError(503, "SOURCE_UNAVAILABLE", "Shopify facts are temporarily unavailable.") from None
    except (KeyError, TypeError, ValueError):
        raise ApplicationError(502, "SOURCE_INVALID", "Shopify returned incomplete or invalid fact data.") from None


async def _read_facts(adapter):
    result = {"products": [], "customers": [], "orders": [], "notes": [], "complete": True,
              "checked_at": datetime.now(timezone.utc).isoformat(), "shop": adapter.shop}
    async with httpx.AsyncClient(timeout=30, transport=adapter.transport, follow_redirects=False) as client:
        token = await adapter.access_token(client)

        async def query(text, variables=None):
            response = await client.post(f"https://{adapter.shop}/admin/api/{adapter.version}/graphql.json",
                headers={"X-Shopify-Access-Token": token}, json={"query": text, "variables": variables or {}})
            if response.status_code != 200:
                raise ApplicationError(503, "SOURCE_UNAVAILABLE", "Shopify facts could not be read; retained facts are not refreshed.")
            data = response.json()
            # Existing access permits orders but denies returns. Preserve independent
            # order/delivery facts while explicitly blocking eligibility on unknown returns.
            errors = data.get("errors") or []
            if errors and 'defaultAddress{city}' in text and all('defaultAddress' in e.get('message','') or 'city' in e.get('message','') for e in errors):
                note='Customer city is unavailable under existing Shopify access. City remains unknown; no location is inferred.'
                if note not in result['notes']:result['notes'].append(note)
                return await query(text.replace('defaultAddress{city}',''),variables)
            return_selection = "returns(first:100){nodes{id status} pageInfo{hasNextPage endCursor}}"
            if errors and return_selection in text and all(e.get("message") == "Access denied for returns field." for e in errors):
                result["complete"] = False
                note = "Return facts are unavailable under existing Shopify access; eligibility remains blocked."
                if note not in result["notes"]: result["notes"].append(note)
                partial = await query(text.replace(return_selection, ""), variables)
                for order in partial["orders"]["nodes"]:
                    order["returns"] = {"nodes": [], "pageInfo": {"hasNextPage": False}, "verified": False}
                return partial
            if data.get("errors") or not data.get("data"):
                raise ApplicationError(422, "FACT_ACCESS_BLOCKED", "Required Shopify fields are unavailable. Review existing access; no permissions were changed.")
            return data["data"]

        async def pages(text, field, variables=None, node=False):
            rows, after, seen = [], None, set()
            for _ in range(100):
                data = await query(text, {**(variables or {}), "after": after})
                section = (data.get("node") or {}).get(field) if node else data.get(field)
                if not section or "nodes" not in section or "pageInfo" not in section:
                    raise ApplicationError(422, "COVERAGE_UNKNOWN", "Source pagination coverage could not be confirmed.")
                rows.extend(section["nodes"])
                info = section["pageInfo"]
                if not info["hasNextPage"]:
                    return rows
                after = info.get("endCursor")
                if not after or after in seen:
                    raise ApplicationError(422, "CURSOR_INVALID", "Source returned an invalid pagination cursor.")
                seen.add(after)
            raise ApplicationError(422, "SYNC_LIMIT", "Source scan exceeds the bounded sync limit; coverage is incomplete.")

        meta = await query("{shop{myshopifyDomain currencyCode} currentAppInstallation{accessScopes{handle}}}")
        if meta["shop"]["myshopifyDomain"] != adapter.shop:
            raise ApplicationError(409, "ACCOUNT_MISMATCH", "Source account does not match this connector.")
        result["currency"] = meta["shop"]["currencyCode"]
        scopes = {s["handle"] for s in meta["currentAppInstallation"]["accessScopes"]}
        if "read_all_orders" not in scopes:
            result["notes"].append("Order access is limited to Shopify's permitted history window; older history is unverified.")
            result["complete"] = False
        for field, text in QUERIES.items():
            result[field] = await pages(text, field)
        for product in result["products"]:
            if product["variants"]["pageInfo"]["hasNextPage"]:
                product["variants"]["nodes"] = await pages("query($id:ID!,$after:String){node(id:$id){...on Product{variants(first:100,after:$after){nodes{id title sku price inventoryQuantity}"+PAGE+"}}}}", "variants", {"id": product["id"]}, True)
        for order in result["orders"]:
            if len(order["fulfillments"]) >= 250:
                raise ApplicationError(422, "FULFILLMENT_COVERAGE", "Fulfillment coverage exceeds the bounded read limit.")
            if order["lineItems"]["pageInfo"]["hasNextPage"]:
                order["lineItems"]["nodes"] = await pages("query($id:ID!,$after:String){node(id:$id){...on Order{lineItems(first:100,after:$after){nodes{id quantity variant{id}}"+PAGE+"}}}}", "lineItems", {"id": order["id"]}, True)
            for field, typename, selection in (("returns", "Order", "id status"),):
                if order[field]["pageInfo"]["hasNextPage"]:
                    order[field]["nodes"] = await pages("query($id:ID!,$after:String){node(id:$id){...on "+typename+"{"+field+"(first:100,after:$after){nodes{"+selection+"}"+PAGE+"}}}}", field, {"id":order["id"]}, True)
            for field, typename, items in (("fulfillmentLineItems", "Fulfillment", order["fulfillments"]),
                                           ("refundLineItems", "Refund", order["refunds"])):
                for item in items:
                    if item[field]["pageInfo"]["hasNextPage"]:
                        item[field]["nodes"] = await pages("query($id:ID!,$after:String){node(id:$id){...on "+typename+"{"+field+"(first:100,after:$after){nodes{quantity lineItem{id}}"+PAGE+"}}}}", field, {"id":item["id"]}, True)
        return result
