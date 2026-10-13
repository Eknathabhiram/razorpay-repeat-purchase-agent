"""Real PostgreSQL acceptance tests. The disposable database name is enforced."""
import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import secrets
import sys
import unittest
import uuid
import httpx
import sqlalchemy as sa
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from alembic import command
from alembic.config import Config
from app import schema as t
from app.cli import bootstrap
from app.db import Database
from app.main import create_app
from app.security import digest, hasher
from app.settings import BACKEND, Settings

if sys.platform == "win32":
    # unittest.IsolatedAsyncioTestCase in Python 3.12 uses the event-loop policy.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def test_urls():
    app_url, owner_url = os.getenv("APP_TEST_DATABASE_URL"), os.getenv("MIGRATION_TEST_DATABASE_URL")
    if not app_url or not owner_url:
        path = BACKEND / ".local/postgres/auth.json"
        if not path.exists():
            raise RuntimeError("Prepare PostgreSQL or configure explicit test URLs")
        auth = json.loads(path.read_text())
        app_url = f"postgresql+psycopg://rpa_app:{auth['app']}@127.0.0.1:55432/rpa_stage1_test"
        owner_url = f"postgresql+psycopg://rpa_migrator:{auth['migrator']}@127.0.0.1:55432/rpa_stage1_test"
    if any(make_url(url).database != "rpa_stage1_test" for url in (app_url, owner_url)):
        raise RuntimeError("Tests only run against the disposable rpa_stage1_test database")
    return app_url, owner_url


class MockShopify:
    shop = "repeat-purchase-agent-test.myshopify.com"
    client_id, secret = "synthetic-id", "synthetic-secret"

    async def snapshot(self):
        return {"mode": "development", "read_only": True, "checked_at": datetime.now(timezone.utc).isoformat(),
                "shop": {"myshopifyDomain": self.shop, "currencyCode": "INR"},
                "products": [{"id": "synthetic-product"}], "customers": [], "orders": [],
                "draftOrders": [], "locations": [], "warnings": []}


class FoundationTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_url, cls.owner_url = test_urls()
        previous = {k: os.environ.get(k) for k in ("APP_DATABASE_URL", "MIGRATION_DATABASE_URL")}
        os.environ["APP_DATABASE_URL"], os.environ["MIGRATION_DATABASE_URL"] = cls.app_url, cls.owner_url
        try:
            cfg = Config(str(BACKEND / "alembic.ini"))
            command.upgrade(cfg, "head")
            command.downgrade(cfg, "base")
            command.upgrade(cfg, "head")
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    async def asyncSetUp(self):
        self.owner_db = Database(self.owner_url)
        async with self.owner_db.unit_of_work() as session:
            names = ", ".join(t.metadata.tables.keys())
            await session.execute(sa.text("TRUNCATE " + names + " CASCADE"))
        self.app = create_app(Settings(self.app_url), MockShopify())
        self.db = self.app.state.db
        self.password = secrets.token_urlsafe(24)
        self.owner_id = await bootstrap(self.db, "owner", self.password, MockShopify.shop)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),
                                       base_url="http://localhost:8766",
                                       headers={"Origin": "http://localhost:8766"})
        response = await self.client.post("/api/v1/auth/login", json={"login": "owner", "password": self.password})
        self.assertEqual(response.status_code, 200)
        self.csrf = response.json()["data"]["csrf_token"]
        self.headers = {"X-CSRF-Token": self.csrf}
        self.workspaces = (await self.client.get("/api/v1/me")).json()["data"]["workspaces"]
        self.demo = next(w for w in self.workspaces if w["environment"] == "demo")
        self.dev = next(w for w in self.workspaces if w["environment"] == "development")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.db.close()
        await self.owner_db.close()

    async def rename(self, workspace=None, key=None, version=1, name="Reviewed workspace"):
        workspace = workspace or self.demo
        return await self.client.put("/api/v1/workspaces/" + workspace["id"],
            headers={**self.headers, "Idempotency-Key": key or str(uuid.uuid4())},
            json={"name": name, "expected_version": version})

    async def test_health_cookie_logout_and_session_hash(self):
        self.assertEqual((await self.client.get("/api/v1/health/ready")).status_code, 200)
        async with self.db.unit_of_work() as session:
            row = (await session.execute(sa.select(t.sessions))).mappings().one()
            self.assertNotEqual(row["token_hash"], self.client.cookies["rpa_foundation_session"])
            self.assertNotEqual(row["csrf_hash"], self.csrf)
        self.assertEqual((await self.client.post("/api/v1/auth/logout", headers=self.headers)).status_code, 200)
        self.assertEqual((await self.client.get("/api/v1/me")).status_code, 401)

    async def test_expired_disabled_and_revoked_session_denied(self):
        async with self.db.unit_of_work() as session:
            await session.execute(t.sessions.update().values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        self.assertEqual((await self.client.get("/api/v1/me")).status_code, 401)
        async with self.db.unit_of_work() as session:
            await session.execute(t.sessions.update().values(expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
            await session.execute(t.users.update().values(disabled_at=sa.func.now()))
        self.assertEqual((await self.client.get("/api/v1/me")).status_code, 401)
        async with self.db.unit_of_work() as session:
            await session.execute(t.users.update().values(disabled_at=None))
            await session.execute(t.sessions.update().values(revoked_at=sa.func.now()))
        self.assertEqual((await self.client.get("/api/v1/me")).status_code, 401)

    async def test_cross_tenant_and_cross_workspace_binding(self):
        await bootstrap(self.db, "second-owner", secrets.token_urlsafe(24), "other.myshopify.com")
        async with self.db.unit_of_work() as session:
            foreign = (await session.execute(sa.select(t.workspaces).where(
                t.workspaces.c.id.not_in([uuid.UUID(w["id"]) for w in self.workspaces])))).mappings().first()
        self.assertEqual((await self.client.get("/api/v1/workspaces/" + str(foreign["id"]))).status_code, 404)
        self.assertEqual((await self.rename({"id": str(foreign["id"])})).status_code, 404)
        # Physical constraints reject another tenant's workspace with this merchant ID.
        with self.assertRaises(DBAPIError):
            async with self.db.unit_of_work() as session:
                ours = (await session.execute(sa.select(t.workspaces).where(
                    t.workspaces.c.id == uuid.UUID(self.demo["id"])))).mappings().one()
                await session.execute(t.connectors.insert().values(merchant_id=ours["merchant_id"],
                    workspace_id=foreign["id"], provider="forged", source_mode="test",
                    provider_environment="development", state="not_connected"))

    async def test_viewer_cannot_mutate_or_check_provider(self):
        async with self.db.unit_of_work() as session:
            await session.execute(t.memberships.update().where(t.memberships.c.user_id == self.owner_id).values(role="viewer"))
        self.assertEqual((await self.rename()).status_code, 403)
        self.assertEqual((await self.client.get("/api/v1/workspaces/" + self.demo["id"])).status_code, 200)

    async def test_csrf_origin_and_unknown_fields(self):
        path = "/api/v1/workspaces/" + self.demo["id"]
        body = {"name": "new", "expected_version": 1}
        response = await self.client.put(path, json=body, headers={"Idempotency-Key": str(uuid.uuid4())})
        self.assertEqual(response.status_code, 403)
        response = await self.client.put(path, json=body, headers={
            **self.headers, "Idempotency-Key": str(uuid.uuid4()), "Origin": "https://attacker.example"})
        self.assertEqual(response.status_code, 403)
        response = await self.client.put(path, json={**body, "merchant_id": "forged"},
            headers={**self.headers, "Idempotency-Key": str(uuid.uuid4())})
        self.assertEqual(response.status_code, 422)

    async def test_idempotent_update_conflict_and_one_audit(self):
        key = str(uuid.uuid4())
        first, second = await self.rename(key=key), await self.rename(key=key)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["data"], second.json()["data"])
        self.assertEqual((await self.rename(key=key, name="different")).status_code, 409)
        self.assertEqual((await self.rename(name="stale")).status_code, 409)
        audit = (await self.client.get("/api/v1/workspaces/" + self.demo["id"] + "/audit")).json()["data"]
        self.assertEqual(sum(a["event_type"] == "workspace.renamed" for a in audit), 1)
        current_dev = (await self.client.get("/api/v1/workspaces/" + self.dev["id"])).json()["data"]
        self.assertEqual(current_dev["version"], 1)

    async def test_concurrent_same_key_and_versions(self):
        key = str(uuid.uuid4())
        results = await asyncio.gather(self.rename(key=key), self.rename(key=key))
        self.assertEqual([r.status_code for r in results], [200, 200])
        self.assertEqual(results[0].json()["data"]["receipt_id"], results[1].json()["data"]["receipt_id"])
        results = await asyncio.gather(self.rename(version=2, name="A"), self.rename(version=2, name="B"))
        self.assertEqual(sorted(r.status_code for r in results), [200, 409])

    async def test_restart_preserves_session_and_workspace(self):
        changed = (await self.rename()).json()["data"]
        restarted = create_app(Settings(self.app_url), MockShopify())
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=restarted),
            base_url="http://localhost:8766", cookies=self.client.cookies) as client:
            row = await client.get("/api/v1/workspaces/" + self.demo["id"])
            self.assertEqual(row.json()["data"]["version"], changed["version"])
            self.assertEqual((await client.get("/api/v1/me")).status_code, 200)
        await restarted.state.db.close()

    async def test_capability_check_is_scoped_and_not_false_live(self):
        development = (await self.client.get("/api/v1/workspaces/" + self.dev["id"] + "/connectors")).json()["data"]
        connector = next(c for c in development if c["provider"] == "shopify")
        self.assertTrue(all(c["status"] == "unverified" for c in connector["capabilities"]))
        forged = await self.client.post("/api/v1/workspaces/" + self.demo["id"] + "/connectors/" + connector["id"] + "/check",
            json={"expected_version": 1}, headers=self.headers)
        self.assertEqual(forged.status_code, 404)
        checked = await self.client.post("/api/v1/workspaces/" + self.dev["id"] + "/connectors/" + connector["id"] + "/check",
            json={"expected_version": 1}, headers=self.headers)
        self.assertEqual(checked.status_code, 200)
        rows = (await self.client.get("/api/v1/workspaces/" + self.dev["id"] + "/connectors")).json()["data"]
        updated = next(c for c in rows if c["provider"] == "shopify")
        self.assertEqual(updated["source_mode"], "test")
        caps = {c["capability"]: c["status"] for c in updated["capabilities"]}
        self.assertEqual(caps["read_orders"], "available")
        self.assertEqual(caps["prepare_checkout"], "unverified")

    async def test_snapshot_compatibility_requires_member_and_preserves_shape(self):
        self.assertEqual((await self.client.get("/api/shopify/snapshot")).json()["mode"], "development")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),
                                    base_url="http://localhost:8766") as outsider:
            self.assertEqual((await outsider.get("/api/shopify/snapshot")).status_code, 401)
        self.assertEqual((await self.client.get("/")).status_code, 200)
        self.assertEqual((await self.client.get("/foundation")).status_code, 200)

    async def test_login_rate_limit_persists_and_errors_never_echo_password(self):
        invalid = await self.client.post("/api/v1/auth/login", json={
            "login": "owner", "password": self.password, "unexpected": "secret"})
        self.assertEqual(invalid.status_code, 422)
        self.assertNotIn(self.password, invalid.text)
        for _ in range(7):
            self.assertEqual((await self.client.post("/api/v1/auth/login",
                json={"login": "owner", "password": "wrong"})).status_code, 401)
        self.assertEqual((await self.client.post("/api/v1/auth/login",
            json={"login": "owner", "password": self.password})).status_code, 429)
        async with self.db.unit_of_work() as session:
            self.assertEqual(await session.scalar(sa.select(sa.func.max(t.login_limits.c.attempts))), 9)

    async def test_private_files_host_and_audit_permissions(self):
        for path in ("/backend/.env", "/backend/.env.foundation", "/.local/postgres/auth.json",
                     "/frontend/../backend/.env", "/frontend/%2e%2e/backend/.env"):
            self.assertEqual((await self.client.get(path)).status_code, 404)
        self.assertEqual((await self.client.get("/api/v1/me", headers={"Host": "attacker.example"})).status_code, 400)
        with self.assertRaises(DBAPIError):
            async with self.db.unit_of_work() as session:
                await session.execute(t.audit_events.update().values(event_type="tampered"))
        async with self.db.unit_of_work() as session:
            role = (await session.execute(sa.text("SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user"))).one()
            self.assertEqual(tuple(role), (False, False))

    async def test_missing_database_has_actionable_readiness(self):
        unconfigured = create_app(Settings(None), MockShopify())
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=unconfigured),
                                    base_url="http://localhost:8766") as client:
            self.assertEqual((await client.get("/api/v1/health/live")).status_code, 200)
            ready = await client.get("/api/v1/health/ready")
            self.assertEqual(ready.status_code, 503)
            self.assertEqual(ready.json()["error"]["code"], "DATABASE_UNCONFIGURED")
        with self.assertRaises(ValueError):
            Settings("sqlite://")


if __name__ == "__main__":
    unittest.main()
