"""Optional local read-only polling fallback; no callback registration or public exposure."""
import argparse
import asyncio
import uuid
import sqlalchemy as sa
from . import schema as t,commerce
from .db import Database
from .settings import Settings
from .repositories import Scope
from .runtime import run
from .payment_sources import RazorpayReadOnly
from shopify_app import connector


async def main(workspace_id,once):
    db=Database(Settings.from_environment().database_url)
    try:
        async with db.unit_of_work() as session:
            workspace=(await session.execute(sa.select(t.workspaces).where(t.workspaces.c.id==workspace_id,t.workspaces.c.environment=="development"))).mappings().one()
            owner=await session.scalar(sa.select(t.memberships.c.user_id).where(t.memberships.c.merchant_id==workspace["merchant_id"],t.memberships.c.role=="owner"))
            scope=Scope(workspace["merchant_id"],workspace_id,owner,"owner")
        while True:
            async with db.unit_of_work() as session:await commerce.sync(session,scope,RazorpayReadOnly(),connector)
            print("Read-only payment evidence refreshed.",flush=True)
            if once:break
            await asyncio.sleep(300)
    finally:await db.close()


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--workspace",type=uuid.UUID,required=True);parser.add_argument("--once",action="store_true")
    args=parser.parse_args();run(main(args.workspace,args.once))
