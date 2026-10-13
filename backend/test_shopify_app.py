import unittest
import httpx
from fastapi import HTTPException
from shopify_app import ShopifyConnector, app


class ConnectorTests(unittest.IsolatedAsyncioTestCase):
    async def test_token_cache_and_partial_access(self):
        calls = []
        def respond(request):
            calls.append(request)
            if request.url.path.endswith("access_token"):
                return httpx.Response(200, json={"access_token": "test-secret", "expires_in": 86400})
            self.assertEqual(request.headers["X-Shopify-Access-Token"], "test-secret")
            if "ReadCustomers" in request.content.decode():
                return httpx.Response(200, json={"errors": [{"message": "Customer access needs approval"}]})
            if "ReadOrders" in request.content.decode():
                return httpx.Response(200, json={"data": {"orders": {"nodes": []}, "draftOrders": {"nodes": []}}})
            return httpx.Response(200, json={"data": {"shop": {"name": "Test"}, "products": {
                "nodes": [{"id": "p1", "variants": {"nodes": []}}], "pageInfo": {"hasNextPage": True}}},
                })
        c = ShopifyConnector("fixture.myshopify.com", "id", "secret", "2026-10", httpx.MockTransport(respond))
        first = await c.snapshot()
        await c.snapshot()
        self.assertEqual(len(calls), 7)
        self.assertIsNone(first["customers"])
        self.assertTrue(first["products_has_more"])
        self.assertEqual(first["warnings"], ["Shopify could not return customers. Review scopes and protected-data access."])
        self.assertNotIn("test-secret", str(first))

    async def test_no_false_connection_on_authentication_failure(self):
        c = ShopifyConnector("fixture.myshopify.com", "id", "secret", "2026-10",
                             httpx.MockTransport(lambda request: httpx.Response(401)))
        with self.assertRaises(HTTPException) as error:
            await c.snapshot()
        self.assertEqual(error.exception.status_code, 502)
        self.assertNotIn("secret", error.exception.detail)

    async def test_reject_non_shopify_host(self):
        with self.assertRaises(ValueError):
            ShopifyConnector("attacker.example", "id", "secret", "2026-10")

    async def test_block_cross_origin_and_private_file_access(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8765") as client:
            self.assertEqual((await client.get("/api/health", headers={"Origin": "https://attacker.example"})).status_code, 403)
            self.assertEqual((await client.get("/backend/.env")).status_code, 404)
            response = await client.get("/api/health")
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("secret", response.text)
            self.assertEqual(response.headers["Cache-Control"], "no-store")


if __name__ == "__main__":
    unittest.main()
