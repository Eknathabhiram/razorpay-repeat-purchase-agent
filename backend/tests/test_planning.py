import asyncio
import unittest
import uuid
from datetime import datetime, timedelta, timezone
import httpx
import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError
from app import schema as t
from app.planning import estimate, money
from app.shopify_facts import read_facts
from shopify_app import ShopifyConnector
import tests.test_foundation as foundation


class EstimatorTests(unittest.TestCase):
    def test_median_mad_and_quantity_compatibility(self):
        now=datetime(2026,10,13,tzinfo=timezone.utc)
        history=[{"delivery_at":now-timedelta(days=d),"quantity":1} for d in (90,60,30)]
        start,end,basis=estimate(history,None)
        self.assertEqual((start,end,basis),(now-timedelta(days=1),now+timedelta(days=1),"same_variant_median"))
        history[1]["quantity"]=2
        self.assertEqual(estimate(history,None)[2],"needs_history")
        self.assertEqual(estimate(history,30)[2],"merchant_product_fallback")
        reminder=now+timedelta(days=4)
        self.assertEqual(estimate(history,30,reminder),(reminder,reminder,"customer_confirmed_date"))
        self.assertEqual(money("1273.15","INR"),127315)

    def test_missing_and_impossible_intervals(self):
        self.assertEqual(estimate([],30)[2],"needs_history")
        now=datetime.now(timezone.utc)
        self.assertEqual(estimate([{"delivery_at":now,"quantity":1}]*3,30)[2],"invalid_history")


class PlanningTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls): foundation.FoundationTests.setUpClass.__func__(cls)
    asyncSetUp=foundation.FoundationTests.asyncSetUp
    asyncTearDown=foundation.FoundationTests.asyncTearDown

    def path(self, workspace=None): return "/api/v1/workspaces/"+(workspace or self.demo)["id"]+"/planning"
    async def read(self,workspace=None): return (await self.client.get(self.path(workspace))).json()["data"]
    async def post(self,endpoint,body,workspace=None,key=None):
        return await self.client.post(self.path(workspace)+"/"+endpoint,json=body,headers={**self.headers,"Idempotency-Key":key or str(uuid.uuid4())})
    async def prepare(self):
        response=await self.post("facts",{"action":"seed_demo"})
        self.assertEqual(response.status_code,200,response.text)
        config={"variant_ids":["demo:laundry:1L"],"fallback_days":30}
        response=await self.post("policies",{"expected_revision":0,"config":config})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()["data"]

    async def test_exact_eligibility_and_provenance(self):
        data=await self.prepare()
        eligible=[o for o in data["opportunities"] if o["eligible"]]
        self.assertEqual(len(eligible),3)
        self.assertEqual({o["basis"] for o in eligible},{"same_variant_median","customer_confirmed_date","merchant_product_fallback"})
        reasons={code for o in data["opportunities"] for code in o["exclusion_codes"]}
        self.assertTrue({"delivery_unverified","opted_out","open_issue","new_relevant_purchase","consent_missing","return_or_refund"}.issubset(reasons))
        self.assertTrue(all(o["evidence_json"]["source_mode"]=="simulated" for o in data["opportunities"]))
        self.assertEqual((await self.read(self.dev))["facts_version"],0)
        self.assertEqual((await self.post("facts",{"action":"seed_demo"},self.dev)).status_code,422)

    async def test_immutable_scope_policy_diff_and_restart(self):
        data=await self.prepare()
        ids=[o["id"] for o in data["opportunities"] if o["eligible"]]
        first=await self.post("drafts",{"expected_revision":0,"selected":ids[:2]})
        self.assertEqual(first.status_code,200,first.text)
        original=first.json()["data"]["draft"]
        second=await self.post("drafts",{"expected_revision":1,"selected":ids[:1]})
        self.assertEqual(second.json()["data"]["draft"]["selected_count"],1)
        self.assertNotEqual(original["digest"],second.json()["data"]["draft"]["digest"])
        config={**data["policy"]["config_json"],"contact_cap":3}
        preview=await self.post("policy-preview",{"expected_revision":1,"config":config})
        self.assertEqual(preview.json()["data"]["diff"]["contact_cap"],{"before":2,"after":3})
        updated=await self.post("policies",{"expected_revision":1,"config":config})
        self.assertTrue(updated.json()["data"]["draft"]["stale"])
        async with self.db.unit_of_work() as session:
            self.assertEqual(await session.scalar(sa.select(sa.func.count()).select_from(t.plan_revisions)),2)
        from app.main import create_app
        from app.settings import Settings
        restarted=create_app(Settings(self.app_url),foundation.MockShopify())
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=restarted),base_url="http://localhost:8766",cookies=self.client.cookies) as client:
            self.assertTrue((await client.get(self.path())).json()["data"]["draft"]["stale"])
        await restarted.state.db.close()
        with self.assertRaises(DBAPIError):
            async with self.db.unit_of_work() as session: await session.execute(t.policies.update().values(digest="tampered"))

    async def test_stale_facts_exclusion_cannot_be_selected(self):
        data=await self.prepare()
        eligible=next(o for o in data["opportunities"] if o["eligible"])
        excluded=next(o for o in data["opportunities"] if not o["eligible"])
        self.assertEqual((await self.post("drafts",{"expected_revision":0,"selected":[excluded["id"]]})).status_code,422)
        async with self.db.unit_of_work() as session:
            await session.execute(t.variants.update().values(stock=0))
        self.assertEqual((await self.post("drafts",{"expected_revision":0,"selected":[eligible["id"]]})).status_code,409)
        refreshed=await self.post("facts",{"action":"refresh"})
        self.assertFalse(any(o["eligible"] for o in refreshed.json()["data"]["opportunities"]))

    async def test_concurrent_revisions_and_exact_idempotency(self):
        data=await self.prepare()
        body={"expected_revision":1,"config":{**data["policy"]["config_json"],"contact_cap":3}}
        key=str(uuid.uuid4())
        first=await self.post("policies",body,key=key)
        replay=await self.post("policies",body,key=key)
        self.assertEqual(first.json()["data"],replay.json()["data"])
        self.assertEqual((await self.post("policies",{**body,"expected_revision":2},key=key)).status_code,409)
        body["expected_revision"]=2
        results=await asyncio.gather(self.post("policies",body),self.post("policies",body))
        self.assertEqual(sorted(r.status_code for r in results),[200,409])

    async def test_tenant_role_and_cross_scope_constraints(self):
        await self.prepare()
        async with self.db.unit_of_work() as session:
            await session.execute(t.memberships.update().values(role="viewer"))
        self.assertEqual((await self.post("facts",{"action":"refresh"})).status_code,403)
        self.assertEqual((await self.client.get("/api/v1/workspaces/"+str(uuid.uuid4())+"/planning")).status_code,404)
        with self.assertRaises(DBAPIError):
            async with self.owner_db.unit_of_work() as session:
                customer=(await session.execute(sa.select(t.customers))).mappings().first()
                await session.execute(t.customer_evidence.insert().values(merchant_id=customer["merchant_id"],workspace_id=uuid.UUID(self.dev["id"]),
                    customer_id=customer["id"],kind="consent",value={},effective_at=datetime.now(timezone.utc),provenance={}))


class PaginationTests(unittest.IsolatedAsyncioTestCase):
    async def test_denied_returns_preserve_orders_but_block_coverage(self):
        def response(request):
            if "oauth" in str(request.url): return httpx.Response(200,json={"access_token":"synthetic","expires_in":600})
            import json
            body=json.loads(request.content);query=body["query"]
            if "currentAppInstallation" in query: return httpx.Response(200,json={"data":{"shop":{"myshopifyDomain":"test.myshopify.com","currencyCode":"INR"},"currentAppInstallation":{"accessScopes":[]}}})
            if "returns(first" in query: return httpx.Response(200,json={"errors":[{"message":"Access denied for returns field."}]})
            field=next(f for f in ("products","customers","orders") if f+"(" in query)
            return httpx.Response(200,json={"data":{field:{"nodes":[{"id":"order1","fulfillments":[],"refunds":[],"lineItems":{"nodes":[],"pageInfo":{"hasNextPage":False}}}] if field=="orders" else [],"pageInfo":{"hasNextPage":False,"endCursor":None}}}})
        adapter=ShopifyConnector("test.myshopify.com","synthetic","synthetic","2026-10",httpx.MockTransport(response))
        snapshot=await read_facts(adapter)
        self.assertEqual(len(snapshot["orders"]),1)
        self.assertFalse(snapshot["complete"])
        self.assertFalse(snapshot["orders"][0]["returns"]["verified"])

    async def test_top_level_pagination_and_invalid_cursor(self):
        calls=[]
        def response(request):
            if "oauth" in str(request.url): return httpx.Response(200,json={"access_token":"synthetic","expires_in":600})
            import json
            body=json.loads(request.content);query=body["query"];after=body["variables"].get("after");calls.append(after)
            if "currentAppInstallation" in query: return httpx.Response(200,json={"data":{"shop":{"myshopifyDomain":"test.myshopify.com","currencyCode":"INR"},"currentAppInstallation":{"accessScopes":[{"handle":"read_all_orders"}]}}})
            field=next(f for f in ("products","customers","orders") if f+"(" in query)
            return httpx.Response(200,json={"data":{field:{"nodes":[{"id":"c1" if not after else "c2"}] if field=="customers" else [],"pageInfo":{"hasNextPage":field=="customers" and not after,"endCursor":"second"}}}})
        adapter=ShopifyConnector("test.myshopify.com","synthetic","synthetic","2026-10",httpx.MockTransport(response))
        snapshot=await read_facts(adapter)
        self.assertEqual(len(snapshot["customers"]),2);self.assertTrue(snapshot["complete"]);self.assertIn("second",calls)
