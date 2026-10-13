"""Operator-only conversation preview with actual scoped Shopify facts.

This does not grant campaign authority, create carts or masquerade as WhatsApp delivery.
Phone numbers are never sent to the interpretation provider or stored in the transcript.
"""
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Literal
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field
from . import schema as t, planning
from .repositories import ScopedRepository
from .store_view import project_snapshot
from .together_provider import redact
from .errors import ApplicationError

class StartTest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    phone: str=Field(pattern=r'^\+[1-9][0-9]{7,14}$')
    variant_id: str=Field(min_length=1,max_length=160)
    confirmed_own_number: Literal[True]
    confirmed_provider_processing: Literal[True]
    mode: Literal['preview','whatsapp']='preview'

class TestReply(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_version: int=Field(ge=1,le=21)
    choice: Literal['yes','no','price','later','support','not_needed','stop']|None=None
    text: str|None=Field(default=None,min_length=1,max_length=1000)

def button(key,title):return {'id':key,'title':title}
YES_NO=[button('yes','Yes'),button('no','No')]
REASONS=[button('price','Price is high'),button('later','Have enough'),button('support','Product issue')]
def message(direction,text,buttons=None):
    return {'direction':direction,'text':text,'buttons':buttons or [],'at':datetime.now(timezone.utc).isoformat(),'transport':'browser_preview'}

async def catalogue(session,scope,shopify,twilio,together):
    # A Demo owner may explicitly inspect their own connected Development catalogue.
    source=(await session.execute(sa.select(t.workspaces.c.id,t.connectors.c.id.label('connector_id')).select_from(
        t.workspaces.join(t.memberships,t.memberships.c.merchant_id==t.workspaces.c.merchant_id).join(t.connectors,
        sa.and_(t.connectors.c.workspace_id==t.workspaces.c.id,t.connectors.c.merchant_id==t.workspaces.c.merchant_id)))
        .where(t.memberships.c.user_id==scope.user_id,t.workspaces.c.environment=='development',
        t.connectors.c.provider=='shopify',t.connectors.c.source_mode=='test',t.connectors.c.provider_account_id==shopify.shop)
        .order_by(t.workspaces.c.id).limit(1))).mappings().first()
    if not source:raise ApplicationError(422,'SHOPIFY_SOURCE_MISSING','No connected Shopify development source is accessible to this account.')
    store=project_snapshot(await shopify.snapshot())
    return {'shop_name':store.shop_name,'domain':store.domain,'checked_at':store.checked_at,'source_mode':'shopify_test',
        'source_workspace_id':source['id'],'products':[p.model_dump() for p in store.products],
        'agent_configured':together.configured,'whatsapp_enabled':False,
        'whatsapp_blockers':(['Account credentials and WhatsApp sender are missing.'] if not twilio.configured else [])+
        ([] if twilio.callback_base.startswith('https://') else ['A verified HTTPS inbound/status callback is missing.'])+
        ['Exact interactive content and recipient/session authority have not been verified.'],
        'notice':'Shopify catalogue is actual development-store data. Browser preview messages are not sent to your phone.'}

async def log(session,scope,identifier,kind,details,correlation):
    await session.execute(t.audit_events.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
        actor_id=scope.user_id,event_type='whatsapp_test.'+kind,target_id=identifier,correlation_id=correlation,details=jsonable_encoder(details)))

async def view(session,scope,identifier):
    repo=ScopedRepository(session,scope)
    rows=(await session.execute(sa.select(t.audit_events.c.details,t.audit_events.c.created_at).where(repo.where(t.audit_events),
        t.audit_events.c.target_id==identifier,t.audit_events.c.event_type.in_(['whatsapp_test.started','whatsapp_test.reply']))
        .order_by(t.audit_events.c.created_at,t.audit_events.c.id))).mappings().all()
    if not rows or 'product' not in rows[0]['details']:raise ApplicationError(404,'NOT_FOUND','Test conversation not found in this workspace.')
    result=dict(rows[0]['details']);result['id']=str(identifier);result['timeline']=list(result['timeline'])
    for row in rows[1:]:
        detail=row['details'];result['timeline'].extend(detail['timeline']);result['state']=detail['state'];result['version']=detail['version']
        result['agent_receipt']=detail.get('agent_receipt')
    result['expired']=rows[0]['created_at']+timedelta(hours=1)<=datetime.now(timezone.utc)
    return result

async def idempotent(session,scope,operation,key,body,run):
    repo=ScopedRepository(session,scope);await repo.workspace(lock=True)
    hash_value=planning.digest(body)
    await session.execute(insert(t.idempotency).values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,actor_id=scope.user_id,
        operation=operation,key=key,request_hash=hash_value,expires_at=datetime.now(timezone.utc)+timedelta(hours=1)).on_conflict_do_nothing(
        index_elements=[t.idempotency.c.merchant_id,t.idempotency.c.workspace_id,t.idempotency.c.actor_id,t.idempotency.c.operation,t.idempotency.c.key]))
    record=(await session.execute(sa.select(t.idempotency).where(repo.where(t.idempotency),t.idempotency.c.actor_id==scope.user_id,
        t.idempotency.c.operation==operation,t.idempotency.c.key==key).with_for_update())).mappings().one()
    if record['request_hash']!=hash_value:raise ApplicationError(409,'IDEMPOTENCY_CONFLICT','The test request key was used for different content.')
    if record['result_json'] is not None:return record['result_json']
    result=jsonable_encoder(await run())
    await session.execute(t.idempotency.update().where(t.idempotency.c.id==record['id']).values(result_json=result))
    return result

async def start(session,scope,body,key,correlation,shopify,twilio,together):
    async def run():
        if body.mode!='preview':raise ApplicationError(503,'WHATSAPP_TEST_BLOCKED','Real WhatsApp requires configured credentials, a verified sender/recipient, interactive content and public callbacks. No message was sent.')
        if not together.configured:raise ApplicationError(503,'TOGETHER_UNCONFIGURED','Configure the AI provider before starting this test.')
        data=await catalogue(session,scope,shopify,twilio,together)
        product=next((p for p in data['products'] if p['variant_id']==body.variant_id),None)
        if not product:raise ApplicationError(409,'PRODUCT_CHANGED','Select a current Shopify product from the catalogue.')
        if product['stock'] is None or product['stock']<=0:raise ApplicationError(422,'STOCK_UNVERIFIED','A positive verified stock quantity is required.')
        identifier=uuid.uuid4();price=f"{product['currency']} {Decimal(product['price']):,.2f}"
        details={'product':product,'shop_name':data['shop_name'],'product_checked_at':data['checked_at'],
            'recipient_hint':'••••'+body.phone[-4:],
            'version':1,'state':'awaiting_choice','source_mode':'browser_preview','provider_processing':True,'sent_to_phone':False,
            'timeline':[message('outbound',f"Would you like to order {product['title']}? Current item price is {price}. Delivery and taxes are confirmed at checkout. Reply STOP to opt out.",YES_NO)]}
        await log(session,scope,identifier,'started',details,correlation)
        return await view(session,scope,identifier)
    return await idempotent(session,scope,'whatsapp_test.start',key,body,run)

async def reply(session,scope,identifier,body,key,correlation,shopify,twilio,together):
    async def run():
        current=await view(session,scope,identifier)
        if current['version']!=body.expected_version:raise ApplicationError(409,'VERSION_CONFLICT','The conversation changed. Refresh before replying.')
        if current['expired'] or current['version']>=20:raise ApplicationError(422,'TEST_EXPIRED','Start a new test conversation.')
        if current['state'] in ('opted_out','support'):raise ApplicationError(422,'TEST_HELD','This test is stopped or held for support. Start a new test to continue.')
        if bool(body.choice)==bool(body.text):raise ApplicationError(422,'REPLY_INVALID','Choose one button or type one message.')
        available={b['id']:b['title'] for b in current['timeline'][-1]['buttons']}
        if body.choice and body.choice not in available:raise ApplicationError(422,'BUTTON_INVALID','Choose a button from the last displayed message.')
        text=available[body.choice] if body.choice else redact(body.text.strip())
        if not text:raise ApplicationError(422,'REPLY_INVALID','Enter a customer message.')
        # Refresh price/stock before replying. The model never supplies commerce facts.
        data=await catalogue(session,scope,shopify,twilio,together)
        product=next((p for p in data['products'] if p['variant_id']==current['product']['variant_id']),None)
        if not product or product['stock'] is None or product['stock']<=0:raise ApplicationError(409,'PRODUCT_CHANGED','Current product or stock is unavailable. No reply was sent.')
        proposal,receipt=await together.interpret(text,{'test_only':True,'product':product['title'],'sku':product['sku'],'current_price':product['price'],'currency':product['currency'],'no_discount_authority':True})
        intents={i.kind for i in proposal.intents} if not body.choice and proposal.confidence>=0.8 else set();state='awaiting_choice';buttons=[];choice=body.choice
        if choice=='stop' or 'opt_out' in intents or text.lower() in ('stop','unsubscribe'):
            state='opted_out';answer='Understood. This test conversation is stopped. No further test messages will be prepared.'
        elif choice=='support' or 'support' in intents:
            state='support';answer='I will pause the reorder conversation and flag this product issue for the merchant. No checkout will be prepared.'
        elif choice=='no':
            state='awaiting_reason';answer='No problem. What is the main reason you are not interested right now?';buttons=REASONS
        elif choice=='later' or 'reminder' in intents:
            state='awaiting_reminder';answer='Understood. Tell me an exact date and time if you want a reminder. Nothing has been scheduled yet.'
        elif choice=='price' or 'offer_enquiry' in intents or any(w in text.lower() for w in ('price','cost','discount','expensive')):
            answer=f"The current Shopify item price for {product['title']} is {product['currency']} {Decimal(product['price']):,.2f}. No discount is approved for this test. Would you still like to order?";buttons=YES_NO
        elif choice=='yes' or 'purchase_interest' in intents:
            state='awaiting_confirmation';answer=f"Please confirm {product['title']}, quantity 1. Reply with the quantity you want. A real checkout link requires the Storefront connection; this preview does not place an order."
        elif 'refusal' in intents:
            state='awaiting_reason';answer='Understood. Would you like to tell us why?';buttons=REASONS
        else:
            answer=f"I can help with {product['title']}, its current item price, a reminder request or a product issue. Would you like to order it?";buttons=YES_NO
        receipt={k:receipt.get(k) for k in ('provider','model','latency_ms','attempts')}
        detail={'version':current['version']+1,'state':state,'agent_receipt':receipt,
            'timeline':[message('inbound',text),message('outbound',answer,buttons)]}
        await log(session,scope,identifier,'reply',detail,correlation)
        return await view(session,scope,identifier)
    return await idempotent(session,scope,'whatsapp_test.reply:'+str(identifier),key,body,run)
