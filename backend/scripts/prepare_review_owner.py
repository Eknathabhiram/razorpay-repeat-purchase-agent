"""Create a random local owner credential for review; never print it."""
import json
from pathlib import Path
import secrets
import os
from app.cli import bootstrap
from app.db import Database
from app.runtime import run
from app.settings import Settings, BACKEND


async def main():
    db = Database(Settings.from_environment().database_url)
    path = BACKEND / ".local" / "owner-access.json"
    credentials = json.loads(path.read_text()) if path.exists() else {
        "login": "owner", "password": secrets.token_urlsafe(32)}
    try:
        await bootstrap(db, credentials["login"], credentials["password"],
                        os.getenv("SHOPIFY_SHOP", "repeat-purchase-agent-test.myshopify.com"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(credentials, indent=2), encoding="utf-8")
        print("Owner ready. Read backend/.local/owner-access.json privately for local login.")
        print("Use python -m app.cli owner-password to choose a replacement; existing sessions will be revoked.")
    finally:
        await db.close()


if __name__ == "__main__":
    run(main())
