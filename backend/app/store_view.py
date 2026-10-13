from datetime import datetime
from pydantic import BaseModel


class ProductRow(BaseModel):
    product_id: str
    title: str
    variant_id: str
    sku: str
    price: str
    currency: str
    stock: int | None


class CustomerRow(BaseModel):
    id: str
    number_of_orders: str


class OrderRow(BaseModel):
    id: str
    name: str
    financial_status: str
    fulfilment_status: str
    total: str
    currency: str
    test: bool


class DraftRow(BaseModel):
    id: str
    name: str
    status: str
    total: str
    currency: str


class StoreView(BaseModel):
    shop_name: str
    domain: str
    source_mode: str
    checked_at: datetime
    coverage_complete: bool
    warnings: list[str]
    product_count: int
    products: list[ProductRow]
    customers: list[CustomerRow] | None
    orders: list[OrderRow] | None
    drafts: list[DraftRow] | None


def project_snapshot(snapshot):
    shop = snapshot["shop"]
    products = [ProductRow(product_id=p["id"], title=p["title"], variant_id=v["id"],
                sku=v.get("sku") or "", price=v["price"], currency=shop["currencyCode"],
                stock=v.get("inventoryQuantity"))
                for p in snapshot["products"] or [] for v in p.get("variants", {}).get("nodes", [])]
    def cost(row):
        return row["totalPriceSet"]["shopMoney"]
    return StoreView(shop_name=shop.get("name", shop["myshopifyDomain"]), domain=shop["myshopifyDomain"],
        source_mode="test", checked_at=snapshot["checked_at"], warnings=snapshot["warnings"],
        coverage_complete=not any(snapshot.get(k + "_has_more") for k in
            ("products", "customers", "orders", "draftOrders", "locations")) and not snapshot["warnings"],
        product_count=len(snapshot["products"] or []), products=products,
        customers=[CustomerRow(id=c["id"], number_of_orders=str(c["numberOfOrders"]))
                   for c in snapshot["customers"]] if snapshot["customers"] is not None else None,
        orders=[OrderRow(id=o["id"], name=o["name"], financial_status=o["displayFinancialStatus"],
                        fulfilment_status=o["displayFulfillmentStatus"], total=cost(o)["amount"],
                        currency=cost(o)["currencyCode"], test=o["test"])
                for o in snapshot["orders"]] if snapshot["orders"] is not None else None,
        drafts=[DraftRow(id=o["id"], name=o["name"], status=o["status"],
                        total=cost(o)["amount"], currency=cost(o)["currencyCode"])
                for o in snapshot["draftOrders"]] if snapshot["draftOrders"] is not None else None)
