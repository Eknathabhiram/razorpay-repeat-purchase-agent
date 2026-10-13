"""Signed WhatsApp ingress shares the execution customer guard. No inferred consent."""
import re
from datetime import datetime, timezone
from urllib.parse import parse_qsl
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from . import schema as t, planning, execution
from .errors import ApplicationError
from .repositories import Scope, ScopedRepository
from .whatsapp_models import WhatsAppView
from .whatsapp_transport import ADDRESS, SID, STATUSES, RequestValidator, validate_signature
from .interaction_content import choices, followup_text

def classify(text):
    words=re.findall(r'[a-z]+',text.lower())
    if any(w in words for w in ('stop','unsubscribe','optout')) or 'opt out' in text.lower() or 'do not contact' in text.lower(): return 'opt_out'
    if any(w in words for w in ('refund','return','damaged','broken','complaint','support','wrong','help')) or 'not arrived' in text.lower(): return 'support'
    if any(w in words for w in ('no','decline','refuse')) or 'not interested' in text.lower(): return 'refusal'
    if any(w in words for w in ('later','remind','tomorrow','week')): return 'reminder_request'
    if any(w in words for w in ('reorder','yes','buy','order')): return 'purchase_interest'
    return 'needs_review'

async def connector(session,scope):
    repo=ScopedRepository(session,scope)
    row=(await session.execute(sa.select(t.connectors).where(repo.where(t.connectors),t.connectors.c.provider=='twilio'))).mappings().first()
    if not row: raise ApplicationError(422,'CONNECTOR_MISSING','Twilio connector is unavailable in this workspace.')
    return row

async def protect(session,scope,customer_id,classification,event_ref,source_mode):
    repo=ScopedRepository(session,scope); now=datetime.now(timezone.utc)
    await execution.hold_customer(session,scope,customer_id,'whatsapp_'+classification,cancel=True)
    journeys=list((await session.execute(sa.select(t.journeys).where(repo.where(t.journeys),t.journeys.c.customer_id==customer_id))).mappings())
    await session.execute(t.reminders.update().where(repo.where(t.reminders),t.reminders.c.journey_id.in_([j['id'] for j in journeys]),t.reminders.c.state=='scheduled').values(state='cancelled'))
    state={'opt_out':'opted_out','support':'support','refusal':'refused','not_now':'refused','reminder_request':'reply_review','purchase_interest':'reply_review','needs_review':'reply_review'}[classification]
    from .automation import enabled
    automated=source_mode=='simulated' and classification not in ('opt_out','support','refusal','not_now') and await enabled(session,scope)
    for journey in journeys:
        if journey['state']=='opted_out' and classification!='opt_out': continue
        if journey['state'] in ('purchased','purchase_under_review','support','unknown_outcome') and classification not in ('opt_out','support'): continue
        auto=automated and not journey['owner_id'] and journey['state'] not in ('unknown_outcome',)
        await session.execute(t.journeys.update().where(repo.where(t.journeys),t.journeys.c.id==journey['id']).values(state='contacted' if auto else state,owner_id=journey['owner_id'] if classification=='not_now' else None if auto else journey['owner_id'] or scope.user_id))
        if classification=='support':
            await session.execute(insert(t.support_cases).values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,journey_id=journey['id'],state='open',owner_id=scope.user_id).on_conflict_do_nothing(index_elements=[t.support_cases.c.merchant_id,t.support_cases.c.workspace_id,t.support_cases.c.journey_id]))
    if classification in ('opt_out','support','refusal'):
        kind,value={'opt_out':('suppression',{'active':True}),'support':('support',{'open':True}),'refusal':('suppression',{'active':True,'reason':'refusal'})}[classification]
        await session.execute(t.customer_evidence.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,customer_id=customer_id,kind=kind,value=value,effective_at=now,
            provenance={'source_mode':source_mode,'classification':'customer_stated','source_ref':event_ref,'retrieved_at':now.isoformat()}))
    await execution.emit(session,scope,'whatsapp.inbound',customer_id,{'classification':classification,'source_mode':source_mode,'message_ref':event_ref})

async def accept_inbound(session,scope,conn,params,source_mode,button_classification=None):
    repo=ScopedRepository(session,scope); await repo.workspace(lock=True)
    sid=params['MessageSid']; key=sid+':inbound'; hash_value=planning.digest(params)
    old=(await session.execute(sa.select(t.whatsapp_events).where(repo.where(t.whatsapp_events),t.whatsapp_events.c.connector_id==conn['id'],t.whatsapp_events.c.event_key==key))).mappings().first()
    if old:
        if old['payload_hash']!=hash_value: raise ApplicationError(409,'EVENT_CONFLICT','Message reference was reused with different content.')
        return
    identity=(await session.execute(sa.select(t.whatsapp_identities).where(repo.where(t.whatsapp_identities),t.whatsapp_identities.c.connector_id==conn['id'],t.whatsapp_identities.c.address==params['From'],t.whatsapp_identities.c.source_mode==source_mode))).mappings().first()
    customer_id=identity['customer_id'] if identity else None
    classification=classify(params.get('Body','')) if identity else 'unmapped_identity'
    if identity and button_classification and classification not in ('opt_out','support'):
        classification=button_classification
    await session.execute(t.whatsapp_events.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,connector_id=conn['id'],event_key=key,payload_hash=hash_value,kind='inbound',customer_id=customer_id,message_ref=sid,
        text=params.get('Body','') if identity else None,classification=classification,source_mode=source_mode,state='processed' if identity else 'quarantined'))
    if identity: await protect(session,scope,customer_id,classification,sid,source_mode)
    if identity and params.get('ButtonPayload'):
        await execution.emit(session,scope,'whatsapp.button',customer_id,{'message_ref':sid,'payload':params['ButtonPayload']})

async def demo_choice(session,scope,body):
    """Replay a received choice only for a submitted, exact, scoped Demo message."""
    repo=ScopedRepository(session,scope);workspace=await repo.workspace(lock=True)
    if workspace['environment']!='demo': raise ApplicationError(422,'SIMULATION_ONLY','Customer replay is only available in Demo.')
    action=await execution.scoped_one(session,repo,t.proposed_actions,body.action_id)
    journey=await execution.scoped_one(session,repo,t.journeys,action['journey_id'])
    choice=next((b for b in action['payload'].get('reply_buttons',[]) if b['id']==body.button_id),None)
    if not choice: raise ApplicationError(422,'BUTTON_INVALID','This choice was not part of the reviewed message.')
    submitted=await session.scalar(sa.select(t.action_receipts.c.id).join(t.dispatch_attempts,
        t.dispatch_attempts.c.id==t.action_receipts.c.attempt_id).where(repo.where(t.action_receipts),
            repo.where(t.dispatch_attempts),t.dispatch_attempts.c.action_id==action['id'],
            t.action_receipts.c.status=='submitted',t.action_receipts.c.source_mode=='simulated'))
    if not submitted: raise ApplicationError(422,'MESSAGE_NOT_SENT','A customer cannot reply to an unsent proposal.')
    conn=await connector(session,scope);ref='demo:'+str(body.event_key)
    address='demo:'+str(journey['customer_id'])
    await session.execute(insert(t.whatsapp_identities).values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
        connector_id=conn['id'],customer_id=journey['customer_id'],address=address,source_mode='simulated',
        verification_ref='synthetic-fixture').on_conflict_do_nothing(index_elements=[t.whatsapp_identities.c.merchant_id,
            t.whatsapp_identities.c.workspace_id,t.whatsapp_identities.c.connector_id,t.whatsapp_identities.c.address]))
    classification={'reorder':'purchase_interest','remind_later':'reminder_request','get_help':'support',
        'same_item':'purchase_interest','change_quantity':'needs_review','not_now':'not_now',
        'confirm_reminder':'reminder_request','change_reminder':'reminder_request'}[body.button_id]
    old=await session.scalar(sa.select(t.whatsapp_events.c.id).where(repo.where(t.whatsapp_events),
        t.whatsapp_events.c.connector_id==conn['id'],t.whatsapp_events.c.event_key==ref+':inbound'))
    params={'MessageSid':ref,'From':address,'Body':choice['title'],'ButtonPayload':str(action['id'])+':'+body.button_id}
    await accept_inbound(session,scope,conn,params,'simulated',classification)
    if not old:
        await execution.emit(session,scope,'whatsapp.choice',journey['customer_id'],{'message_ref':ref,
            'journey_id':str(journey['id']),'action_id':str(action['id']),'button_id':body.button_id,
            'button_title':choice['title'],'source_mode':'simulated'})
        current=await execution.scoped_one(session,repo,t.journeys,journey['id'])
        if body.button_id in ('reorder','remind_later') and current['state']=='reply_review':
            policy=await planning.latest(session,repo,t.policies)
            variant=await execution.scoped_one(session,repo,t.variants,journey['variant_id'])
            line=(await session.execute(sa.select(t.order_lines.c.quantity).join(t.commerce_orders,
                t.commerce_orders.c.id==t.order_lines.c.order_id).where(repo.where(t.order_lines),repo.where(t.commerce_orders),
                    t.commerce_orders.c.customer_id==journey['customer_id'],t.order_lines.c.variant_id==journey['variant_id'],
                    t.order_lines.c.delivery_at.is_not(None)).order_by(t.order_lines.c.delivery_at.desc()).limit(1))).first()
            quantity=line[0] if line and 1 <= line[0] <= 20 else 1
            step='confirm_item' if body.button_id=='reorder' else 'choose_reminder'
            now=datetime.now(timezone.utc)
            payload={**action['payload'],'kind':'choice_followup','interaction_step':step,'quantity':quantity,
                'text':followup_text(step,variant['title'],quantity),'reply_buttons':choices(step,quantity),
                'actor_id':str(current['owner_id']),'reply_ref':ref,'due_at':now.isoformat()}
            if policy: await execution.create_action(session,scope,current,policy,payload,now,action['expires_at'])
    from .merchant import thread
    return await thread(session,scope,journey['id'])

async def status_event(session,scope,conn,params,source_mode):
    repo=ScopedRepository(session,scope); await repo.workspace(lock=True)
    sid=params['MessageSid']; status=params['MessageStatus']; error=params.get('ErrorCode','')
    key=sid+':'+status+':'+error; hash_value=planning.digest(params)
    old=(await session.execute(sa.select(t.whatsapp_events).where(repo.where(t.whatsapp_events),t.whatsapp_events.c.connector_id==conn['id'],t.whatsapp_events.c.event_key==key))).mappings().first()
    if old:
        if old['payload_hash']!=hash_value: raise ApplicationError(409,'EVENT_CONFLICT','Status reference conflicts with earlier evidence.')
        return
    delivery=(await session.execute(sa.select(t.whatsapp_deliveries).where(repo.where(t.whatsapp_deliveries),t.whatsapp_deliveries.c.connector_id==conn['id'],t.whatsapp_deliveries.c.provider_ref==sid,t.whatsapp_deliveries.c.source_mode==source_mode).with_for_update())).mappings().first()
    state='quarantined' if not delivery else 'processed'
    ranks={'submitted':0,'queued':1,'sending':2,'sent':3,'delivered':4,'read':5}
    if delivery:
        previous=delivery['status']; failures={'failed','undelivered'}
        if (previous in failures and status not in failures) or (previous in ('delivered','read') and status in failures):
            state='requires_authoritative_refetch'
        elif previous not in failures and (status in failures or ranks.get(status,0)>=ranks.get(previous,0)):
            await session.execute(t.whatsapp_deliveries.update().where(repo.where(t.whatsapp_deliveries),t.whatsapp_deliveries.c.id==delivery['id']).values(status=status,error_code=error or None))
        if state=='requires_authoritative_refetch':
            attempt=(await session.execute(sa.select(t.dispatch_attempts).join(t.action_receipts,t.action_receipts.c.attempt_id==t.dispatch_attempts.c.id).where(repo.where(t.dispatch_attempts),t.action_receipts.c.id==delivery['receipt_id']))).mappings().first()
            if attempt:
                action=await execution.scoped_one(session,repo,t.proposed_actions,attempt['action_id'])
                journey=await execution.scoped_one(session,repo,t.journeys,action['journey_id'])
                await execution.hold_customer(session,scope,journey['customer_id'],'delivery_status_conflict',cancel=True)
    await session.execute(t.whatsapp_events.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,connector_id=conn['id'],event_key=key,payload_hash=hash_value,kind='status',message_ref=sid,
        classification=status,source_mode=source_mode,state=state))

async def demo_inbound(session,scope,body):
    repo=ScopedRepository(session,scope); workspace=await repo.workspace(lock=True)
    if workspace['environment']!='demo': raise ApplicationError(422,'SIMULATION_ONLY','Synthetic messages are allowed only in Demo.')
    conn=await connector(session,scope); journey=await execution.scoped_one(session,repo,t.journeys,body.journey_id)
    address='demo:'+str(journey['customer_id'])
    await session.execute(insert(t.whatsapp_identities).values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,connector_id=conn['id'],customer_id=journey['customer_id'],address=address,source_mode='simulated',verification_ref='synthetic-fixture').on_conflict_do_nothing(index_elements=[t.whatsapp_identities.c.merchant_id,t.whatsapp_identities.c.workspace_id,t.whatsapp_identities.c.connector_id,t.whatsapp_identities.c.address]))
    await accept_inbound(session,scope,conn,{'MessageSid':'demo:'+str(body.event_key),'From':address,'Body':body.text},'simulated')
    return await view(session,scope)

async def demo_status(session,scope,body):
    repo=ScopedRepository(session,scope)
    if (await repo.workspace())['environment']!='demo': raise ApplicationError(422,'SIMULATION_ONLY','Synthetic statuses are allowed only in Demo.')
    await materialize_demo(session,scope)
    conn=await connector(session,scope); receipt=await execution.scoped_one(session,repo,t.action_receipts,body.receipt_id)
    if receipt['source_mode']!='simulated' or receipt['status']!='submitted': raise ApplicationError(422,'RECEIPT_INVALID','A submitted Demo receipt is required.')
    await status_event(session,scope,conn,{'MessageSid':receipt['provider_ref'],'MessageStatus':body.status},'simulated')
    return await view(session,scope)

async def materialize_demo(session,scope):
    repo=ScopedRepository(session,scope)
    if (await repo.workspace())['environment']!='demo': return
    conn=await connector(session,scope)
    for receipt in await planning.rows(session,repo,t.action_receipts):
        if receipt['status']=='submitted' and receipt['source_mode']=='simulated' and receipt['provider_ref']:
            await session.execute(insert(t.whatsapp_deliveries).values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,connector_id=conn['id'],receipt_id=receipt['id'],provider_ref=receipt['provider_ref'],status='submitted',source_mode='simulated').on_conflict_do_nothing(index_elements=[t.whatsapp_deliveries.c.merchant_id,t.whatsapp_deliveries.c.workspace_id,t.whatsapp_deliveries.c.receipt_id]))

async def view(session,scope,transport=None):
    repo=ScopedRepository(session,scope);workspace=await repo.workspace();demo=workspace['environment']=='demo'
    journeys=await planning.rows(session,repo,t.journeys); customers={c['id']:c['display_alias'] for c in await planning.rows(session,repo,t.customers)}
    receipts={r['id']:r for r in await planning.rows(session,repo,t.action_receipts)}
    attempts={a['id']:a for a in await planning.rows(session,repo,t.dispatch_attempts)}
    actions={a['id']:a for a in await planning.rows(session,repo,t.proposed_actions)}
    messages=[]
    for delivery in await planning.rows(session,repo,t.whatsapp_deliveries):
        receipt=receipts.get(delivery['receipt_id'])
        attempt=attempts.get(receipt['attempt_id']) if receipt else None
        action=actions.get(attempt['action_id']) if attempt else None
        messages.append({**dict(delivery),'text':action['payload'].get('text') if action else None,'customer_alias':action['payload'].get('customer_alias') if action else None})
    return WhatsAppView(environment=workspace['environment'],notice='Demo messages and delivery receipts are synthetic. Replies stop competing outreach and enter human review.' if demo else 'Real transport is blocked. The correct join receipt was verified earlier; trial linkage/custom templates and public callback delivery remain unverified. No repeat join or customer outreach is required.',
        capabilities={'account_read_configured':bool(transport and transport.configured),'signed_ingress_configured':bool(RequestValidator and transport and transport.configured and transport.callback_base.startswith('https://')),'custom_outreach_verified':False,'real_send_enabled':False,'join_receipt_verified':True,'prior_inbound_error':'12300'},
        journeys=[{'id':j['id'],'customer_alias':customers.get(j['customer_id'],'Customer'),'state':j['state'],'owner_id':j['owner_id']} for j in journeys],
        messages=jsonable_encoder(messages),
        events=jsonable_encoder([dict(r) for r in await planning.rows(session,repo,t.whatsapp_events)]),
        identities=[{'customer_alias':customers.get(i['customer_id'],'Customer'),'source_mode':i['source_mode'],'verification_ref':i['verification_ref'],'address_hint':'Synthetic identity' if i['source_mode']=='simulated' else 'Verified address ending '+i['address'][-4:]} for i in await planning.rows(session,repo,t.whatsapp_identities)])

async def receive(request,session,workspace_id,connector_id,kind):
    transport=request.app.state.twilio
    if kind not in ('inbound','status'): raise ApplicationError(404,'NOT_FOUND','Callback not found.')
    if not transport.configured or not transport.callback_base.startswith('https://'): raise ApplicationError(503,'CALLBACK_UNCONFIGURED','Verified Twilio credentials, sender and public callback base are required.')
    if request.headers.get('content-type','').split(';')[0].strip()!='application/x-www-form-urlencoded': raise ApplicationError(415,'CONTENT_TYPE_INVALID','Twilio callbacks require form encoding.')
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>16384: raise ApplicationError(413,'EVENT_TOO_LARGE','Callback exceeds its size limit.')
    try: pairs=parse_qsl(raw.decode('utf-8'),keep_blank_values=True,strict_parsing=True)
    except (ValueError,UnicodeError): raise ApplicationError(422,'EVENT_INVALID','Malformed form callback.') from None
    if len(pairs)!=len({k for k,v in pairs}): raise ApplicationError(422,'EVENT_INVALID','Duplicate form fields are not accepted.')
    params=dict(pairs); url=transport.callback_base+request.url.path
    if request.url.query or not validate_signature(url,params,request.headers.get('x-twilio-signature',''),transport.token): raise ApplicationError(401,'SIGNATURE_INVALID','Twilio callback signature is invalid.')
    conn=(await session.execute(sa.select(t.connectors).where(t.connectors.c.id==connector_id,t.connectors.c.workspace_id==workspace_id,t.connectors.c.provider=='twilio',t.connectors.c.source_mode=='test',t.connectors.c.provider_account_id==transport.account))).mappings().first()
    if not conn or params.get('AccountSid')!=transport.account: raise ApplicationError(403,'ACCOUNT_MISMATCH','Callback does not match the bound Twilio account.')
    if not SID.fullmatch(params.get('MessageSid','')): raise ApplicationError(422,'MESSAGE_INVALID','MessageSid is required.')
    owner=(await session.execute(sa.select(t.memberships.c.user_id).where(t.memberships.c.merchant_id==conn['merchant_id'],t.memberships.c.role=='owner'))).scalar()
    if not owner: raise ApplicationError(503,'OWNER_UNAVAILABLE','A workspace owner is required for protected inbound review.')
    scope=Scope(conn['merchant_id'],workspace_id,owner,'owner')
    if kind=='inbound':
        if params.get('To')!=transport.sender or not ADDRESS.fullmatch(params.get('From','')) or len(params.get('Body',''))>2000: raise ApplicationError(422,'SENDER_INVALID','Inbound sender/recipient or body is invalid.')
        await accept_inbound(session,scope,conn,params,'test')
    else:
        if params.get('MessageStatus') not in STATUSES: raise ApplicationError(422,'STATUS_INVALID','Unsupported delivery status.')
        await status_event(session,scope,conn,params,'test')
    # New trial does not support direct TwiML. Acknowledge without an auto-reply.
    return Response('{}',media_type='application/json')

async def review_identity(session,scope,body,transport,correlation):
    repo=ScopedRepository(session,scope);workspace=await repo.workspace(lock=True)
    if workspace['environment']!='development' or scope.role!='owner':
        raise ApplicationError(403,'OWNER_REQUIRED','Only the Development workspace owner may review a test recipient identity.')
    await execution.scoped_one(session,repo,t.customers,body.customer_id)
    conn=await connector(session,scope)
    if conn['source_mode']!='test' or conn['provider_account_id'] not in (None,transport.account):
        raise ApplicationError(422,'ACCOUNT_UNBOUND','Twilio connector account must be verified before identity review.')
    proof=await transport.read_message(body.message_sid)
    if proof['direction']!='inbound' or proof['from']!=body.address or proof['to']!=transport.sender or proof['status']!='received':
        raise ApplicationError(422,'IDENTITY_UNVERIFIED','An exact account-bound inbound message from the reviewed recipient is required.')
    await session.execute(t.connectors.update().where(repo.where(t.connectors),t.connectors.c.id==conn['id']).values(provider_account_id=transport.account,state='partial',last_checked_at=datetime.now(timezone.utc),version=conn['version']+1))
    existing=(await session.execute(sa.select(t.whatsapp_identities).where(repo.where(t.whatsapp_identities),t.whatsapp_identities.c.connector_id==conn['id'],t.whatsapp_identities.c.address==body.address))).mappings().first()
    if existing and existing['customer_id']!=body.customer_id:
        raise ApplicationError(409,'IDENTITY_CONFLICT','This recipient is already mapped to a different customer.')
    await session.execute(insert(t.whatsapp_identities).values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,connector_id=conn['id'],customer_id=body.customer_id,address=body.address,source_mode='test',verification_ref=body.message_sid).on_conflict_do_nothing(index_elements=[t.whatsapp_identities.c.merchant_id,t.whatsapp_identities.c.workspace_id,t.whatsapp_identities.c.connector_id,t.whatsapp_identities.c.address]))
    await session.execute(t.audit_events.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,actor_id=scope.user_id,event_type='whatsapp.identity_reviewed',target_id=body.customer_id,correlation_id=correlation,details={'source_mode':'test','proof_ref':body.message_sid,'marketing_consent_created':False}))
    return await view(session,scope,transport)
