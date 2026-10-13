"""A fresh private QA tenant; never resets owner records."""
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
    access={"login":"stage04-qa-"+uuid.uuid4().hex[:8],"password":secrets.token_urlsafe(32)}
    try:
        await bootstrap(db,access["login"],access["password"],os.getenv("SHOPIFY_SHOP","repeat-purchase-agent-test.myshopify.com"))
        (BACKEND/".local/stage04-qa.json").write_text(json.dumps(access),encoding="utf-8")
        print("Fresh Stage 04 QA tenant prepared; credentials remain private.")
    finally:await db.close()


if __name__=="__main__":run(main())
