"""Durable, policy-bound Demo conversations. No customer payment or real transport authority."""
import asyncio
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from . import schema as t, planning, execution, commerce
from .repositories import ScopedRepository, Scope
from .errors import ApplicationError
from .commerce_models import CartRequest
from .interaction_content import choices, followup_text

CONSUMER='bounded.conversations.v1'
PROTECTED=('opted_out','support','purchased','purchase_under_review','refused','unknown_outcome')

async def enabled(session,scope):
    repo=ScopedRepository(session,scope)
    policy=await planning.latest(session,repo,t.policies)
    return bool(policy and policy['config_json']['mode']=='bounded' and policy['config_json'].get('conversation_automation'))

def content(response,variant):
    """Render only allowlisted facts and reviewed style. A model cannot author money or links."""
    step=response['step'];qty=response.get('quantity',1)
    if step in ('confirm_item','choose_reminder'):
        text=followup_text(step,variant['title'],qty)
        if step=='confirm_item' and response.get('offer_ref'):
            text+=f" Approved offer {response['offer_ref']}: INR {response['discount_minor']/100:.2f} off this cart. Final charges are shown at checkout."
        return text,choices(step,qty)
    if step=='change_quantity':return 'How many of the same item would you like? Please choose 1–20. We will confirm the item and quantity before checkout.',[]
    if step=='confirm_reminder':
        local=planning.date(response['due_at']).astimezone(ZoneInfo('Asia/Kolkata'))
        return f"Confirm a WhatsApp reminder for {variant['title']} on {local.strftime('%d %b %Y at %H:%M')} IST?",[{'id':'confirm_reminder','title':'Confirm reminder'},{'id':'change_reminder','title':'Change date'}]
    if step=='reminder_saved':
        local=planning.date(response['due_at']).astimezone(ZoneInfo('Asia/Kolkata'))
        return f"Your WhatsApp reminder for {variant['title']} is saved for {local.strftime('%d %b %Y at %H:%M')} IST. Reply STOP to opt out.",[]
    if step=='facts':
        text=f"{variant['title']} is the same variant from your delivered order. The current item price is INR {variant['price_minor']/100:.2f}. Shipping, tax and final payable are shown at checkout."
        if response.get('offer_enquiry'):text+=' Only an offer approved for this product and your checkout can be applied. No discount has been added.'
        return text+' Would you like to reorder or choose a reminder?',choices('reorder_check')
    if step=='clarify':return 'Would you like to reorder the same item, choose a reminder, or get help? You can also type your question.',choices('reorder_check')
    raise ValueError('Unsupported response')

async def exception(session,scope,journey,reason):
    repo=ScopedRepository(session,scope)
    await execution.hold_customer(session,scope,journey['customer_id'],reason,cancel=True)
    if journey['state'] not in PROTECTED:
        await session.execute(t.journeys.update().where(repo.where(t.journeys),t.journeys.c.id==journey['id']).values(state='reply_review',owner_id=scope.user_id))
    await execution.emit(session,scope,'conversation.exception',journey['id'],{'reason':reason,'source_mode':'simulated'})

async def sent_action(session,repo,journey,identifier=None):
    query=sa.select(t.proposed_actions).join(t.dispatch_attempts,t.dispatch_attempts.c.action_id==t.proposed_actions.c.id).join(t.action_receipts,t.action_receipts.c.attempt_id==t.dispatch_attempts.c.id).where(
        repo.where(t.proposed_actions),repo.where(t.dispatch_attempts),repo.where(t.action_receipts),t.proposed_actions.c.journey_id==journey['id'],t.action_receipts.c.status=='submitted')
    if identifier:query=query.where(t.proposed_actions.c.id==identifier)
    return (await session.execute(query.order_by(t.action_receipts.c.created_at.desc()).limit(1))).mappings().first()

def exact_date(text):
    # Relative dates remain a question. Never guess a date, hour or timezone from model output.
    match=re.search(r'\b(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})(?::\d{2})?\s*(IST|\+05:30|Z|[+-]\d{2}:\d{2})',text,re.I)
    if not match:return None
    try:return datetime.fromisoformat(match[1]+'T'+match[2]+(':00+05:30' if match[3].upper()=='IST' else ':00'+match[3].upper().replace('Z','+00:00')))
    except ValueError:return None

async def reply(session,scope,journey,policy,draft,event,variant,response):
    now=datetime.now(timezone.utc);text,buttons=content(response,variant)
    customer=await execution.scoped_one(session,ScopedRepository(session,scope),t.customers,journey['customer_id'])
    payload={'customer_id':str(journey['customer_id']),'variant_id':str(variant['id']),'provider_variant_id':variant['provider_variant_id'],
        'customer_alias':customer['display_alias'],'variant_title':variant['title'],'kind':'automated_reply','channel':'whatsapp',
        'text':text,'reply_buttons':buttons,'response':response,'conversation_event_id':str(event['id']),
        'policy_id':str(policy['id']),'plan_revision_id':str(draft['id']),'source_mode':'simulated','cost_minor':25,'currency':'INR'}
    await execution.create_action(session,scope,journey,policy,payload,now,min(draft['expires_at'],event['created_at']+timedelta(hours=24)),auto=True)

async def checkout(session,scope,journey,policy,draft,event,quantity,offer_ref=None):
    repo=ScopedRepository(session,scope);now=datetime.now(timezone.utc)
    quoted=await commerce.quote(session,scope,CartRequest(journey_id=journey['id'],quantity=quantity,confirmed_same_product=True,confirmed_whatsapp_handoff=True,offer_ref=offer_ref))
    identifier=uuid.uuid4();expires=min(quoted['expires_at'],event['created_at']+timedelta(hours=24))
    prepared={'id':identifier,'terms_json':quoted['terms'],'digest':quoted['digest'],'checkout_url':'/app/#/commerce?cart='+str(identifier),'expires_at':expires}
    await session.execute(t.checkout_preparations.update().where(repo.where(t.checkout_preparations),t.checkout_preparations.c.journey_id==journey['id'],t.checkout_preparations.c.state.in_(('prepared','link_proposed'))).values(state='superseded'))
    await session.execute(t.checkout_preparations.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,journey_id=journey['id'],state='prepared',**{k:v for k,v in prepared.items()}))
    payload={'customer_id':str(journey['customer_id']),'variant_id':quoted['terms']['variant_id'],'provider_variant_id':quoted['terms']['provider_variant_id'],
        'customer_alias':(await execution.scoped_one(session,repo,t.customers,journey['customer_id']))['display_alias'],
        'variant_title':quoted['terms']['title'],'kind':'checkout_link','channel':'whatsapp','text':commerce.link_text(prepared),
        'cost_minor':25+quoted['terms']['discount_minor'],'currency':'INR','source_mode':'simulated','preparation_id':str(identifier),'terms_digest':quoted['digest'],
        'plan_revision_id':str(draft['id']),'policy_id':str(policy['id']),'conversation_event_id':str(event['id'])}
    action=await execution.create_action(session,scope,journey,policy,payload,now,expires,auto=True)
    await session.execute(t.checkout_preparations.update().where(repo.where(t.checkout_preparations),t.checkout_preparations.c.id==identifier).values(link_action_id=action,state='link_proposed'))
    await session.execute(t.journeys.update().where(repo.where(t.journeys),t.journeys.c.id==journey['id']).values(state='checkout_pending'))
    await execution.emit(session,scope,'checkout.automated',identifier,{'customer_confirmation_event':str(event['id']),'quantity':quantity,'source_mode':'simulated'})

async def process(session,scope,outbox,provider):
    repo=ScopedRepository(session,scope);now=datetime.now(timezone.utc)
    journey=(await session.execute(sa.select(t.journeys).where(repo.where(t.journeys),t.journeys.c.customer_id==outbox['subject_id']).order_by(t.journeys.c.created_at.desc()).limit(1))).mappings().first()
    if not journey or journey['owner_id'] or journey['state'] in PROTECTED:return
    policy=await planning.latest(session,repo,t.policies);draft=await planning.latest(session,repo,t.plan_revisions)
    if not policy or not draft or draft['id']!=journey['plan_revision_id'] or draft['policy_id']!=policy['id'] or draft['expires_at']<=now:
        await exception(session,scope,journey,'plan_requires_renewal');return
    approved=await execution.existing_approval(session,repo,'plan',draft['id'])
    if not approved or approved['decision']!='approve':return
    event=(await session.execute(sa.select(t.whatsapp_events).where(repo.where(t.whatsapp_events),t.whatsapp_events.c.customer_id==journey['customer_id'],
        t.whatsapp_events.c.message_ref==outbox['details'].get('message_ref'),t.whatsapp_events.c.kind=='inbound'))).mappings().first()
    if not event or event['source_mode']!='simulated':return
    newest=await session.scalar(sa.select(t.whatsapp_events.c.id).where(repo.where(t.whatsapp_events),t.whatsapp_events.c.customer_id==journey['customer_id'],t.whatsapp_events.c.kind=='inbound').order_by(t.whatsapp_events.c.created_at.desc(),t.whatsapp_events.c.id.desc()).limit(1))
    if newest!=event['id']:return
    if event['created_at']+timedelta(hours=24)<=now:await exception(session,scope,journey,'customer_window_expired');return
    variant=await execution.scoped_one(session,repo,t.variants,journey['variant_id'])
    fresh=await planning.compute(session,scope,customer_id=journey['customer_id'])
    if not any(i['variant_id']==str(variant['id']) and i['eligible'] for i in fresh):await exception(session,scope,journey,'facts_or_permission_changed');return
    inflight=await session.scalar(sa.select(t.contact_guards.c.inflight_action_id).where(repo.where(t.contact_guards),t.contact_guards.c.customer_id==journey['customer_id']))
    if inflight:await exception(session,scope,journey,'delivery_uncertain');return
    button=(await session.execute(sa.select(t.event_outbox).where(repo.where(t.event_outbox),t.event_outbox.c.event_type=='whatsapp.button',
        t.event_outbox.c.subject_id==journey['customer_id'],t.event_outbox.c.details['message_ref'].astext==event['message_ref']))).mappings().first()
    source=await sent_action(session,repo,journey);button_id=None
    if button:
        try:action_id,value=button['details']['payload'].rsplit(':',1);action_id=uuid.UUID(action_id)
        except (ValueError,KeyError):await exception(session,scope,journey,'button_context_missing');return
        if not source or source['id']!=action_id or not any(b['id']==value for b in source['payload'].get('reply_buttons',[])):
            await exception(session,scope,journey,'stale_customer_choice');return
        button_id=value
    if not source:await exception(session,scope,journey,'conversation_context_missing');return
    if button_id=='same_item':
        if source['payload'].get('response',{}).get('step',source['payload'].get('interaction_step'))!='confirm_item':await exception(session,scope,journey,'item_confirmation_missing');return
        await checkout(session,scope,journey,policy,draft,event,source['payload'].get('response',{}).get('quantity',source['payload'].get('quantity',1)),source['payload'].get('response',{}).get('offer_ref'));return
    response=None
    if button_id=='confirm_reminder':
        response=source['payload'].get('response',{})
        due=planning.date(response.get('due_at')) if response.get('step')=='confirm_reminder' else None
        local=due.astimezone(ZoneInfo('Asia/Kolkata')) if due else None
        if not due or not now<due<draft['expires_at'] or not policy['config_json']['contact_start']<=local.strftime('%H:%M')<policy['config_json']['contact_end']:
            await exception(session,scope,journey,'reminder_outside_approved_limits');return
        await session.execute(t.reminders.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,journey_id=journey['id'],event_key=event['id'],due_at=due,timezone='Asia/Kolkata',channel='whatsapp',state='scheduled'))
        await session.execute(t.customer_evidence.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,customer_id=journey['customer_id'],kind='reminder',value={'date':due.isoformat(),'timezone':'Asia/Kolkata','channel':'whatsapp','variant_id':str(variant['id'])},effective_at=now,provenance={'source_mode':'simulated','classification':'customer_stated','source_ref':event['message_ref'],'retrieved_at':now.isoformat()}))
        payload={**source['payload'],'kind':'reminder','text':"As requested, here's your reminder about "+variant['title']+". Would you like to reorder the same product?",'reply_buttons':choices('reminder'),'confirmed_event_key':str(event['id']),'timezone':'Asia/Kolkata'}
        for key in ('response','conversation_event_id'):payload.pop(key,None)
        await execution.create_action(session,scope,journey,policy,payload,due,draft['expires_at'],auto=True)
        await reply(session,scope,journey,policy,draft,event,variant,{'step':'reminder_saved','due_at':due.isoformat()});return
    if button_id=='reorder':response={'step':'confirm_item','quantity':1}
    elif button_id in ('remind_later','change_reminder'):response={'step':'choose_reminder'}
    elif button_id=='change_quantity':response={'step':'change_quantity'}
    else:
        from .intelligence import baseline, preserve_explicit_intents
        text=event['text'];proposal=baseline(text)
        if policy['config_json'].get('contextual_replies'):
            proposal,receipt=await provider.interpret(text,{'same_product':variant['title'],'timezone':'Asia/Kolkata','last_business_message':source['payload']['text'][:1000]})
            proposal=preserve_explicit_intents(proposal,text)
            await execution.emit(session,scope,'conversation.interpreted',event['id'],{'proposal':proposal.model_dump(),'receipt':receipt,'source_mode':'simulated'})
        kinds={i.kind for i in proposal.intents}
        if kinds.intersection(('opt_out','support','refusal')):
            from .whatsapp import protect
            classification=next(k for k in ('opt_out','support','refusal') if k in kinds)
            await protect(session,scope,journey['customer_id'],classification,event['message_ref'],'simulated');return
        if 'purchase_claim' in kinds:await exception(session,scope,journey,'payment_evidence_required');return
        if proposal.requested_product and proposal.requested_product.lower() not in ('same','same product','same item','this product','this item','it',variant['title'].lower()):
            await exception(session,scope,journey,'product_outside_approved_scope');return
        if proposal.confidence<0.7:await exception(session,scope,journey,'missing_customer_facts');return
        due=exact_date(text)
        if 'reminder' in kinds or due:
            if due and not now<due<draft['expires_at']:await exception(session,scope,journey,'reminder_outside_approved_limits');return
            response={'step':'confirm_reminder','due_at':due.isoformat()} if due else {'step':'choose_reminder'}
        elif re.search(r'\b(price|cost)\b',text,re.I) and not re.search(r'\b(coupon|discount|offer|promotion)\b',text,re.I):
            response={'step':'facts'}
        elif 'offer_enquiry' in kinds:
            refs=policy['config_json'].get('approved_offer_refs',[])
            requested=next((ref for ref in refs if ref.lower() in text.lower()),refs[0] if len(refs)==1 else None)
            if not policy['config_json'].get('offers_enabled') or not requested or re.search(r'\b(bigger|extra|more|negotiate)\b|\d+\s*%',text,re.I):
                await exception(session,scope,journey,'offer_request_outside_approved_limits');return
            quoted=await commerce.quote(session,scope,CartRequest(journey_id=journey['id'],quantity=proposal.quantity or 1,confirmed_same_product=True,confirmed_whatsapp_handoff=True,offer_ref=requested))
            response={'step':'confirm_item','quantity':proposal.quantity or 1,'offer_ref':requested,'discount_minor':quoted['terms']['discount_minor']}
        elif 'purchase_interest' in kinds or proposal.quantity:
            response={'step':'confirm_item','quantity':proposal.quantity or 1}
        elif re.search(r'\b(price|cost|item|product)\b',text,re.I):response={'step':'facts'}
        elif source['payload'].get('response',{}).get('step')=='clarify':
            await exception(session,scope,journey,'missing_customer_facts');return
        else:response={'step':'clarify'}
    await reply(session,scope,journey,policy,draft,event,variant,response)

async def run_conversations(db,scope,provider,limit=20):
    async with db.unit_of_work() as session:
        repo=ScopedRepository(session,scope);await repo.workspace(lock=True)
        if not await enabled(session,scope):return
        agent=await execution.agent(session,scope)
        if not agent or agent['paused']:return
        consumed=sa.exists(sa.select(t.event_consumptions.c.id).where(repo.where(t.event_consumptions),t.event_consumptions.c.event_id==t.event_outbox.c.id,t.event_consumptions.c.consumer==CONSUMER))
        events=(await session.execute(sa.select(t.event_outbox).where(repo.where(t.event_outbox),t.event_outbox.c.event_type=='whatsapp.inbound',~consumed).order_by(t.event_outbox.c.created_at,t.event_outbox.c.id).limit(limit))).mappings().all()
        for event in events:
            try:
                async with session.begin_nested():await process(session,scope,event,provider)
            except ApplicationError as error:
                journey=(await session.execute(sa.select(t.journeys).where(repo.where(t.journeys),t.journeys.c.customer_id==event['subject_id']).order_by(t.journeys.c.created_at.desc()).limit(1))).mappings().first()
                if journey:await exception(session,scope,journey,error.code.lower())
            await session.execute(insert(t.event_consumptions).values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,event_id=event['id'],consumer=CONSUMER).on_conflict_do_nothing(index_elements=[t.event_consumptions.c.merchant_id,t.event_consumptions.c.workspace_id,t.event_consumptions.c.event_id,t.event_consumptions.c.consumer]))

async def validate_reply(session,scope,action,journey,variant,now):
    repo=ScopedRepository(session,scope)
    if not await enabled(session,scope):return 'conversation_mandate_changed'
    try:event=await execution.scoped_one(session,repo,t.whatsapp_events,uuid.UUID(action['payload']['conversation_event_id']))
    except (KeyError,ValueError,ApplicationError):return 'conversation_proof_missing'
    if event['customer_id']!=journey['customer_id'] or event['kind']!='inbound' or event['source_mode']!='simulated':return 'conversation_scope_changed'
    if event['created_at']+timedelta(hours=24)<=now:return 'customer_window_expired'
    if action['payload']['kind']=='automated_reply':
        response=action['payload'].get('response',{});qty=response.get('quantity',1)
        if type(qty) is not int or not 1<=qty<=20:return 'quantity_outside_approved_limits'
        if response.get('offer_ref'):
            try:quoted=await commerce.quote(session,scope,CartRequest(journey_id=journey['id'],quantity=qty,confirmed_same_product=True,confirmed_whatsapp_handoff=True,offer_ref=response['offer_ref']))
            except ApplicationError as error:return error.code.lower()
            if quoted['terms']['discount_minor']!=response.get('discount_minor'):return 'offer_terms_changed'
        try:text,buttons=content(action['payload']['response'],variant)
        except (KeyError,ValueError,TypeError):return 'conversation_content_invalid'
        if action['payload']['text']!=text or action['payload'].get('reply_buttons',[])!=buttons:return 'conversation_content_changed'
    elif action['payload']['kind']=='checkout_link':
        button=(await session.execute(sa.select(t.event_outbox).where(repo.where(t.event_outbox),t.event_outbox.c.event_type=='whatsapp.button',t.event_outbox.c.subject_id==journey['customer_id'],t.event_outbox.c.details['message_ref'].astext==event['message_ref']))).mappings().first()
        try:
            identifier,choice=button['details']['payload'].rsplit(':',1)
            source=await sent_action(session,repo,journey,uuid.UUID(identifier))
            prepared=await execution.scoped_one(session,repo,t.checkout_preparations,uuid.UUID(action['payload']['preparation_id']))
        except (TypeError,KeyError,ValueError,ApplicationError):return 'customer_confirmation_missing'
        response=source['payload'].get('response',{}) if source else {}
        if choice!='same_item' or response.get('step')!='confirm_item' or response.get('quantity')!=prepared['terms_json']['quantity'] or response.get('offer_ref')!=prepared['terms_json']['offer_ref']:return 'customer_confirmation_changed'
    return None

async def background(db,provider):
    """Only opted-in Demo mandates. Leases and customer guards arbitrate multiple workers."""
    from . import worker
    while True:
        try:
            async with db.unit_of_work() as session:
                rows=(await session.execute(sa.select(t.workspaces.c.id,t.workspaces.c.merchant_id,t.memberships.c.user_id).join(t.memberships,t.memberships.c.merchant_id==t.workspaces.c.merchant_id).join(t.agents,sa.and_(t.agents.c.workspace_id==t.workspaces.c.id,t.agents.c.merchant_id==t.workspaces.c.merchant_id)).where(t.workspaces.c.environment=='demo',t.memberships.c.role=='owner',~t.agents.c.paused))).all()
            for workspace_id,merchant_id,user_id in rows:
                scope=Scope(merchant_id,workspace_id,user_id,'owner')
                async with db.unit_of_work() as session:auto=await enabled(session,scope)
                if auto:
                    await run_conversations(db,scope,provider)
                    await worker.run_once(db,scope,limit=10)
        except asyncio.CancelledError:raise
        except Exception:
            logging.getLogger('rpa.automation').error('Automatic Demo processing paused for this cycle; no exception content logged.')
        await asyncio.sleep(2)
