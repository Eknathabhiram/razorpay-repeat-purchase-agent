"""Local, read-only Shopify development-store connector. No execution engine."""
import asyncio
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "backend" / ".env")
QUERY = """
query ReadStoreSnapshot {
  shop { id name myshopifyDomain currencyCode }
  products(first: 50) {
    nodes { id title status variants(first: 20) {
      nodes { id title sku price inventoryQuantity }
      pageInfo { hasNextPage }
    } }
    pageInfo { hasNextPage }
  }
  locations(first: 10) { nodes { id name } pageInfo { hasNextPage } }
}
"""
CUSTOMERS_QUERY = """
query ReadCustomers {
  customers(first: 50) {
    nodes { id numberOfOrders }
    pageInfo { hasNextPage }
  }
}
"""
ORDERS_QUERY = """
query ReadOrders {
  orders(first: 20, sortKey: CREATED_AT, reverse: true) {
    nodes { id name createdAt test displayFinancialStatus displayFulfillmentStatus
      totalPriceSet { shopMoney { amount currencyCode } }
    }
    pageInfo { hasNextPage }
  }
  draftOrders(first: 20, sortKey: UPDATED_AT, reverse: true) {
    nodes { id name status totalPriceSet { shopMoney { amount currencyCode } } }
    pageInfo { hasNextPage }
  }
}
"""


class ShopifyConnector:
    def __init__(self, shop, client_id, secret, version, transport=None):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.myshopify\.com", shop):
            raise ValueError("SHOPIFY_SHOP must be a myshopify.com domain")
        if not re.fullmatch(r"20\d{2}-(01|04|07|10)", version):
            raise ValueError("Invalid Shopify API version")
        self.shop, self.client_id, self.secret, self.version = shop, client_id, secret, version
        self.transport = transport
        self.token, self.expires_at = None, 0
        self.lock = asyncio.Lock()

    async def access_token(self, client):
        async with self.lock:
            if self.token and time.monotonic() < self.expires_at:
                return self.token
            response = await client.post(
                f"https://{self.shop}/admin/oauth/access_token",
                data={"grant_type": "client_credentials", "client_id": self.client_id,
                      "client_secret": self.secret},
            )
            if response.status_code != 200:
                raise HTTPException(502, "Shopify authentication failed. Check app installation and server credentials.")
            value = response.json()
            if not value.get("access_token"):
                raise HTTPException(502, "Shopify did not return an access token.")
            self.token = value["access_token"]
            self.expires_at = time.monotonic() + max(0, int(value.get("expires_in", 0)) - 60)
            return self.token

    async def snapshot(self):
        if not self.client_id or not self.secret:
            raise HTTPException(503, "Shopify credentials are missing from the server configuration.")
        try:
            async with httpx.AsyncClient(timeout=20, transport=self.transport, follow_redirects=False) as client:
                token = await self.access_token(client)
                data, warnings = {}, []
                # Protected customer/order permissions must not hide a valid catalogue connection.
                for area, query in (("store", QUERY), ("customers", CUSTOMERS_QUERY), ("orders and drafts", ORDERS_QUERY)):
                    response = await client.post(
                        f"https://{self.shop}/admin/api/{self.version}/graphql.json",
                        headers={"X-Shopify-Access-Token": token}, json={"query": query},
                    )
                    if response.status_code in (401, 403):
                        self.token, self.expires_at = None, 0
                        raise HTTPException(502, "Shopify access was denied. Review installed app permissions.")
                    if response.status_code == 429:
                        raise HTTPException(503, "Shopify rate limit reached. Wait before refreshing.")
                    if response.status_code != 200:
                        raise HTTPException(502, "Shopify is unavailable. Refresh the connection later.")
                    payload = response.json()
                    data.update(payload.get("data") or {})
                    if payload.get("errors"):
                        warnings.append(f"Shopify could not return {area}. Review scopes and protected-data access.")
        except httpx.TimeoutException:
            raise HTTPException(504, "Shopify request timed out. No data was confirmed.") from None
        except (httpx.RequestError, ValueError, TypeError):
            raise HTTPException(502, "Unable to read a valid Shopify response. Check the connection.") from None
        if not data.get("shop"):
            raise HTTPException(502, "Shopify did not confirm this store. Check app access and API version.")
        result = {"shop": data["shop"], "mode": "development", "read_only": True,
                  "checked_at": datetime.now(timezone.utc).isoformat(), "warnings": warnings}
        for field in ("products", "customers", "orders", "draftOrders", "locations"):
            section = data.get(field)
            result[field] = section.get("nodes", []) if section else None
            result[field + "_has_more"] = section.get("pageInfo", {}).get("hasNextPage", False) if section else None
        if any(p.get("variants", {}).get("pageInfo", {}).get("hasNextPage") for p in result["products"] or []):
            result["warnings"].append("Some products have more than 20 variants; this snapshot is partial.")
        return result


connector = ShopifyConnector(
    os.getenv("SHOPIFY_SHOP", "repeat-purchase-agent-test.myshopify.com"),
    os.getenv("SHOPIFY_CLIENT_ID", ""), os.getenv("SHOPIFY_CLIENT_SECRET", ""),
    os.getenv("SHOPIFY_API_VERSION", "2026-10"),
)
app = FastAPI(title="Repeat Purchase Agent — local Shopify connector", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])


@app.middleware("http")
async def local_browser_only(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin and origin not in ("http://127.0.0.1:8765", "http://localhost:8765"):
        return JSONResponse({"detail": "Use the local app URL to access this connector."}, status_code=403)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.get("/")
async def frontend():
    return FileResponse(ROOT / "frontend" / "design-handoff.html")


@app.get("/api/shopify/snapshot")
async def snapshot():
    return await connector.snapshot()


@app.get("/api/health")
async def health():
    return {"service": "local-shopify-connector", "configured": bool(connector.client_id and connector.secret),
            "shop": connector.shop, "read_only": True}


app.mount("/frontend", StaticFiles(directory=ROOT / "frontend"), name="frontend")
