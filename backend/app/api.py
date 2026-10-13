import asyncio
import secrets
import uuid
from datetime import datetime, timedelta, timezone, date
from typing import Annotated
import sqlalchemy as sa
from fastapi import APIRouter, Depends, Request, Response, Header, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from . import schema as t
from .errors import ApplicationError
from .repositories import ScopedRepository, resolve_scope
from .security import authenticate, check_password, charge_login_attempt, digest, dummy_digest, verify_csrf, session_csrf
from .services import rename_workspace, record_shopify_check
from .settings import REVISION
from .ui_models import Envelope, Me, Connector, UIReadModel, DemoCommand
from .ui_services import read_ui, demo_command
from .store_view import StoreView, project_snapshot
from .planning_models import PlanningView, PlanningCommand, PolicyChange, DraftChange
from . import planning
from .execution_models import ExecutionCommand, ExecutionView, DemoEvent, Tick
from . import execution, worker
from .commerce_models import CartRequest, CommerceCommand, CommerceView, OfferPolicy, DemoPurchase
from . import commerce, commerce_callbacks
from . import whatsapp
from .whatsapp_models import DemoInbound, DemoStatus, WhatsAppView, IdentityReview
from . import intelligence
from .intelligence_models import StartSession, TextTurn, ConfirmTranscript, SessionCommand, ReminderConfirmation, VoiceCheckout, IntelligenceView
from . import outcomes
from .outcomes_models import AccountingReview, SuggestionDecision, OutcomeView
from . import merchant
from . import test_conversations
from .merchant_models import AudienceSelection, DemoChoice

router = APIRouter(prefix="/api/v1")


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Input):
    login: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("login")
    @classmethod
    def normalise(cls, value):
        value = value.strip().lower()
        if not value:
            raise ValueError("Login cannot be blank")
        return value


class Rename(Input):
    name: str = Field(min_length=1, max_length=120)
    expected_version: int = Field(ge=1)

    @field_validator("name")
    @classmethod
    def trim(cls, value):
        if not value.strip() or any(ord(c) < 32 for c in value):
            raise ValueError("Use a nonempty name without control characters")
        return value.strip()


class Check(Input):
    expected_version: int = Field(ge=1)


def envelope(request, data):
    return {"data": data, "meta": {"correlation_id": str(request.state.correlation_id),
                                 "generated_at": datetime.now(timezone.utc).isoformat()}}


async def transaction(request: Request):
    async with request.app.state.db.unit_of_work() as session:
        yield session


Session = Annotated[object, Depends(transaction, scope="function")]


async def actor_for(request, session, mutation=False):
    actor = await authenticate(session, request.cookies.get(request.app.state.settings.cookie_name))
    if mutation:
        verify_csrf(actor, request.headers.get("x-csrf-token"))
    return actor


@router.get("/health/live")
async def live():
    return {"service": "repeat-purchase-foundation", "alive": True}


@router.get("/health/ready")
async def ready(request: Request):
    async with request.app.state.db.unit_of_work() as session:
        revision = await session.scalar(sa.text("SELECT version_num FROM alembic_version"))
        if revision != REVISION:
            raise ApplicationError(503, "SCHEMA_NOT_READY", "Run the application migration before starting.")
    return {"ready": True, "schema_revision": REVISION}


@router.post("/auth/login")
async def login(body: Login, request: Request, response: Response, session: Session):
    settings = request.app.state.settings
    if request.headers.get("origin") not in settings.origins:
        raise ApplicationError(403, "ORIGIN_REQUIRED", "Sign in from the local application review page.")
    ip = request.client.host if request.client else "unknown"
    await charge_login_attempt(request.app.state.db, body.login, ip)
    user = (await session.execute(sa.select(t.users).where(
        t.users.c.login_identifier == body.login, t.users.c.disabled_at.is_(None)))).mappings().first()
    valid = await asyncio.to_thread(check_password, user["password_digest"] if user else dummy_digest,
                                   body.password)
    if not user or not valid:
        raise ApplicationError(401, "INVALID_LOGIN", "Login or password is incorrect.")
    token = secrets.token_urlsafe(32)
    csrf = session_csrf(token)
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.session_hours)
    await session.execute(t.sessions.insert().values(
        user_id=user["id"], token_hash=digest(token), csrf_hash=digest(csrf), expires_at=expires))
    response.set_cookie(settings.cookie_name, token, httponly=True, secure=settings.cookie_secure,
                        samesite="lax", max_age=settings.session_hours * 3600, path="/")
    return envelope(request, {"login": user["login_identifier"], "csrf_token": csrf,
                              "expires_at": expires})


@router.post("/auth/logout")
async def logout(request: Request, response: Response, session: Session):
    actor = await actor_for(request, session, mutation=True)
    await session.execute(t.sessions.update().where(t.sessions.c.id == actor["session_id"])
                          .values(revoked_at=datetime.now(timezone.utc)))
    response.delete_cookie(request.app.state.settings.cookie_name, path="/",
                           httponly=True, secure=request.app.state.settings.cookie_secure, samesite="lax")
    return envelope(request, {"signed_out": True})


@router.get("/me", response_model=Envelope[Me])
async def me(request: Request, session: Session):
    actor = await actor_for(request, session)
    rows = (await session.execute(sa.select(t.workspaces.c.id, t.workspaces.c.name,
        t.workspaces.c.environment, t.workspaces.c.version, t.memberships.c.role
    ).select_from(t.workspaces.join(t.memberships,
        t.memberships.c.merchant_id == t.workspaces.c.merchant_id)
    ).where(t.memberships.c.user_id == actor["user_id"]).order_by(t.workspaces.c.environment))).mappings().all()
    return envelope(request, {"login": actor["login_identifier"], "workspaces": [dict(r) for r in rows]})


@router.get("/workspaces/{workspace_id}")
async def workspace(workspace_id: uuid.UUID, request: Request, session: Session):
    actor = await actor_for(request, session)
    scope = await resolve_scope(session, actor["user_id"], workspace_id)
    row = await ScopedRepository(session, scope).workspace()
    return envelope(request, {k: row[k] for k in ("id", "name", "environment", "version")})


@router.put("/workspaces/{workspace_id}")
async def rename(workspace_id: uuid.UUID, body: Rename, request: Request, session: Session,
                 idempotency_key: Annotated[uuid.UUID, Header()]):
    actor = await actor_for(request, session, mutation=True)
    scope = await resolve_scope(session, actor["user_id"], workspace_id, mutate=True)
    result = await rename_workspace(session, scope, body.name, body.expected_version,
                                    idempotency_key, request.state.correlation_id)
    return envelope(request, result)


@router.get("/workspaces/{workspace_id}/connectors", response_model=Envelope[list[Connector]])
async def connectors(workspace_id: uuid.UUID, request: Request, session: Session):
    actor = await actor_for(request, session)
    scope = await resolve_scope(session, actor["user_id"], workspace_id)
    return envelope(request, await ScopedRepository(session, scope).connector_list())


@router.post("/workspaces/{workspace_id}/connectors/{connector_id}/check")
async def check(workspace_id: uuid.UUID, connector_id: uuid.UUID, body: Check,
                request: Request, session: Session):
    actor = await actor_for(request, session, mutation=True)
    scope = await resolve_scope(session, actor["user_id"], workspace_id, mutate=True)
    repo = ScopedRepository(session, scope)
    connector = await repo.connector(connector_id)
    if connector["version"] != body.expected_version:
        raise ApplicationError(409, "VERSION_CONFLICT", "Connection changed. Refresh before checking.")
    if connector["provider"] != "shopify" or connector["source_mode"] != "test":
        raise ApplicationError(422, "CAPABILITY_UNVERIFIED", "Only the existing Shopify development read adapter is implemented.")
    snapshot = await request.app.state.shopify.snapshot()
    return envelope(request, await record_shopify_check(session, scope, connector_id,
                                                      snapshot, request.state.correlation_id))


@router.get("/workspaces/{workspace_id}/audit")
async def audit(workspace_id: uuid.UUID, request: Request, session: Session):
    actor = await actor_for(request, session)
    scope = await resolve_scope(session, actor["user_id"], workspace_id)
    repo = ScopedRepository(session, scope)
    rows = (await session.execute(sa.select(t.audit_events.c.id, t.audit_events.c.event_type,
        t.audit_events.c.target_id, t.audit_events.c.details, t.audit_events.c.created_at
    ).where(repo.where(t.audit_events)).order_by(t.audit_events.c.created_at.desc()).limit(50))).mappings().all()
    return envelope(request, [dict(row) for row in rows])


@router.post("/auth/session")
async def restore_session(request: Request, session: Session):
    if request.headers.get("origin") not in request.app.state.settings.origins:
        raise ApplicationError(403, "ORIGIN_REQUIRED", "Use the application origin.")
    actor = await actor_for(request, session)
    csrf = session_csrf(request.cookies[request.app.state.settings.cookie_name])
    await session.execute(t.sessions.update().where(t.sessions.c.id == actor["session_id"])
                          .values(csrf_hash=digest(csrf)))
    return envelope(request, {"csrf_token": csrf})


@router.get("/workspaces/{workspace_id}/ui-state", response_model=Envelope[UIReadModel])
async def ui_state(workspace_id: uuid.UUID, request: Request, session: Session):
    actor = await actor_for(request, session)
    scope = await resolve_scope(session, actor["user_id"], workspace_id)
    return envelope(request, await read_ui(session, scope))


@router.post("/workspaces/{workspace_id}/demo-commands", response_model=Envelope[UIReadModel])
async def ui_command(workspace_id: uuid.UUID, body: DemoCommand, request: Request, session: Session,
                     idempotency_key: Annotated[uuid.UUID, Header()]):
    actor = await actor_for(request, session, mutation=True)
    scope = await resolve_scope(session, actor["user_id"], workspace_id, mutate=True)
    return envelope(request, await demo_command(session, scope, body, idempotency_key,
                                               request.state.correlation_id))


@router.get("/workspaces/{workspace_id}/connectors/{connector_id}/store", response_model=Envelope[StoreView])
async def store_view(workspace_id: uuid.UUID, connector_id: uuid.UUID, request: Request, session: Session):
    actor = await actor_for(request, session)
    scope = await resolve_scope(session, actor["user_id"], workspace_id)
    connector = await ScopedRepository(session, scope).connector(connector_id)
    if (connector["provider"] != "shopify" or connector["source_mode"] != "test" or
        connector["provider_account_id"] != request.app.state.shopify.shop):
        raise ApplicationError(422, "CAPABILITY_UNVERIFIED", "No verified development-store adapter is bound here.")
    return envelope(request, project_snapshot(await request.app.state.shopify.snapshot()))


@router.get("/workspaces/{workspace_id}/planning", response_model=Envelope[PlanningView])
async def planning_view(workspace_id: uuid.UUID, request: Request, session: Session):
    actor = await actor_for(request, session)
    scope = await resolve_scope(session, actor["user_id"], workspace_id)
    return envelope(request, await planning.view(session, scope))


@router.post("/workspaces/{workspace_id}/planning/facts", response_model=Envelope[PlanningView])
async def planning_facts(workspace_id: uuid.UUID, body: PlanningCommand, request: Request, session: Session,
                         idempotency_key: Annotated[uuid.UUID, Header()]):
    actor = await actor_for(request, session, mutation=True)
    scope = await resolve_scope(session, actor["user_id"], workspace_id, mutate=True)
    return envelope(request, await planning.command(session, scope, "facts", body, idempotency_key,
        request.state.correlation_id, request.app.state.shopify))


@router.post("/workspaces/{workspace_id}/planning/policy-preview")
async def policy_preview(workspace_id: uuid.UUID, body: PolicyChange, request: Request, session: Session):
    actor = await actor_for(request, session, mutation=True)
    scope = await resolve_scope(session, actor["user_id"], workspace_id, mutate=True)
    current = await planning.view(session, scope)
    before = current.policy["config_json"] if current.policy else {}
    after = body.config.model_dump(mode="json")
    items = await planning.compute(session, scope, config=body.config)
    return envelope(request, {"diff": {key:{"before":before.get(key),"after":value} for key,value in after.items() if before.get(key)!=value},
        "eligible_count":sum(item["eligible"] for item in items), "excluded_count":sum(not item["eligible"] for item in items),
        "draft_requires_review": bool(current.draft), "expected_revision":current.policy["revision"] if current.policy else 0})


@router.post("/workspaces/{workspace_id}/planning/policies", response_model=Envelope[PlanningView])
async def planning_policy(workspace_id: uuid.UUID, body: PolicyChange, request: Request, session: Session,
                          idempotency_key: Annotated[uuid.UUID, Header()]):
    actor = await actor_for(request, session, mutation=True)
    scope = await resolve_scope(session, actor["user_id"], workspace_id, mutate=True)
    return envelope(request, await planning.command(session, scope, "policy", body, idempotency_key, request.state.correlation_id))


@router.post("/workspaces/{workspace_id}/planning/drafts", response_model=Envelope[PlanningView])
async def planning_draft(workspace_id: uuid.UUID, body: DraftChange, request: Request, session: Session,
                         idempotency_key: Annotated[uuid.UUID, Header()]):
    actor = await actor_for(request, session, mutation=True)
    scope = await resolve_scope(session, actor["user_id"], workspace_id, mutate=True)
    return envelope(request, await planning.command(session, scope, "draft", body, idempotency_key, request.state.correlation_id))


@router.get("/workspaces/{workspace_id}/execution", response_model=Envelope[ExecutionView])
async def execution_view(workspace_id: uuid.UUID, request: Request, session: Session):
    actor = await actor_for(request, session)
    scope = await resolve_scope(session, actor["user_id"], workspace_id)
    return envelope(request, await execution.view(session, scope))


@router.post("/workspaces/{workspace_id}/execution/commands", response_model=Envelope[ExecutionView])
async def execution_command(workspace_id: uuid.UUID, body: ExecutionCommand, request: Request, session: Session,
                            idempotency_key: Annotated[uuid.UUID, Header()]):
    actor = await actor_for(request, session, mutation=True)
    scope = await resolve_scope(session, actor["user_id"], workspace_id, mutate=True)
    return envelope(request, await execution.command(session, scope, body, idempotency_key, request.state.correlation_id))


@router.post("/workspaces/{workspace_id}/execution/demo-events", response_model=Envelope[ExecutionView])
async def execution_event(workspace_id: uuid.UUID, body: DemoEvent, request: Request, session: Session):
    actor = await actor_for(request, session, mutation=True)
    scope = await resolve_scope(session, actor["user_id"], workspace_id, mutate=True)
    return envelope(request, await execution.event(session, scope, body, request.state.correlation_id))


@router.post("/workspaces/{workspace_id}/execution/run-due", response_model=Envelope[ExecutionView])
async def execution_tick(workspace_id: uuid.UUID, body: Tick, request: Request):
    # Auth transaction commits before the worker opens independent short transactions.
    async with request.app.state.db.unit_of_work() as session:
        actor = await actor_for(request, session, mutation=True)
        scope = await resolve_scope(session, actor["user_id"], workspace_id, mutate=True)
    await worker.run_once(request.app.state.db, scope, body.outcome, body.limit)
    async with request.app.state.db.unit_of_work() as session:
        return envelope(request, await execution.view(session, scope))


@router.get("/workspaces/{workspace_id}/commerce", response_model=Envelope[CommerceView])
async def commerce_view(workspace_id: uuid.UUID, request: Request, session: Session):
    actor=await actor_for(request,session);scope=await resolve_scope(session,actor["user_id"],workspace_id)
    return envelope(request,await commerce.view(session,scope))


@router.post("/workspaces/{workspace_id}/commerce/quote")
async def commerce_quote(workspace_id: uuid.UUID, body: CartRequest, request: Request, session: Session):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor["user_id"],workspace_id,mutate=True)
    return envelope(request,await commerce.quote(session,scope,body))


@router.post("/workspaces/{workspace_id}/commerce/commands", response_model=Envelope[CommerceView])
async def commerce_command(workspace_id: uuid.UUID, body: CommerceCommand, request: Request, session: Session,
                           idempotency_key: Annotated[uuid.UUID, Header()]):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor["user_id"],workspace_id,mutate=True)
    return envelope(request,await commerce.command(session,scope,body,idempotency_key,request.state.correlation_id,request.app.state.razorpay,request.app.state.shopify))


@router.post("/workspaces/{workspace_id}/commerce/offer-policy", response_model=Envelope[CommerceView])
async def commerce_offer_policy(workspace_id: uuid.UUID, body: OfferPolicy, request: Request, session: Session):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor["user_id"],workspace_id,mutate=True)
    return envelope(request,await commerce.configure_offer(session,scope,body,request.state.correlation_id))


@router.post("/workspaces/{workspace_id}/commerce/demo-evidence", response_model=Envelope[CommerceView])
async def commerce_demo_evidence(workspace_id: uuid.UUID, body: DemoPurchase, request: Request, session: Session):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor["user_id"],workspace_id,mutate=True)
    return envelope(request,await commerce.demo_purchase(session,scope,body,request.state.correlation_id))


@router.post("/providers/{provider}/{workspace_id}/{connector_id}/events")
async def commerce_callback(provider: str, workspace_id: uuid.UUID, connector_id: uuid.UUID, request: Request, session: Session):
    if provider not in ("shopify","razorpay"):raise ApplicationError(404,"NOT_FOUND","Provider callback not found.")
    return await commerce_callbacks.receive(request,session,provider,workspace_id,connector_id)

@router.get("/workspaces/{workspace_id}/whatsapp", response_model=Envelope[WhatsAppView])
async def whatsapp_view(workspace_id: uuid.UUID, request: Request, session: Session):
    actor=await actor_for(request,session);scope=await resolve_scope(session,actor["user_id"],workspace_id)
    return envelope(request,await whatsapp.view(session,scope,request.app.state.twilio))

@router.post("/workspaces/{workspace_id}/whatsapp/demo-inbound", response_model=Envelope[WhatsAppView])
async def whatsapp_demo_inbound(workspace_id: uuid.UUID, body: DemoInbound, request: Request, session: Session):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor["user_id"],workspace_id,mutate=True)
    return envelope(request,await whatsapp.demo_inbound(session,scope,body))

@router.post("/workspaces/{workspace_id}/whatsapp/demo-status", response_model=Envelope[WhatsAppView])
async def whatsapp_demo_status(workspace_id: uuid.UUID, body: DemoStatus, request: Request, session: Session):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor["user_id"],workspace_id,mutate=True)
    return envelope(request,await whatsapp.demo_status(session,scope,body))

@router.post("/providers/twilio/{workspace_id}/{connector_id}/{kind}")
async def whatsapp_callback(workspace_id: uuid.UUID, connector_id: uuid.UUID, kind: str, request: Request, session: Session):
    return await whatsapp.receive(request,session,workspace_id,connector_id,kind)

@router.post("/workspaces/{workspace_id}/whatsapp/identity-review", response_model=Envelope[WhatsAppView])
async def whatsapp_identity_review(workspace_id: uuid.UUID, body: IdentityReview, request: Request, session: Session):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor["user_id"],workspace_id,mutate=True)
    return envelope(request,await whatsapp.review_identity(session,scope,body,request.app.state.twilio,request.state.correlation_id))

@router.get("/workspaces/{workspace_id}/intelligence", response_model=Envelope[IntelligenceView])
async def intelligence_view(workspace_id: uuid.UUID, request: Request, session: Session):
    actor=await actor_for(request,session);scope=await resolve_scope(session,actor["user_id"],workspace_id)
    return envelope(request,await intelligence.view(session,scope,request.app.state.together))

@router.post("/workspaces/{workspace_id}/voice-sessions")
async def start_voice_session(workspace_id: uuid.UUID, body: StartSession, request: Request, session: Session):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor["user_id"],workspace_id,mutate=True)
    return envelope(request,await intelligence.start(session,scope,body,request.app.state.together))

async def voice_actor(request,workspace_id):
    async with request.app.state.db.unit_of_work() as session:
        actor=await actor_for(request,session,mutation=True)
        return await resolve_scope(session,actor["user_id"],workspace_id,mutate=True)

@router.post("/workspaces/{workspace_id}/voice-sessions/{session_id}/turns", response_model=Envelope[IntelligenceView])
async def voice_text_turn(workspace_id: uuid.UUID, session_id: uuid.UUID, body: TextTurn, request: Request):
    scope=await voice_actor(request,workspace_id)
    return envelope(request,await intelligence.text_turn(request.app.state.db,scope,session_id,body,request.app.state.together))

@router.post("/workspaces/{workspace_id}/voice-sessions/{session_id}/audio", response_model=Envelope[IntelligenceView])
async def voice_audio_turn(workspace_id: uuid.UUID, session_id: uuid.UUID, sequence: int, request: Request):
    scope=await voice_actor(request,workspace_id)
    if not 1<=sequence<=20:raise ApplicationError(422,"TURN_SEQUENCE","Invalid audio turn sequence.")
    mime=request.headers.get("content-type","").split(";")[0]
    if mime not in ("audio/webm","audio/wav"):raise ApplicationError(415,"AUDIO_FORMAT","Use WebM or WAV audio.")
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>8_000_000:raise ApplicationError(413,"AUDIO_TOO_LARGE","Limit browser audio to a short turn.")
    if len(raw)<100:raise ApplicationError(422,"AUDIO_EMPTY","Record a clear message or use typed text.")
    return envelope(request,await intelligence.audio_turn(request.app.state.db,scope,session_id,sequence,bytes(raw),mime,request.app.state.together))

@router.post("/workspaces/{workspace_id}/intelligence/turns/{turn_id}/confirm", response_model=Envelope[IntelligenceView])
async def confirm_voice_transcript(workspace_id: uuid.UUID, turn_id: uuid.UUID, body: ConfirmTranscript, request: Request):
    scope=await voice_actor(request,workspace_id)
    return envelope(request,await intelligence.confirm_transcript(request.app.state.db,scope,turn_id,body,request.app.state.together))

@router.post("/workspaces/{workspace_id}/voice-sessions/{session_id}/stop", response_model=Envelope[IntelligenceView])
async def stop_voice_session(workspace_id: uuid.UUID, session_id: uuid.UUID, body: SessionCommand, request: Request, session: Session):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor["user_id"],workspace_id,mutate=True)
    return envelope(request,await intelligence.stop(session,scope,session_id,body))

@router.post("/workspaces/{workspace_id}/intelligence/turns/{turn_id}/reminder", response_model=Envelope[IntelligenceView])
async def confirm_voice_reminder(workspace_id: uuid.UUID, turn_id: uuid.UUID, body: ReminderConfirmation, request: Request, session: Session):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor["user_id"],workspace_id,mutate=True)
    return envelope(request,await intelligence.reminder(session,scope,turn_id,body))

@router.post("/workspaces/{workspace_id}/intelligence/turns/{turn_id}/speech")
async def voice_reply_speech(workspace_id: uuid.UUID, turn_id: uuid.UUID, request: Request):
    from fastapi.responses import Response
    scope=await voice_actor(request,workspace_id)
    async with request.app.state.db.unit_of_work() as session:
        repo=ScopedRepository(session,scope);turn=await execution.scoped_one(session,repo,t.intelligence_turns,turn_id)
        voice=await intelligence.get_session(session,scope,turn["session_id"])
        if voice["provider"]!="together" or not voice["consent"]["provider_processing"] or turn["state"] not in ("completed","needs_review") or not turn["reply"]:
            raise ApplicationError(422,"SPEECH_BLOCKED","A reviewed server reply and provider consent are required.")
        reply=turn["reply"]
    audio=await request.app.state.together.speech(reply)
    async with request.app.state.db.unit_of_work() as session:await intelligence.get_session(session,scope,voice["id"])
    return Response(audio,media_type="audio/mpeg")

@router.post("/workspaces/{workspace_id}/intelligence/turns/{turn_id}/checkout-quote")
async def voice_checkout_quote(workspace_id: uuid.UUID, turn_id: uuid.UUID, body: VoiceCheckout, request: Request, session: Session):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor["user_id"],workspace_id,mutate=True)
    turn,cart=await intelligence.checkout_request(session,scope,turn_id,body)
    return envelope(request,await commerce.quote(session,scope,cart))

@router.post("/workspaces/{workspace_id}/intelligence/turns/{turn_id}/checkout", response_model=Envelope[IntelligenceView])
async def voice_checkout_prepare(workspace_id: uuid.UUID, turn_id: uuid.UUID, body: VoiceCheckout, request: Request, session: Session, idempotency_key: Annotated[uuid.UUID,Header()]):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor["user_id"],workspace_id,mutate=True)
    turn,cart=await intelligence.checkout_request(session,scope,turn_id,body)
    await commerce.command(session,scope,CommerceCommand(action="prepare",cart=cart),idempotency_key,request.state.correlation_id,request.app.state.razorpay,request.app.state.shopify)
    await session.execute(t.intelligence_turns.update().where(ScopedRepository(session,scope).where(t.intelligence_turns),t.intelligence_turns.c.id==turn_id).values(confirmed_action="checkout_prepared"))
    return envelope(request,await intelligence.view(session,scope,request.app.state.together))

@router.get("/workspaces/{workspace_id}/outcomes", response_model=Envelope[OutcomeView])
async def outcomes_view(workspace_id: uuid.UUID, request: Request, session: Session):
    actor=await actor_for(request,session);scope=await resolve_scope(session,actor["user_id"],workspace_id)
    return envelope(request,await outcomes.view(session,scope))

@router.post("/workspaces/{workspace_id}/outcomes/accounting", response_model=Envelope[OutcomeView])
async def outcomes_accounting(workspace_id: uuid.UUID, body: AccountingReview, request: Request, session: Session):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor["user_id"],workspace_id,mutate=True)
    return envelope(request,await outcomes.accounting(session,scope,body,request.state.correlation_id))

@router.post("/workspaces/{workspace_id}/outcomes/suggestions", response_model=Envelope[OutcomeView])
async def outcomes_suggestions(workspace_id: uuid.UUID, request: Request, session: Session):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor["user_id"],workspace_id,mutate=True)
    return envelope(request,await outcomes.suggest(session,scope,request.state.correlation_id))

@router.post("/workspaces/{workspace_id}/outcomes/suggestions/{suggestion_id}/decision", response_model=Envelope[OutcomeView])
async def outcomes_suggestion_decision(workspace_id: uuid.UUID, suggestion_id: uuid.UUID, body: SuggestionDecision, request: Request, session: Session):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor["user_id"],workspace_id,mutate=True)
    return envelope(request,await outcomes.decide(session,scope,suggestion_id,body,request.state.correlation_id))

@router.get('/workspaces/{workspace_id}/test-conversations/catalogue')
async def test_catalogue(workspace_id: uuid.UUID, request: Request, session: Session):
    actor=await actor_for(request,session);scope=await resolve_scope(session,actor['user_id'],workspace_id)
    return envelope(request,await test_conversations.catalogue(session,scope,request.app.state.shopify,request.app.state.twilio,request.app.state.together))

@router.post('/workspaces/{workspace_id}/test-conversations')
async def start_test(workspace_id: uuid.UUID,body: test_conversations.StartTest,request: Request,session: Session,idempotency_key: Annotated[uuid.UUID,Header()]):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor['user_id'],workspace_id,mutate=True)
    return envelope(request,await test_conversations.start(session,scope,body,idempotency_key,request.state.correlation_id,request.app.state.shopify,request.app.state.twilio,request.app.state.together))

@router.get('/workspaces/{workspace_id}/test-conversations/{conversation_id}')
async def test_thread(workspace_id: uuid.UUID,conversation_id: uuid.UUID,request: Request,session: Session):
    actor=await actor_for(request,session);scope=await resolve_scope(session,actor['user_id'],workspace_id)
    return envelope(request,await test_conversations.view(session,scope,conversation_id))

@router.post('/workspaces/{workspace_id}/test-conversations/{conversation_id}/reply')
async def test_reply(workspace_id: uuid.UUID,conversation_id: uuid.UUID,body: test_conversations.TestReply,request: Request,session: Session,idempotency_key: Annotated[uuid.UUID,Header()]):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor['user_id'],workspace_id,mutate=True)
    return envelope(request,await test_conversations.reply(session,scope,conversation_id,body,idempotency_key,request.state.correlation_id,request.app.state.shopify,request.app.state.twilio,request.app.state.together))

@router.get('/workspaces/{workspace_id}/merchant/overview')
async def merchant_overview(workspace_id: uuid.UUID, request: Request, session: 'Session'):
    actor=await actor_for(request,session);scope=await resolve_scope(session,actor['user_id'],workspace_id)
    return envelope(request,await merchant.summary(session,scope))

@router.get('/workspaces/{workspace_id}/merchant/planning')
async def merchant_planning(workspace_id: uuid.UUID, request: Request, session: 'Session'):
    actor=await actor_for(request,session);scope=await resolve_scope(session,actor['user_id'],workspace_id)
    return envelope(request,await merchant.planning_summary(session,scope))

@router.get('/workspaces/{workspace_id}/merchant/filters')
async def merchant_filters(workspace_id: uuid.UUID,request: Request,session: 'Session'):
    actor=await actor_for(request,session);scope=await resolve_scope(session,actor['user_id'],workspace_id)
    return envelope(request,await merchant.filters(session,scope))

@router.get('/workspaces/{workspace_id}/merchant/readiness')
async def merchant_readiness(workspace_id: uuid.UUID,request: Request,session: 'Session'):
    from . import readiness
    actor=await actor_for(request,session);scope=await resolve_scope(session,actor['user_id'],workspace_id)
    return envelope(request,await readiness.view(session,scope,request.app.state.shopify,request.app.state.razorpay,request.app.state.twilio,request.app.state.together))

@router.get('/workspaces/{workspace_id}/merchant/launch')
async def merchant_launch(workspace_id: uuid.UUID,request: Request,session: 'Session',page: int=Query(1,ge=1),page_size: int=Query(25,ge=1,le=100)):
    actor=await actor_for(request,session);scope=await resolve_scope(session,actor['user_id'],workspace_id)
    return envelope(request,await merchant.launch(session,scope,page,page_size))

@router.post('/workspaces/{workspace_id}/merchant/commands')
async def merchant_commands(workspace_id: uuid.UUID,body: ExecutionCommand,request: Request,session: 'Session',idempotency_key: Annotated[uuid.UUID,Header()]):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor['user_id'],workspace_id,mutate=True)
    return envelope(request,await execution.command(session,scope,body,idempotency_key,request.state.correlation_id,compact=True))

@router.get('/workspaces/{workspace_id}/merchant/opportunities')
async def merchant_opportunities(workspace_id: uuid.UUID, request: Request, session: 'Session',
    page: int=Query(1,ge=1,le=100000),page_size: int=Query(25,ge=1,le=100),
    search: str=Query('',max_length=120),eligibility: str=Query('all',pattern='^(all|eligible|excluded)$'),
    city: str=Query('',max_length=120),date_from: date|None=None,date_to: date|None=None):
    actor=await actor_for(request,session);scope=await resolve_scope(session,actor['user_id'],workspace_id)
    if date_from and date_to and date_from>date_to:raise ApplicationError(422,'DATE_RANGE_INVALID','End date must follow start date.')
    return envelope(request,await merchant.opportunity_page(session,scope,page,page_size,search,eligibility,city,date_from,date_to))

@router.get('/workspaces/{workspace_id}/merchant/journeys')
async def merchant_journeys(workspace_id: uuid.UUID, request: Request, session: 'Session',
    page: int=Query(1,ge=1,le=100000),page_size: int=Query(25,ge=1,le=100),search: str=Query('',max_length=120),
    state: str=Query('all',pattern='^(all|review|held|scheduled|contacted|reply_review|support|opted_out|refused|purchased|unknown_outcome|purchase_under_review)$'),inbox: bool=False,
    city: str=Query('',max_length=120),date_from: date|None=None,date_to: date|None=None):
    actor=await actor_for(request,session);scope=await resolve_scope(session,actor['user_id'],workspace_id)
    if date_from and date_to and date_from>date_to:raise ApplicationError(422,'DATE_RANGE_INVALID','End date must follow start date.')
    return envelope(request,await merchant.journey_page(session,scope,page,page_size,search,state,inbox,city,date_from,date_to))

@router.get('/workspaces/{workspace_id}/merchant/threads/{journey_id}')
async def merchant_thread(workspace_id: uuid.UUID, journey_id: uuid.UUID, request: Request, session: 'Session'):
    actor=await actor_for(request,session);scope=await resolve_scope(session,actor['user_id'],workspace_id)
    return envelope(request,await merchant.thread(session,scope,journey_id))

@router.post('/workspaces/{workspace_id}/merchant/audience')
async def merchant_audience(workspace_id: uuid.UUID, body: AudienceSelection, request: Request, session: 'Session',
    idempotency_key: Annotated[uuid.UUID,Header()]):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor['user_id'],workspace_id,mutate=True)
    await ScopedRepository(session,scope).workspace(lock=True)
    repo,policy,point,draft,stale,items=await merchant.planning_context(session,scope)
    if not policy or policy['id']!=body.policy_id or not point or point['facts_version']!=body.facts_version:
        raise ApplicationError(409,'FACTS_CHANGED','The audience facts or policy changed. Refresh and review again.')
    if len(set(body.selected))!=len(body.selected) or len(set(body.excluded))!=len(body.excluded):
        raise ApplicationError(422,'AUDIENCE_DUPLICATE','Select or exclude each opportunity only once.')
    if body.mode=='eligible': selected=set((await session.execute(merchant.opportunity_filters(sa.select(items.c.id).where(items.c.eligible),items,body.filters.search,body.filters.city,body.filters.date_from,body.filters.date_to))).scalars())
    elif body.mode=='saved':
        if not draft or stale: raise ApplicationError(409,'DRAFT_STALE','Review a fresh selection before saving.')
        selected=set((await session.execute(sa.select(t.plan_members.c.opportunity_id).where(repo.where(t.plan_members),
            t.plan_members.c.plan_revision_id==draft['id'],t.plan_members.c.selected))).scalars())
    else: selected=set()
    selected=(selected|set(body.selected))-set(body.excluded)
    if len(selected)>20000: raise ApplicationError(422,'AUDIENCE_TOO_LARGE','Review this audience in plans of at most 20,000 opportunities.')
    await planning.command(session,scope,'draft',DraftChange(expected_revision=body.expected_revision,selected=list(selected),audience_filters=body.filters if body.mode=='eligible' else None),
        idempotency_key,request.state.correlation_id)
    return envelope(request,await merchant.planning_summary(session,scope))

@router.post('/workspaces/{workspace_id}/merchant/whatsapp/demo-choice')
async def merchant_demo_choice(workspace_id: uuid.UUID, body: DemoChoice, request: Request, session: 'Session'):
    actor=await actor_for(request,session,mutation=True);scope=await resolve_scope(session,actor['user_id'],workspace_id,mutate=True)
    return envelope(request,await whatsapp.demo_choice(session,scope,body))
