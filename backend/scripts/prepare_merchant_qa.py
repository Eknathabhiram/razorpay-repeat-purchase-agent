"""Create a fresh private QA login, leaving every existing merchant workspace intact."""
import json,os,secrets,uuid
from app.cli import bootstrap
from app.db import Database
from app.runtime import run
from app.settings import Settings,BACKEND

async def main():
    db=Database(Settings.from_environment().database_url)
    access={'login':'merchant-qa-'+uuid.uuid4().hex[:8],'password':secrets.token_urlsafe(32)}
    try:
        await bootstrap(db,access['login'],access['password'],os.getenv('SHOPIFY_SHOP','repeat-purchase-agent-test.myshopify.com'))
        (BACKEND/'.local/merchant-qa.json').write_text(json.dumps(access),encoding='utf-8')
        print('Fresh merchant QA tenant ready; credentials retained privately.')
    finally:await db.close()

if __name__=='__main__':run(main())
