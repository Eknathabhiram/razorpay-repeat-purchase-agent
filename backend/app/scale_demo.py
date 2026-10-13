"""Large synthetic cohort in an empty Demo workspace; never replaces existing facts."""
import uuid
from datetime import datetime,timedelta,timezone
import sqlalchemy as sa
from . import schema as t,planning
from .repositories import ScopedRepository
from .errors import ApplicationError

async def seed(session,scope,count=200):
    repo=ScopedRepository(session,scope)
    if (await repo.workspace())['environment']!='demo':raise ApplicationError(422,'SIMULATION_ONLY','Scale fixtures require an empty Demo workspace.')
    if await session.scalar(sa.select(sa.func.count()).select_from(t.customers).where(repo.where(t.customers))) or await planning.rows(session,repo,t.sync_checkpoints):
        raise ApplicationError(409,'WORKSPACE_NOT_EMPTY','Existing source facts are preserved. Use an empty Demo workspace for a scale sample.')
    now=datetime.now(timezone.utc);provenance={'source_mode':'simulated','classification':'source_verified','source_ref':'d2c-scale-fixture-v1','retrieved_at':now.isoformat()}
    variant=await planning.put(session,scope,t.variants,dict(provider_variant_id='demo:laundry:1L',provider_product_id='demo:laundry',title='Laundry liquid · 1 L',sku='DEMO-LAUNDRY-1L',price_minor=49900,currency='INR',stock=100000,active=True,provenance=provenance),['provider_variant_id'])
    common={'merchant_id':scope.merchant_id,'workspace_id':scope.workspace_id}
    for start in range(0,count,250):
        customers=[];events=[];orders=[];lines=[]
        for index in range(start,min(start+250,count)):
            identifier=uuid.uuid4();order_id=uuid.uuid4();city=['Mumbai','Bengaluru','Hyderabad','Delhi','Pune'][index%5]
            no_consent=index%10==8;recent=index%10==9;age=2 if recent else 28+index%7
            customers.append({**common,'id':identifier,'provider_customer_id':f'demo:scale:{index:05}','display_alias':f'Customer {index+1:05}','identity_state':'synthetic'})
            for kind,value in [('consent',{'granted':not no_consent,'channel':'whatsapp','purpose':'replenishment'}),('suppression',{'active':False}),('support',{'open':False}),('campaign',{'blocked':False}),('location',{'city':city})]:
                events.append({**common,'customer_id':identifier,'kind':kind,'value':value,'effective_at':now,'provenance':provenance})
            orders.append({**common,'id':order_id,'provider_order_id':f'demo:scale:order:{index}','customer_id':identifier,'placed_at':now-timedelta(days=age+2),'financial_state':'PAID','fulfilment_state':'DELIVERED','total_minor':49900,'currency':'INR','provenance':provenance})
            lines.append({**common,'order_id':order_id,'provider_line_id':f'demo:scale:line:{index}','variant_id':variant['id'],'quantity':1,'refunded_quantity':0,'delivery_at':now-timedelta(days=age),'return_state':'NONE','coverage_complete':True,'provenance':provenance})
        for table,values in [(t.customers,customers),(t.customer_evidence,events),(t.commerce_orders,orders),(t.order_lines,lines)]:await session.execute(table.insert(),values)
    await planning.put(session,scope,t.sync_checkpoints,dict(resource='commerce',cursor=None,facts_version=1,coverage_complete=True,notes=[f'{count:,} synthetic D2C customers. No customer outreach or real payment authority.'],source_mode='simulated',synced_at=now),['resource'])
