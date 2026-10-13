"""Fresh isolated Stage 05 QA workspace, preserving all owner data."""
import json
import secrets
import uuid
import os
from app.cli import bootstrap
from app.db import Database
from app.runtime import run
from app.settings import Settings,BACKEND


async def main():
    db=Database(Settings.from_environment().database_url)
    access={"login":"stage05-qa-"+uuid.uuid4().hex[:8],"password":secrets.token_urlsafe(32)}
    try:
        await bootstrap(db,access["login"],access["password"],os.getenv("SHOPIFY_SHOP","repeat-purchase-agent-test.myshopify.com"))
        (BACKEND/".local/stage05-qa.json").write_text(json.dumps(access),encoding="utf-8")
        print("Fresh Stage 05 QA tenant prepared without printing credentials.")
    finally:await db.close()


if __name__=="__main__":run(main())
