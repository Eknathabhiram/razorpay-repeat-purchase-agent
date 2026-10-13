"""Browser test orchestration. AI proposals never authorize external actions."""
import re
import uuid
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import sqlalchemy as sa
from fastapi.encoders import jsonable_encoder
from . import schema as t, planning, execution, whatsapp
from .repositories import ScopedRepository
from .errors import ApplicationError
from .intelligence_models import IntentProposal, IntentItem, IntelligenceView
from .execution_models import DemoEvent
from .together_provider import redact, PROMPT_VERSION, SCHEMA_VERSION

def baseline(text):
    found=[]
    patterns=[('opt_out',r'\b(stop|unsubscribe|optout)\b|opt out|do not contact'),('support',r'\b(refund|return|damaged|broken|complaint|support)\b'),('refusal',r'\b(no thanks|not interested|decline)\b'),('reminder',r'\b(later|remind|tomorrow|friday|week)\b'),('offer_enquiry',r'\b(coupon|discount|offer)\b'),('purchase_claim',r'\b(paid|purchased)\b'),('purchase_interest',r'\b(reorder|buy|yes|same product)\b')]
    for kind,pattern in patterns:
        match=re.search(pattern,text,re.I)
        if match:found.append(IntentItem(kind=kind,evidence=match.group()))
    if not found:found=[IntentItem(kind='clarification',evidence=text[:300])]
    number=re.search(r'\b([1-9]|1[0-9]|20)\b',text)
    quantity=int(number.group()) if number else next((n for n,w in ((1,'one'),(2,'two'),(3,'three')) if re.search(r'\b'+w+r'\b',text,re.I)),None)
    return IntentProposal(intents=found[:6],quantity=quantity,requested_product=None,date_text=None,confidence=1.0)

def render(proposal,facts):
    kinds={i.kind for i in proposal.intents}
    if 'opt_out' in kinds:return 'Your opt-out is recorded. Further replenishment outreach is stopped.'
    if 'support' in kinds:return 'A team member will review your product or support issue. Replenishment outreach is on hold.'
    if 'refusal' in kinds:return 'Your preference is recorded. Further replenishment outreach is stopped.'
    parts=[]
    if 'reminder' in kinds:parts.append('Please confirm an exact future reminder date and time in IST, and permission for a WhatsApp reminder. No reminder is scheduled yet.')
    if 'offer_enquiry' in kinds:parts.append('An offer needs current approved eligibility, costs and checkout review. No coupon or discount has been applied.')
    if 'purchase_claim' in kinds:parts.append('A payment statement does not confirm a purchase. Commerce and gateway evidence must match independently.')
    if 'purchase_interest' in kinds:
        if proposal.requested_product and proposal.requested_product.lower() not in ('same','same product',facts['title'].lower()):
            parts.append('This journey supports only the previously purchased product. Please confirm that same product.')
        else:
            price=facts.get('price_minor');currency=facts.get('currency')
            if price is not None and currency:
                parts.append(('Demo item price' if facts['source_mode']=='simulated' else 'Verified item price')+' '+currency+' '+format(price/100,'.2f')+'. Shipping, tax and final payable need checkout review.')
            parts.append('Confirm the same product, quantity'+(' '+str(proposal.quantity) if proposal.quantity else '')+' and separate WhatsApp handoff permission before preparing checkout. No link is sent.')
    if not parts or proposal.confidence<0.7:parts=['Please clarify your request. A team member is reviewing this conversation; outreach remains on hold.']
    return ' '.join(parts)

def preserve_explicit_intents(proposal,text):
    explicit=baseline(text)
    if any(i.kind in ('opt_out','support','refusal') for i in explicit.intents):return explicit
    claim_supported=bool(re.search(r'\b(paid|purchased|bought)\b|already ordered|payment (done|complete)',text,re.I))
    unique={i.kind:i for i in proposal.intents if i.kind!='purchase_claim' or claim_supported}
    for intent in explicit.intents:
        if intent.kind!='clarification':unique.setdefault(intent.kind,intent)
    return proposal.model_copy(update={'intents':list(unique.values())[:6]})

async def start(session,scope,body,provider):
    repo=ScopedRepository(session,scope);workspace=await repo.workspace(lock=True)
    if workspace['environment']!='demo':raise ApplicationError(422,'BROWSER_TEST_ONLY','Browser voice currently uses isolated Demo customer journeys.')
    journey=await execution.scoped_one(session,repo,t.journeys,body.journey_id)
    if journey['owner_id'] and journey['owner_id']!=scope.user_id:raise ApplicationError(403,'OWNER_REQUIRED','The current conversation owner must start this test.')
    if body.provider=='together' and (not body.confirmed_provider_processing or not provider.configured):raise ApplicationError(422,'PROVIDER_CONSENT_REQUIRED','Configure Together and explicitly consent to processing this test text/audio.')
    now=datetime.now(timezone.utc)
    sessions=await planning.rows(session,repo,t.voice_sessions)
    if any(s['state']=='active' and s['expires_at']>now and s['journey_id']==journey['id'] for s in sessions):raise ApplicationError(409,'SESSION_ACTIVE','Stop the existing browser session before starting another.')
    await whatsapp.protect(session,scope,journey['customer_id'],'needs_review','browser-session', 'simulated')
    row=(await session.execute(t.voice_sessions.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,journey_id=journey['id'],actor_id=scope.user_id,provider=body.provider,
        consent={'browser_test':True,'provider_processing':body.confirmed_provider_processing,'source_mode':'simulated','telephone':False},state='active',version=1,last_sequence=0,expires_at=now+timedelta(minutes=15)).returning(t.voice_sessions))).mappings().one()
    return jsonable_encoder(dict(row))

async def get_session(session,scope,session_id,active=True):
    repo=ScopedRepository(session,scope);row=await execution.scoped_one(session,repo,t.voice_sessions,session_id,True)
    if row['actor_id']!=scope.user_id:raise ApplicationError(403,'SESSION_OWNER_REQUIRED','Only this browser session owner may operate it.')
    if active and (row['state']!='active' or row['expires_at']<=datetime.now(timezone.utc)):raise ApplicationError(409,'SESSION_STOPPED','Browser session stopped or expired.')
    return row

async def facts_for(session,scope,voice):
    repo=ScopedRepository(session,scope);journey=await execution.scoped_one(session,repo,t.journeys,voice['journey_id'])
    variant=await execution.scoped_one(session,repo,t.variants,journey['variant_id'])
    return {'journey_id':str(journey['id']),'variant_id':str(variant['id']),'plan_revision_id':str(journey['plan_revision_id']),'title':variant['title'],'price_minor':variant['price_minor'],'currency':variant['currency'],'stock':variant['stock'],'source_mode':variant['provenance'].get('source_mode','unverified'),'captured_at':datetime.now(timezone.utc).isoformat()}

async def claim(session,scope,session_id,sequence,kind,value):
    repo=ScopedRepository(session,scope);await repo.workspace(lock=True);voice=await get_session(session,scope,session_id)
    hash_value=planning.digest({'kind':kind,'value':value})
    existing=(await session.execute(sa.select(t.intelligence_turns).where(repo.where(t.intelligence_turns),t.intelligence_turns.c.session_id==session_id,t.intelligence_turns.c.sequence==sequence))).mappings().first()
    if existing:
        if existing['input_hash']!=hash_value:raise ApplicationError(409,'TURN_CONFLICT','Turn sequence was reused with different input.')
        return voice,existing,False
    if sequence!=voice['last_sequence']+1:raise ApplicationError(409,'TURN_SEQUENCE','Submit the next consecutive turn; refresh uncertain outcomes.')
    if any(x['state']=='processing' or x['state']=='awaiting_transcript_confirmation' for x in await planning.rows(session,repo,t.intelligence_turns) if x['session_id']==session_id):raise ApplicationError(409,'TURN_PENDING','Resolve the pending turn first.')
    facts=await facts_for(session,scope,voice)
    row=(await session.execute(t.intelligence_turns.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,session_id=session_id,sequence=sequence,input_hash=hash_value,input_kind=kind,
        transcript=value if kind=='text' else None,state='processing',facts=facts,receipt={}).returning(t.intelligence_turns))).mappings().one()
    await session.execute(t.voice_sessions.update().where(repo.where(t.voice_sessions),t.voice_sessions.c.id==session_id).values(last_sequence=sequence,version=voice['version']+1))
    if kind=='text':await protect_text(session,scope,voice,value,str(row['id']))
    return voice,row,True

async def protect_text(session,scope,voice,text,ref):
    repo=ScopedRepository(session,scope);journey=await execution.scoped_one(session,repo,t.journeys,voice['journey_id'])
    kinds={i.kind for i in baseline(text).intents}
    classification=next((c for i,c in [('opt_out','opt_out'),('support','support'),('refusal','refusal')] if i in kinds),'needs_review')
    await whatsapp.protect(session,scope,journey['customer_id'],classification,'voice:'+ref,'simulated')

async def interpret(db,scope,voice,turn,provider):
    text=turn['transcript'];proposal=baseline(text);error=None
    receipt={'provider':'deterministic','prompt_version':PROMPT_VERSION,'schema_version':SCHEMA_VERSION,'latency_ms':0,'cost_usd':0,'usage':[]}
    protective=any(i.kind in ('opt_out','support','refusal') for i in proposal.intents)
    if voice['provider']=='together' and not protective:
        try:
            async with db.unit_of_work() as session:
                repo=ScopedRepository(session,scope)
                history=sorted(await planning.rows(session,repo,t.intelligence_turns),key=lambda x:x['sequence'])
                context=[redact(x['transcript'][:1000]) for x in history if x['session_id']==voice['id'] and x['id']!=turn['id'] and x['transcript']][-4:]
            proposal,receipt=await provider.interpret(text,{'previous_turns':context,'same_product':turn['facts']['title'],'timezone':'Asia/Kolkata'})
            raw_kinds=[i.kind for i in proposal.intents]
            proposal=preserve_explicit_intents(proposal,text)
            receipt['model_intents']=raw_kinds
            receipt['validated_intents']=[i.kind for i in proposal.intents]
        except ApplicationError as exc:
            error=exc.code;receipt={'provider':'together','model':provider.model,'prompt_version':PROMPT_VERSION,'schema_version':SCHEMA_VERSION,'cost_usd':None,'status':'failed'}
    async with db.unit_of_work() as session:
        repo=ScopedRepository(session,scope);await repo.workspace(lock=True)
        current=await get_session(session,scope,voice['id'],False)
        row=await execution.scoped_one(session,repo,t.intelligence_turns,turn['id'],True)
        if row['state']!='processing':return
        stopped=current['state']!='active' or current['expires_at']<=datetime.now(timezone.utc)
        fresh=await facts_for(session,scope,current)
        journey=await execution.scoped_one(session,repo,t.journeys,current['journey_id'])
        if not stopped:
            protective_kind=next((c for i,c in [('opt_out','opt_out'),('support','support'),('refusal','refusal')] if any(p.kind==i for p in proposal.intents)),None)
            if protective_kind and not protective:await whatsapp.protect(session,scope,journey['customer_id'],protective_kind,'voice:'+str(row['id']),'simulated')
        reply=render(proposal,fresh) if not error else 'Interpretation is unavailable. A team member must review your request; outreach remains on hold.'
        if journey['state'] in ('opted_out','support','refused'):
            reply={'opted_out':'Your opt-out is recorded. Further replenishment outreach is stopped.','support':'Your support issue is under review. Replenishment outreach is on hold.','refused':'Your preference is recorded. Further replenishment outreach is stopped.'}[journey['state']]
        await session.execute(t.intelligence_turns.update().where(repo.where(t.intelligence_turns),t.intelligence_turns.c.id==row['id']).values(state='cancelled' if stopped else 'needs_review' if error else 'completed',proposal=proposal.model_dump(),reply=None if stopped else reply,facts=fresh,receipt=receipt,error_code=error))

async def text_turn(db,scope,session_id,body,provider):
    async with db.unit_of_work() as session:voice,turn,new=await claim(session,scope,session_id,body.sequence,'text',body.text.strip())
    if new:await interpret(db,scope,voice,turn,provider)
    async with db.unit_of_work() as session:return await view(session,scope,provider)

async def audio_turn(db,scope,session_id,sequence,audio,mime,provider):
    import hashlib
    async with db.unit_of_work() as session:
        voice=await get_session(session,scope,session_id)
        if voice['provider']!='together' or not voice['consent']['provider_processing']:raise ApplicationError(422,'AUDIO_BLOCKED','Together processing consent is required for audio.')
        voice,turn,new=await claim(session,scope,session_id,sequence,'audio',hashlib.sha256(audio).hexdigest())
    if new:
        error=None;text=None
        try:text=await provider.transcribe(audio,mime)
        except ApplicationError as exc:error=exc.code
        async with db.unit_of_work() as session:
            repo=ScopedRepository(session,scope);await repo.workspace(lock=True);current=await get_session(session,scope,session_id,False)
            stopped=current['state']!='active' or current['expires_at']<=datetime.now(timezone.utc)
            if text and not stopped:await protect_text(session,scope,voice,text,str(turn['id']))
            await session.execute(t.intelligence_turns.update().where(repo.where(t.intelligence_turns),t.intelligence_turns.c.id==turn['id']).values(state='cancelled' if stopped else 'needs_review' if error else 'awaiting_transcript_confirmation',transcript=text,error_code=error,receipt={'provider':'together','model':provider.stt_model,'raw_audio_retained':False}))
    async with db.unit_of_work() as session:return await view(session,scope,provider)

async def confirm_transcript(db,scope,turn_id,body,provider):
    async with db.unit_of_work() as session:
        repo=ScopedRepository(session,scope);await repo.workspace(lock=True);turn=await execution.scoped_one(session,repo,t.intelligence_turns,turn_id,True)
        voice=await get_session(session,scope,turn['session_id'])
        if turn['state']!='awaiting_transcript_confirmation':raise ApplicationError(409,'TRANSCRIPT_STALE','Only an unconfirmed transcript can be confirmed.')
        await protect_text(session,scope,voice,body.text,str(turn['id']))
        await session.execute(t.intelligence_turns.update().where(repo.where(t.intelligence_turns),t.intelligence_turns.c.id==turn_id).values(state='processing',transcript=body.text))
        turn={**turn,'transcript':body.text,'state':'processing'}
    await interpret(db,scope,voice,turn,provider)
    async with db.unit_of_work() as session:return await view(session,scope,provider)

async def stop(session,scope,session_id,body):
    repo=ScopedRepository(session,scope);await repo.workspace(lock=True);voice=await get_session(session,scope,session_id,False)
    if voice['version']!=body.expected_version:raise ApplicationError(409,'SESSION_VERSION','Refresh the current browser session.')
    await session.execute(t.voice_sessions.update().where(repo.where(t.voice_sessions),t.voice_sessions.c.id==session_id).values(state='stopped',version=voice['version']+1))
    await session.execute(t.intelligence_turns.update().where(repo.where(t.intelligence_turns),t.intelligence_turns.c.session_id==session_id,t.intelligence_turns.c.state.in_(('processing','awaiting_transcript_confirmation'))).values(state='cancelled'))
    return await view(session,scope)

async def reminder(session,scope,turn_id,body):
    repo=ScopedRepository(session,scope);await repo.workspace(lock=True);turn=await execution.scoped_one(session,repo,t.intelligence_turns,turn_id,True);voice=await get_session(session,scope,turn['session_id'])
    if turn['state']!='completed' or voice['last_sequence']!=turn['sequence'] or turn['confirmed_action'] or not any(i['kind']=='reminder' for i in turn['proposal']['intents']):raise ApplicationError(409,'TURN_STALE','Review the current reminder request before confirming.')
    journey=await execution.scoped_one(session,repo,t.journeys,voice['journey_id'])
    if journey['state'] in ('opted_out','support','refused','purchased','purchase_under_review','unknown_outcome'):raise ApplicationError(422,'CUSTOMER_HELD','Customer protection blocks this reminder.')
    await execution.event(session,scope,DemoEvent(event_key=turn['id'],journey_id=journey['id'],kind='reminder',due_at=body.due_at),uuid.uuid4())
    from .outcomes import learn_reminder
    await learn_reminder(session,scope,turn,voice,body.due_at)
    await session.execute(t.intelligence_turns.update().where(repo.where(t.intelligence_turns),t.intelligence_turns.c.id==turn_id).values(confirmed_action='reminder_confirmed'))
    return await view(session,scope)

async def view(session,scope,provider=None):
    repo=ScopedRepository(session,scope);workspace=await repo.workspace();customers={c['id']:c['display_alias'] for c in await planning.rows(session,repo,t.customers)}
    observed=await planning.rows(session,repo,t.intelligence_turns)
    verified=bool(provider and any(x['state']=='completed' and x['receipt'].get('provider')=='together' and x['receipt'].get('account_ref')==provider.account_ref for x in observed))
    return IntelligenceView(environment=workspace['environment'],provider={'name':'Together AI','configured':bool(provider and provider.configured),'chat_model':provider.model if provider else 'Qwen/Qwen3.5-9B','stt_model':provider.stt_model if provider else 'nvidia/parakeet-tdt-0.6b-v3','tts_model':provider.tts_model if provider else 'hexgrad/Kokoro-82M','account_verified':verified},
        notice='Consented operator conversation test with synthetic customer journeys. Together processes text/audio only with explicit session consent. Responses are previews; no telephone call or WhatsApp send occurs.',
        journeys=[{'id':j['id'],'customer_alias':customers.get(j['customer_id'],'Customer'),'state':j['state']} for j in await planning.rows(session,repo,t.journeys)],
        sessions=jsonable_encoder([dict(s) for s in sorted(await planning.rows(session,repo,t.voice_sessions),key=lambda s:s['created_at'],reverse=True) if s['actor_id']==scope.user_id]),
        turns=jsonable_encoder([dict(x) for x in sorted(await planning.rows(session,repo,t.intelligence_turns),key=lambda x:(x['created_at'],x['sequence'])) if x['session_id'] in {s['id'] for s in await planning.rows(session,repo,t.voice_sessions) if s['actor_id']==scope.user_id}]))

async def checkout_request(session,scope,turn_id,body):
    from .commerce_models import CartRequest
    repo=ScopedRepository(session,scope);await repo.workspace(lock=True)
    turn=await execution.scoped_one(session,repo,t.intelligence_turns,turn_id,True);voice=await get_session(session,scope,turn['session_id'])
    if turn['state']!='completed' or turn['confirmed_action'] or voice['last_sequence']!=turn['sequence'] or not any(i['kind']=='purchase_interest' for i in turn['proposal']['intents']):
        raise ApplicationError(409,'TURN_STALE','Confirm the latest interpreted same-product request before checkout.')
    proposal=turn['proposal'];facts=await facts_for(session,scope,voice)
    if proposal.get('requested_product') and proposal['requested_product'].lower() not in ('same','same product',facts['title'].lower()):
        raise ApplicationError(422,'SAME_PRODUCT_REQUIRED','This request does not identify the previously purchased product.')
    if proposal.get('quantity') is not None and proposal['quantity']!=body.quantity:
        raise ApplicationError(409,'QUANTITY_CHANGED','Confirm a new customer turn if the requested quantity changed.')
    return turn,CartRequest(journey_id=voice['journey_id'],quantity=body.quantity,confirmed_same_product=True,confirmed_whatsapp_handoff=True,offer_ref=None,quote_digest=body.quote_digest)
