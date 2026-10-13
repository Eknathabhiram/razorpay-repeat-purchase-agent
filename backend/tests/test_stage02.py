import json
import unittest
import uuid
import httpx
from app.main import create_app
from app.settings import Settings
import tests.test_foundation as foundation


class Stage02Tests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        foundation.FoundationTests.setUpClass.__func__(cls)

    asyncSetUp = foundation.FoundationTests.asyncSetUp
    asyncTearDown = foundation.FoundationTests.asyncTearDown

    async def read(self, workspace=None):
        return (await self.client.get("/api/v1/workspaces/" + (workspace or self.demo)["id"] + "/ui-state")).json()["data"]

    async def command(self, action, workspace=None, key=None, **fields):
        workspace = workspace or self.demo
        current = await self.read(workspace)
        return await self.client.post("/api/v1/workspaces/" + workspace["id"] + "/demo-commands",
            headers={**self.headers, "Idempotency-Key": key or str(uuid.uuid4())},
            json={"expected_version": current["version"], "action": action, **fields})

    async def test_demo_state_persists_and_development_is_unavailable(self):
        current = await self.read()
        self.assertEqual(current["source_mode"], "simulated")
        self.assertEqual((await self.command("pause")).status_code, 200)
        self.assertTrue((await self.read())["state"]["paused"])
        dev = await self.read(self.dev)
        self.assertIsNone(dev["state"])
        self.assertEqual((await self.command("reset", workspace=self.dev)).status_code, 422)
        restarted = create_app(Settings(self.app_url), foundation.MockShopify())
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=restarted),
            base_url="http://localhost:8766", cookies=self.client.cookies) as client:
            data = (await client.get("/api/v1/workspaces/" + self.demo["id"] + "/ui-state")).json()["data"]
            self.assertTrue(data["state"]["paused"])
        await restarted.state.db.close()

    async def test_first_plan_installation_and_no_fabricated_outcomes(self):
        await self.command("reset", scenario="setup")
        self.assertEqual((await self.command("approve_plan", selected=["ananya"])).status_code, 422)
        policy = (await self.read())["state"]["policy"]
        await self.command("install", policy={**policy, "mode": "bounded"})
        state = (await self.read())["state"]
        self.assertTrue(state["installed"])
        self.assertFalse(state["plan_approved"])
        self.assertEqual(state["policy"]["mode"], "bounded")
        await self.command("approve_plan", selected=["ananya", "rahul"])
        state = (await self.read())["state"]
        self.assertEqual(state["assigned"], ["ananya", "rahul"])
        self.assertFalse(state["order_confirmed"])
        self.assertFalse(state["checkout_sent"])
        self.assertEqual((await self.command("approve_checkout")).status_code, 422)

    async def test_policy_hold_pause_and_purchase_survives_renewal(self):
        current = (await self.read())["state"]
        policy = current["policy"]
        await self.command("save_policy", policy={**policy, "cap": 3})
        self.assertTrue((await self.read())["state"]["plan_needs_review"])
        self.assertEqual((await self.command("approve_checkout")).status_code, 422)
        await self.command("approve_plan", selected=["ananya", "rahul", "meera"])
        state = (await self.read())["state"]
        self.assertNotIn("meera", state["selected"])
        self.assertTrue(state["order_confirmed"])
        await self.command("pause")
        self.assertEqual((await self.command("approve_checkout")).status_code, 422)
        await self.command("resume")
        self.assertEqual((await self.command("approve_checkout")).status_code, 200)
        self.assertTrue((await self.read())["state"]["order_confirmed"])

    async def test_exact_idempotency_version_and_unauthorised_commands(self):
        current = await self.read()
        path = "/api/v1/workspaces/" + self.demo["id"] + "/demo-commands"
        body = {"expected_version": current["version"], "action": "takeover"}
        headers = {**self.headers, "Idempotency-Key": str(uuid.uuid4())}
        first = await self.client.post(path, json=body, headers=headers)
        second = await self.client.post(path, json=body, headers=headers)
        self.assertEqual(first.json()["data"], second.json()["data"])
        self.assertEqual((await self.client.post(path, json={**body, "action": "handback"}, headers=headers)).status_code, 409)
        self.assertEqual((await self.client.post(path, json=body, headers=self.headers | {"Idempotency-Key": str(uuid.uuid4())})).status_code, 409)
        self.assertEqual((await self.client.post(path, json={**body, "action": "charge_card"}, headers=headers)).status_code, 422)

    async def test_session_restore_and_scoped_store_route(self):
        restored = await self.client.post("/api/v1/auth/session")
        self.assertEqual(restored.status_code, 200)
        self.headers["X-CSRF-Token"] = restored.json()["data"]["csrf_token"]
        self.assertEqual((await self.command("pause")).status_code, 200)
        connectors = (await self.client.get("/api/v1/workspaces/" + self.dev["id"] + "/connectors")).json()["data"]
        shop = next(c for c in connectors if c["provider"] == "shopify")
        response = await self.client.get("/api/v1/workspaces/" + self.demo["id"] + "/connectors/" + shop["id"] + "/store")
        self.assertEqual(response.status_code, 404)
        schema = (await self.client.get("/api/openapi.json")).json()
        self.assertIn("UIReadModel", schema["components"]["schemas"])
        self.assertIn("StoreView", schema["components"]["schemas"])
