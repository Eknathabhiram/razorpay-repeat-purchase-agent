"""Local administration. Passwords use hidden prompts/environment, never argv."""
import argparse
import asyncio
import os
from getpass import getpass
import uuid
import sqlalchemy as sa
from . import schema as t
from .db import Database
from .security import hasher
from .settings import Settings
from .runtime import run


async def bootstrap(db, login, password, shop):
    if len(password) < 12 or len(password) > 1024:
        raise ValueError("Use an owner password between 12 and 1024 characters")
    async with db.unit_of_work() as session:
        user = (await session.execute(sa.select(t.users).where(
            t.users.c.login_identifier == login))).mappings().first()
        if user:
            if not hasher.verify(user["password_digest"], password):
                raise ValueError("Existing owner password differs; use the explicit owner-password command")
            return user["id"]
        user_id, merchant_id = uuid.uuid4(), uuid.uuid4()
        await session.execute(t.merchants.insert().values(id=merchant_id, name="Loop Essentials",
            default_timezone="Asia/Kolkata", currency="INR"))
        await session.execute(t.users.insert().values(id=user_id, login_identifier=login,
                                                     password_digest=hasher.hash(password)))
        await session.execute(t.memberships.insert().values(merchant_id=merchant_id,
                                                           user_id=user_id, role="owner"))
        for environment in ("demo", "development"):
            workspace_id = uuid.uuid4()
            await session.execute(t.workspaces.insert().values(id=workspace_id, merchant_id=merchant_id,
                environment=environment, name="Loop Essentials · " + environment))
            for provider, caps in {
                "shopify": ("read_catalogue", "read_customers", "read_orders", "prepare_checkout"),
                "razorpay": ("read_payment_evidence", "reconcile_payment"),
                "twilio": ("trial_template_send", "receive_inbound", "receive_status"),
                "voice": ("browser_audio",), "support": ("internal_cases",)
            }.items():
                connector_id = uuid.uuid4()
                simulated = environment == "demo"
                await session.execute(t.connectors.insert().values(id=connector_id, merchant_id=merchant_id,
                    workspace_id=workspace_id, provider=provider,
                    provider_account_id=shop if provider == "shopify" and not simulated else None,
                    source_mode="simulated" if simulated or provider in ("voice", "support") else "test",
                    provider_environment="fixture" if simulated else "development",
                    credential_ref="env:SHOPIFY_CLIENT_ID+SHOPIFY_CLIENT_SECRET" if provider == "shopify" and not simulated else None,
                    state="not_connected"))
                for capability in caps:
                    await session.execute(t.capabilities.insert().values(merchant_id=merchant_id,
                        workspace_id=workspace_id, connector_id=connector_id, capability=capability,
                        status="unverified", reason="Stage 01 creates bindings; adapter capability has not been checked here."))
            await session.execute(t.audit_events.insert().values(
                merchant_id=merchant_id, workspace_id=workspace_id, actor_id=user_id,
                event_type="workspace.bootstrapped", target_id=workspace_id,
                correlation_id=uuid.uuid4(), details={"environment": environment}))
        return user_id


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["bootstrap", "owner-password"])
    parser.add_argument("--login", default="owner")
    args = parser.parse_args()
    settings = Settings.from_environment()
    db = Database(settings.database_url)
    login = args.login.strip().lower()
    if not login or len(login) > 120:
        raise ValueError("Invalid login identifier")
    password = os.getenv("APP_BOOTSTRAP_PASSWORD") or getpass("Owner application password (12+ characters): ")
    try:
        if args.command == "bootstrap":
            await bootstrap(db, login, password, os.getenv("SHOPIFY_SHOP", "repeat-purchase-agent-test.myshopify.com"))
            print("Owner and separate demo/development workspaces are ready. No credential was printed.")
        else:
            if not 12 <= len(password) <= 1024:
                raise ValueError("Use a password between 12 and 1024 characters")
            async with db.unit_of_work() as session:
                user = (await session.execute(sa.select(t.users).where(
                    t.users.c.login_identifier == login).with_for_update())).mappings().first()
                if not user:
                    raise ValueError("Owner not found")
                await session.execute(t.users.update().where(t.users.c.id == user["id"])
                                      .values(password_digest=hasher.hash(password), updated_at=sa.func.now()))
                await session.execute(t.sessions.update().where(t.sessions.c.user_id == user["id"])
                                      .values(revoked_at=sa.func.now()))
            print("Owner password changed locally; all earlier sessions revoked.")
    finally:
        await db.close()


if __name__ == "__main__":
    run(main())
