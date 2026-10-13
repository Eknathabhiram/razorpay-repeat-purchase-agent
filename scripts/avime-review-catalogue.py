"""Add review-only catalogue rows to the linked local synthetic workspace. No provider writes."""
from datetime import datetime, timezone
from uuid import UUID
import sqlalchemy as sa
from app import schema as t
from app.db import Database
from app.settings import Settings
from app.repositories import Scope
from app.planning import put
from app.runtime import run

WORKSPACE=UUID('4b9786d5-3244-4adf-99dc-6e11539f568b')
PRODUCTS=[('aloe-gel','Aloe vera gel · 200 g',29900,180),('hair-oil','Herbal hair oil · 100 ml',49900,124),('shampoo','Herbal shampoo · 250 ml',34900,210),('conditioner','Nourishing conditioner · 200 ml',39900,96),('face-wash','Rose face wash · 100 ml',24900,156),('neem-soap','Neem soap · 100 g',9900,320),('body-lotion','Almond body lotion · 200 ml',44900,88),('wellness-tea','Herbal wellness tea · 100 g',29900,72)]

async def main():
    db=Database(Settings.from_environment().database_url)
    try:
        async with db.unit_of_work() as session:
            workspace=(await session.execute(sa.select(t.workspaces).where(t.workspaces.c.id==WORKSPACE))).mappings().one()
            if workspace['environment']!='demo':raise RuntimeError('Only the local synthetic review workspace may be changed')
            owner=(await session.execute(sa.select(t.memberships.c.user_id).where(t.memberships.c.merchant_id==workspace['merchant_id'],t.memberships.c.role=='owner').limit(1))).scalar_one()
            scope=Scope(workspace['merchant_id'],WORKSPACE,owner,'owner')
            provenance={'source_mode':'simulated','classification':'source_verified','source_ref':'avime-ui-review-catalogue','retrieved_at':datetime.now(timezone.utc).isoformat(),'note':'Illustrative review products, prices and stock; not Shopify merchant inventory.'}
            for key,title,price,stock in PRODUCTS:
                await put(session,scope,t.variants,dict(provider_variant_id='demo:avime:'+key,provider_product_id='demo:avime:'+key,title=title,sku='REVIEW-'+key.upper(),price_minor=price,currency='INR',stock=stock,active=True,provenance=provenance),['provider_variant_id'])
        print('Added eight review catalogue products. Existing products, purchase history and campaign approvals preserved. No provider calls.')
    finally:await db.close()

if __name__=='__main__':run(main())
