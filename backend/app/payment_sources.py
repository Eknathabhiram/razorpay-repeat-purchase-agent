"""Read-only test payment sources. No capture/refund/order-creation API."""
import hashlib
import os
import re
from datetime import datetime,timezone
import httpx
from .errors import ApplicationError


class RazorpayReadOnly:
    def __init__(self,key=None,secret=None,transport=None):
        self.key=key if key is not None else os.getenv("RAZORPAY_KEY_ID","")
        self.secret=secret if secret is not None else os.getenv("RAZORPAY_KEY_SECRET","")
        self.transport=transport
        self.account_ref="test-key:"+hashlib.sha256(self.key.encode()).hexdigest()[:24]

    async def snapshot(self):
        if not self.key.startswith("rzp_test_") or not self.secret:
            raise ApplicationError(422,"TEST_KEYS_REQUIRED","Configured test credentials are required; live keys are rejected.")
        try:
            async with httpx.AsyncClient(timeout=20,auth=(self.key,self.secret),transport=self.transport,follow_redirects=False) as client:
                async def get(path,params=None):
                    if not re.fullmatch(r"/(payments|orders|refunds)(/[A-Za-z0-9_]+)?",path):
                        raise ApplicationError(422,"READ_PATH_INVALID","Unsupported payment read path.")
                    response=await client.get("https://api.razorpay.com/v1"+path,params=params)
                    if response.status_code!=200:raise ApplicationError(503,"PAYMENT_READ_FAILED","Test payment evidence could not be read.")
                    return response.json()
                async def pages(path):
                    rows=[];seen=set()
                    for offset in range(0,10000,100):
                        value=await get(path,{"count":100,"skip":offset})
                        batch=value.get("items")
                        if not isinstance(batch,list):raise ApplicationError(502,"PAYMENT_RESPONSE_INVALID","Payment collection coverage is unverified.")
                        for row in batch:
                            if row["id"] in seen:raise ApplicationError(422,"PAYMENT_PAGINATION_CHANGED","Collection changed during pagination. Refresh evidence.")
                            seen.add(row["id"])
                        rows.extend(batch)
                        if len(batch)<100:return rows
                    raise ApplicationError(422,"PAYMENT_SCAN_LIMIT","Payment scan exceeded its bounded coverage limit.")
                payments=await pages("/payments");orders={}
                for payment in payments:
                    identifier=payment.get("order_id")
                    if identifier and identifier not in orders:orders[identifier]=await get("/orders/"+identifier)
                refunds=await pages("/refunds")
                # Project only evidence fields; no contact/email/card/notes are persisted.
                return {"account_ref":self.account_ref,"checked_at":datetime.now(timezone.utc).isoformat(),
                    "payments":[{key:p.get(key) for key in ("id","order_id","amount","currency","status","captured","amount_refunded")} for p in payments],
                    "orders":{key:{field:row.get(field) for field in ("id","receipt","status","amount","amount_paid","currency")} for key,row in orders.items()},
                    "refunds":[{key:r.get(key) for key in ("id","payment_id","amount","currency","status")} for r in refunds]}
        except httpx.TimeoutException:raise ApplicationError(504,"PAYMENT_TIMEOUT","Test payment evidence timed out.") from None
        except (httpx.RequestError,ValueError,KeyError,TypeError):raise ApplicationError(502,"PAYMENT_RESPONSE_INVALID","Test payment evidence is unavailable or invalid.") from None


async def shopify_transactions(adapter):
    query="""query($after:String){shop{myshopifyDomain} orders(first:100,after:$after,sortKey:CREATED_AT){nodes{
      id test createdAt updatedAt customer{id} displayFinancialStatus displayFulfillmentStatus
      totalPriceSet{shopMoney{amount currencyCode}}
      transactions(first:100){id paymentId gateway kind status test amountSet{shopMoney{amount currencyCode}}}
    }pageInfo{hasNextPage endCursor}}}"""
    try:
        async with httpx.AsyncClient(timeout=30,transport=adapter.transport,follow_redirects=False) as client:
            token=await adapter.access_token(client);rows=[];after=None;seen=set()
            for _ in range(100):
                response=await client.post(f"https://{adapter.shop}/admin/api/{adapter.version}/graphql.json",headers={"X-Shopify-Access-Token":token},json={"query":query,"variables":{"after":after}})
                data=response.json()
                if response.status_code!=200 or data.get("errors"):raise ApplicationError(422,"TRANSACTION_READ_BLOCKED","Shopify transaction evidence is unavailable under existing access.")
                data=data["data"]
                if data["shop"]["myshopifyDomain"]!=adapter.shop:raise ApplicationError(409,"ACCOUNT_MISMATCH","Shopify evidence belongs to another store.")
                for order in data["orders"]["nodes"]:
                    if len(order["transactions"])>=100:raise ApplicationError(422,"TRANSACTION_COVERAGE","Transaction coverage exceeds the bounded read limit.")
                    rows.append(order)
                info=data["orders"]["pageInfo"]
                if not info["hasNextPage"]:return rows
                after=info["endCursor"]
                if not after or after in seen:raise ApplicationError(422,"CURSOR_INVALID","Transaction pagination could not be confirmed.")
                seen.add(after)
            raise ApplicationError(422,"TRANSACTION_SCAN_LIMIT","Transaction scan exceeded its bounded coverage limit.")
    except httpx.TimeoutException:raise ApplicationError(504,"TRANSACTION_TIMEOUT","Shopify transaction evidence timed out.") from None
    except (httpx.RequestError,KeyError,ValueError,TypeError):raise ApplicationError(502,"TRANSACTION_INVALID","Shopify returned invalid transaction evidence.") from None


class StorefrontCartAdapter:
    """Typed contract available for separately authorized Storefront capability."""
    def __init__(self,shop,version,token,transport=None,allow_creation=False):
        if not re.fullmatch(r"[a-z0-9-]+\.myshopify\.com",shop):raise ValueError("Invalid storefront domain")
        self.shop,self.version,self.token,self.transport,self.allow_creation=shop,version,token,transport,allow_creation

    async def verify(self):
        if not self.token:return {"available":False,"reason":"No Storefront token is configured."}
        async with httpx.AsyncClient(timeout=15,transport=self.transport,follow_redirects=False) as client:
            response=await client.post(f"https://{self.shop}/api/{self.version}/graphql.json",headers={"X-Shopify-Storefront-Access-Token":self.token},json={"query":"{shop{name}}"})
            return {"available":response.status_code==200 and not response.json().get("errors"),"reason":"Cart mutation permission and buyer context require separate verification."}

    async def prepare(self,variant_id,quantity,correlation):
        if not self.token or not self.allow_creation:raise ApplicationError(422,"STOREFRONT_UNVERIFIED","Storefront cart creation is not authorized/configured.")
        if not re.fullmatch(r"gid://shopify/ProductVariant/\d+",variant_id) or not 1<=quantity<=20:raise ApplicationError(422,"CART_SCOPE","An exact variant and bounded quantity are required.")
        query="""mutation($input:CartInput!){cartCreate(input:$input){cart{id checkoutUrl cost{totalAmount{amount currencyCode}} lines(first:20){nodes{quantity merchandise{...on ProductVariant{id}}}}} userErrors{field message}}}"""
        async with httpx.AsyncClient(timeout=15,transport=self.transport,follow_redirects=False) as client:
            response=await client.post(f"https://{self.shop}/api/{self.version}/graphql.json",headers={"X-Shopify-Storefront-Access-Token":self.token},json={"query":query,"variables":{"input":{"lines":[{"merchandiseId":variant_id,"quantity":quantity}],"attributes":[{"key":"rpa_correlation","value":str(correlation)}]}}})
            if response.status_code!=200:raise ApplicationError(503,"CART_UNKNOWN","Cart outcome is unknown; do not retry blindly.")
            data=response.json()
            result=(data.get("data") or {}).get("cartCreate") or {}
            if data.get("errors") or result.get("userErrors") or not result.get("cart"):raise ApplicationError(422,"CART_REJECTED","Storefront did not confirm a valid cart.")
            cart=result["cart"];lines=cart["lines"]["nodes"]
            from urllib.parse import urlparse
            url=urlparse(cart["checkoutUrl"])
            if len(lines)!=1 or lines[0]["quantity"]!=quantity or lines[0]["merchandise"]["id"]!=variant_id or url.scheme!="https" or url.hostname!=self.shop:
                raise ApplicationError(422,"CART_MISMATCH","Storefront cart or checkout origin does not match the requested scope.")
            return cart
