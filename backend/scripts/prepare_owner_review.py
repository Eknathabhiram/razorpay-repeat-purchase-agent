"""Add an isolated synthetic 200-customer review workspace to an existing owner login.

Existing workspaces, policies, credentials, orders and approvals are never changed.
The new cohort is a draft only. The merchant must perform its initial approval.
"""
import argparse,json,uuid
import sqlalchemy as sa
from app import schema as t,planning,scale_demo
from app.db import Database
from app.runtime import run
from app.repositories import Scope,ScopedRepository
from app.settings import Settings,BACKEND
from app.planning_models import PolicyConfig,PolicyChange,DraftChange

NAME='D2C review · 200 customers'

async def prepare(source_workspace):
    db=Database(Settings.from_environment().database_url)
    try:
        async with db.unit_of_work() as session:
            # Resolve the existing owner from the explicitly selected workspace.
            source=(await session.execute(sa.select(t.workspaces).where(t.workspaces.c.id==source_workspace))).mappings().one()
            owner=(await session.execute(sa.select(t.memberships.c.user_id).where(t.memberships.c.merchant_id==source['merchant_id'],t.memberships.c.role=='owner'))).scalar_one()
            login=await session.scalar(sa.select(t.users.c.login_identifier).where(t.users.c.id==owner,t.users.c.disabled_at.is_(None)))
            local_owner=json.loads((BACKEND/'.local/owner-access.json').read_text(encoding='utf-8'))
            if login!=local_owner['login']:raise RuntimeError('Selected workspace does not belong to the configured local owner.')
            old=(await session.execute(sa.select(t.workspaces).join(t.memberships,t.memberships.c.merchant_id==t.workspaces.c.merchant_id).where(t.memberships.c.user_id==owner,t.workspaces.c.name==NAME,t.workspaces.c.environment=='demo'))).mappings().first()
            if old:
                scope=Scope(old['merchant_id'],old['id'],owner,'owner');repo=ScopedRepository(session,scope)
                approved=await session.scalar(sa.select(sa.func.count()).select_from(t.approvals).where(repo.where(t.approvals),t.approvals.c.resource_type=='plan',t.approvals.c.decision=='approve'))
                current=await planning.latest(session,repo,t.policies)
                desired=PolicyConfig(variant_ids=['demo:laundry:1L'],fallback_days=30,mode='bounded',conversation_automation=True,contextual_replies=True,provider_processing=True,contact_start='00:00',contact_end='23:59',contact_cap=10,budget_minor=50000)
                if not approved and current and current['config_json']!=desired.model_dump(mode='json'):
                    await planning.command(session,scope,'policy',PolicyChange(expected_revision=current['revision'],config=desired),uuid.uuid4(),uuid.uuid4())
                    data=await planning.view(session,scope)
                    await planning.command(session,scope,'draft',DraftChange(expected_revision=data.draft['revision'] if data.draft else 0,selected=[item['id'] for item in data.opportunities if item['eligible']]),uuid.uuid4(),uuid.uuid4())
                print(json.dumps({'workspace_id':str(old['id']),'name':NAME,'reused':True}));return
            merchant_id,workspace_id=uuid.uuid4(),uuid.uuid4()
            await session.execute(t.merchants.insert().values(id=merchant_id,name='D2C review brand',default_timezone='Asia/Kolkata',currency='INR'))
            await session.execute(t.memberships.insert().values(merchant_id=merchant_id,user_id=owner,role='owner'))
            await session.execute(t.workspaces.insert().values(id=workspace_id,merchant_id=merchant_id,environment='demo',name=NAME))
            for provider,caps in {'shopify':['read_catalogue','read_customers','read_orders','prepare_checkout'],'razorpay':['read_payment_evidence','reconcile_payment'],'twilio':['trial_template_send','receive_inbound','receive_status'],'voice':['browser_audio'],'support':['internal_cases']}.items():
                connector_id=uuid.uuid4()
                await session.execute(t.connectors.insert().values(id=connector_id,merchant_id=merchant_id,workspace_id=workspace_id,provider=provider,provider_account_id=None,source_mode='simulated',provider_environment='fixture',credential_ref=None,state='not_connected'))
                for capability in caps:await session.execute(t.capabilities.insert().values(merchant_id=merchant_id,workspace_id=workspace_id,connector_id=connector_id,capability=capability,status='unverified',reason='Synthetic review workspace; no external provider authority.'))
            scope=Scope(merchant_id,workspace_id,owner,'owner')
            await scale_demo.seed(session,scope)
            config=PolicyConfig(variant_ids=['demo:laundry:1L'],fallback_days=30,mode='bounded',conversation_automation=True,contextual_replies=True,provider_processing=True,contact_start='00:00',contact_end='23:59',contact_cap=10,budget_minor=50000)
            await planning.command(session,scope,'policy',PolicyChange(expected_revision=0,config=config),uuid.uuid4(),uuid.uuid4())
            data=await planning.view(session,scope)
            await planning.command(session,scope,'draft',DraftChange(expected_revision=0,selected=[item['id'] for item in data.opportunities if item['eligible']]),uuid.uuid4(),uuid.uuid4())
            await session.execute(t.audit_events.insert().values(merchant_id=merchant_id,workspace_id=workspace_id,actor_id=owner,event_type='review_workspace.prepared',target_id=workspace_id,correlation_id=uuid.uuid4(),details={'source_mode':'simulated','customer_count':200,'initial_approval_required':True}))
            print(json.dumps({'workspace_id':str(workspace_id),'name':NAME,'customer_count':200,'eligible_count':160,'initial_approval_required':True}))
    finally:await db.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source-workspace',type=uuid.UUID,required=True)
    run(prepare(parser.parse_args().source_workspace))
