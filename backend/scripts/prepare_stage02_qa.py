"""Prepare an isolated QA tenant without resetting the owner's demo state."""
import json
import secrets
import uuid
import os
from app.cli import bootstrap
from app.db import Database
from app.runtime import run
from app.settings import Settings, BACKEND


async def main():
    db = Database(Settings.from_environment().database_url)
    credentials = {"login": "stage02-qa-" + uuid.uuid4().hex[:8],
                   "password": secrets.token_urlsafe(32)}
    try:
        await bootstrap(db, credentials["login"], credentials["password"],
                        os.getenv("SHOPIFY_SHOP", "repeat-purchase-agent-test.myshopify.com"))
        (BACKEND / ".local/stage02-qa.json").write_text(json.dumps(credentials), encoding="utf-8")
        print("Isolated Stage 02 QA tenant prepared. Credential values were not printed.")
    finally:
        await db.close()


if __name__ == "__main__":
    run(main())
