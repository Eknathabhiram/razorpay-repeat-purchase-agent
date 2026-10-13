"""Exact approvals and supervision. Stage 04 permits Demo side effects only."""
import uuid
from datetime import datetime, timedelta, timezone
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from fastapi.encoders import jsonable_encoder
from . import schema as t, planning
from .errors import ApplicationError
from .repositories import ScopedRepository
from .execution_models import ExecutionView
from .interaction_content import choices

OPEN = ("awaiting_review", "ready", "held")


async def scoped_one(session, repo, table, identifier, lock=False):
    query = sa.select(table).where(repo.where(table), table.c.id == identifier)
    if lock: query = query.with_for_update()
    row = (await session.execute(query)).mappings().first()
    if not row: raise ApplicationError(404,"NOT_FOUND","Record not found in this workspace.")
    return row


async def agent(session, scope, create=False):
    repo = ScopedRepository(session,scope)
    if create:
        await session.execute(insert(t.agents).values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
            version=0,paused=False,dispatch_epoch=0).on_conflict_do_nothing(index_elements=[t.agents.c.merchant_id,t.agents.c.workspace_id]))
    return (await session.execute(sa.select(t.agents).where(repo.where(t.agents)))).mappings().first()


async def emit(session,scope,event_type,subject,details):
    await session.execute(t.event_outbox.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
        event_type=event_type,subject_id=subject,details=details))


async def approval(session,scope,kind,identifier,digest,decision):
    await session.execute(t.approvals.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
        resource_type=kind,resource_id=identifier,digest=digest,decision=decision,actor_id=scope.user_id))


async def existing_approval(session,repo,kind,identifier):
    return (await session.execute(sa.select(t.approvals).where(repo.where(t.approvals),t.approvals.c.resource_type==kind,
        t.approvals.c.resource_id==identifier))).mappings().first()


async def manifest(session,scope):
    current=await planning.view(session,scope)
    if not current.draft: return None
    draft=current.draft
    selected={str(m["opportunity_id"]) for m in draft["members"] if m["selected"]}
    items=[item for item in current.opportunities if str(item["id"]) in selected]
    messages=[]
    for item in sorted(items,key=lambda i:str(i["customer_id"])):
        info=item["evidence_json"]
        due=item["window_start"] if item["basis"]=="customer_confirmed_date" else draft["created_at"]
        text=("As requested, here's your reminder about "+info["variant_title"]+". Would you like to reorder the same product?" if item["basis"]=="customer_confirmed_date" else
              "Would you like to reorder your "+info["variant_title"]+"? You can tell us if you need more time. Reply STOP to opt out.")
        payload={"customer_id":str(item["customer_id"]),"variant_id":str(item["variant_id"]),"provider_variant_id":info["provider_variant_id"],
            "customer_alias":info["customer_alias"],"variant_title":info["variant_title"],"kind":"reminder" if item["basis"]=="customer_confirmed_date" else "reorder_check",
            "channel":"whatsapp","text":text,"cost_minor":25,"currency":"INR","source_mode":"simulated","due_at":due,
            "plan_revision_id":str(draft["id"]),"policy_id":str(current.policy["id"]) if current.policy else None,"facts_version":current.facts_version}
        payload['reply_buttons'] = choices(payload['kind'])
        if item["basis"]=="customer_confirmed_date":
            payload["confirmed_event_key"]=str(uuid.uuid5(uuid.NAMESPACE_URL,str(draft["id"])+str(item["customer_id"])))
            payload["timezone"]="Asia/Kolkata"
        messages.append({"payload":payload,"digest":planning.digest(payload)})
    combined=planning.digest({"draft_digest":draft["digest"],"messages":messages})
    return {"id":str(draft["id"]),"revision":draft["revision"],"digest":combined,"stale":draft["stale"] or len(items)!=len(selected),
            "selected_count":len(selected),"mode":current.policy["config_json"]["mode"] if current.policy else "review",
            "messages":messages,"expires_at":draft["expires_at"]}


async def create_action(session,scope,journey,policy,payload,due,expires,auto=False):
    identifier=uuid.uuid4();hash_value=planning.digest(payload)
    await session.execute(t.proposed_actions.insert().values(id=identifier,merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
        journey_id=journey["id"],policy_id=policy["id"],payload=payload,digest=hash_value,state="ready" if auto else "awaiting_review",due_at=due,expires_at=expires))
    await session.execute(t.jobs.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,action_id=identifier,
        due_at=due,state="ready" if auto else "waiting_review",attempts=0))
    if auto: await approval(session,scope,"action",identifier,hash_value,"approve")
    await emit(session,scope,"action.proposed",identifier,{"source_mode":"simulated","approval_required":not auto})
    return identifier


async def hold_customer(session,scope,customer_id,reason,cancel=False):
    repo=ScopedRepository(session,scope)
    journeys=sa.select(t.journeys.c.id).where(repo.where(t.journeys),t.journeys.c.customer_id==customer_id)
    identifiers=list((await session.execute(sa.select(t.proposed_actions.c.id).where(repo.where(t.proposed_actions),
        t.proposed_actions.c.journey_id.in_(journeys),t.proposed_actions.c.state.in_(OPEN)))).scalars())
    if identifiers:
        await session.execute(t.proposed_actions.update().where(repo.where(t.proposed_actions),t.proposed_actions.c.id.in_(identifiers)).values(state='cancelled' if cancel else 'held'))
        await session.execute(t.jobs.update().where(repo.where(t.jobs),t.jobs.c.action_id.in_(identifiers)).values(state='cancelled' if cancel else 'held',blocked_reason=reason,lease_token=None,lease_until=None))


async def approve_plan(session,scope,body,current_agent):
    repo=ScopedRepository(session,scope)
    review=await manifest(session,scope)
    if not review or str(body.subject_id)!=review["id"] or review["stale"] or body.digest!=review["digest"]:
        raise ApplicationError(409,"APPROVAL_STALE","Review the exact current draft and message content before approval.")
    if await existing_approval(session,repo,"plan",body.subject_id):
        raise ApplicationError(409,"ALREADY_DECIDED","This draft already has an immutable decision. Create a new revision to change it.")
    if body.action=="reject_plan":
        await approval(session,scope,"plan",body.subject_id,body.digest,"reject");return
    if current_agent["paused"]: raise ApplicationError(422,"AGENT_PAUSED","Resume before approving a new audience.")
    fresh=await planning.compute(session,scope)
    eligible={(i["customer_id"],i["variant_id"]) for i in fresh if i["eligible"]}
    if any((m["payload"]["customer_id"],m["payload"]["variant_id"]) not in eligible for m in review["messages"]):
        raise ApplicationError(409,"FACTS_CHANGED","Eligibility changed. Refresh and review a new draft.")
    draft=await scoped_one(session,repo,t.plan_revisions,body.subject_id)
    policy=await scoped_one(session,repo,t.policies,draft["policy_id"])
    await approval(session,scope,"plan",body.subject_id,body.digest,"approve")
    prior_journeys=await planning.rows(session,repo,t.journeys)
    prior_owners={j['customer_id']:j['owner_id'] for j in prior_journeys if j['owner_id']}
    prior_actions=sa.select(t.proposed_actions.c.id).where(repo.where(t.proposed_actions),t.proposed_actions.c.state.in_(OPEN))
    await session.execute(t.jobs.update().where(repo.where(t.jobs),t.jobs.c.action_id.in_(prior_actions)).values(state='cancelled',blocked_reason='plan_superseded',lease_token=None,lease_until=None))
    await session.execute(t.proposed_actions.update().where(repo.where(t.proposed_actions),t.proposed_actions.c.state.in_(OPEN)).values(state='cancelled'))
    await session.execute(t.reminders.update().where(repo.where(t.reminders),t.reminders.c.state=="scheduled").values(state="cancelled"))
    await session.execute(insert(t.budget_buckets).values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
        policy_id=policy["id"],cap_minor=policy["config_json"]["budget_minor"],reserved_minor=0,spent_minor=0).on_conflict_do_nothing(
            index_elements=[t.budget_buckets.c.merchant_id,t.budget_buckets.c.workspace_id,t.budget_buckets.c.policy_id]))
    for message in review["messages"]:
        payload=message["payload"]
        customer_id,variant_id=uuid.UUID(payload["customer_id"]),uuid.UUID(payload["variant_id"])
        await session.execute(t.cohort_assignments.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
            plan_revision_id=draft["id"],customer_id=customer_id,variant_id=variant_id))
        identifier=uuid.uuid4()
        await session.execute(t.journeys.insert().values(id=identifier,merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
            plan_revision_id=draft["id"],customer_id=customer_id,variant_id=variant_id,state="scheduled",
            owner_id=prior_owners.get(customer_id)))
        await session.execute(insert(t.contact_guards).values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,customer_id=customer_id).on_conflict_do_nothing(
            index_elements=[t.contact_guards.c.merchant_id,t.contact_guards.c.workspace_id,t.contact_guards.c.customer_id]))
        due=planning.date(payload["due_at"])
        if payload["kind"]=="reminder":
            await session.execute(t.reminders.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
                journey_id=identifier,event_key=uuid.UUID(payload["confirmed_event_key"]),due_at=due,timezone="Asia/Kolkata",channel="whatsapp",state="scheduled"))
        await create_action(session,scope,{"id":identifier},policy,payload,due,draft["expires_at"],auto=policy["config_json"]["mode"]=="bounded")
    await emit(session,scope,"plan.approved",draft["id"],{"selected_count":review["selected_count"]})


async def command(session,scope,body,key,correlation,compact=False):
    repo=ScopedRepository(session,scope)
    workspace=await repo.workspace(lock=True)
    if workspace["environment"]!="demo": raise ApplicationError(422,"SIMULATION_ONLY","Execution remains blocked outside Demo.")
    current=await agent(session,scope,True)
    operation="merchant.command" if compact else "execution.command";hash_value=planning.digest(body)
    await session.execute(insert(t.idempotency).values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,actor_id=scope.user_id,
        operation=operation,key=key,request_hash=hash_value,expires_at=datetime.now(timezone.utc)+timedelta(days=7)).on_conflict_do_nothing(
            index_elements=[t.idempotency.c.merchant_id,t.idempotency.c.workspace_id,t.idempotency.c.actor_id,t.idempotency.c.operation,t.idempotency.c.key]))
    record=(await session.execute(sa.select(t.idempotency).where(repo.where(t.idempotency),t.idempotency.c.actor_id==scope.user_id,
        t.idempotency.c.operation==operation,t.idempotency.c.key==key).with_for_update())).mappings().one()
    if record["request_hash"]!=hash_value: raise ApplicationError(409,"IDEMPOTENCY_CONFLICT","Request key was used for different execution content.")
    if record["result_json"] is not None: return record["result_json"]
    if current["version"]!=body.expected_version: raise ApplicationError(409,"VERSION_CONFLICT","Execution changed. Refresh and review current state.")
    action=body.action
    if action in ("approve_plan","reject_plan"):
        await approve_plan(session,scope,body,current)
    elif action in ("approve_action","reject_action"):
        proposed=await scoped_one(session,repo,t.proposed_actions,body.subject_id)
        if proposed["digest"]!=body.digest or proposed["state"]!="awaiting_review" or proposed["expires_at"]<=datetime.now(timezone.utc):
            raise ApplicationError(409,"APPROVAL_STALE","The exact current action must be reviewed before approval.")
        if action=="approve_action":
            from .worker import validate
            reason=await validate(session,scope,proposed,datetime.now(timezone.utc),check_contact_hours=False,require_action_approval=False)
            if reason: raise ApplicationError(422,"ACTION_BLOCKED",reason.replace("_"," "))
        await approval(session,scope,"action",proposed["id"],body.digest,"approve" if action=="approve_action" else "reject")
        await session.execute(t.proposed_actions.update().where(repo.where(t.proposed_actions),t.proposed_actions.c.id==proposed["id"]).values(state="ready" if action=="approve_action" else "rejected"))
        await session.execute(t.jobs.update().where(repo.where(t.jobs),t.jobs.c.action_id==proposed["id"]).values(state="ready" if action=="approve_action" else "cancelled",blocked_reason=None))
    elif action in ("pause","resume"):
        if action=="resume":
            planning_view=await planning.view(session,scope)
            if planning_view.draft and planning_view.draft["stale"]:
                raise ApplicationError(422,"PLAN_STALE","Review a current draft before resuming.")
            await session.execute(t.jobs.update().where(repo.where(t.jobs),t.jobs.c.state=="held",t.jobs.c.blocked_reason=="agent_paused").values(state="ready",blocked_reason=None))
            await session.execute(t.proposed_actions.update().where(repo.where(t.proposed_actions),t.proposed_actions.c.id.in_(
                sa.select(t.jobs.c.action_id).where(repo.where(t.jobs),t.jobs.c.state=="ready")),t.proposed_actions.c.state=="held").values(state="ready"))
        await session.execute(t.agents.update().where(repo.where(t.agents)).values(paused=action=="pause"))
    elif action in ("takeover","handback","propose_reply"):
        journey=await scoped_one(session,repo,t.journeys,body.subject_id)
        if action=="takeover":
            await session.execute(t.journeys.update().where(repo.where(t.journeys),t.journeys.c.customer_id==journey["customer_id"]).values(owner_id=scope.user_id))
            await hold_customer(session,scope,journey["customer_id"],"human_takeover")
        elif action=="handback":
            if journey["owner_id"]!=scope.user_id: raise ApplicationError(403,"OWNER_REQUIRED","Only the current conversation owner can hand back.")
            inflight=await session.scalar(sa.select(t.contact_guards.c.inflight_action_id).where(repo.where(t.contact_guards),t.contact_guards.c.customer_id==journey["customer_id"]))
            if inflight: raise ApplicationError(422,"HANDOFF_BLOCKED","Resolve the in-flight or unknown outcome before handing back.")
            if current["paused"] or journey["state"] in ("opted_out","support","purchased","unknown_outcome","purchase_under_review","refused","reply_review"): raise ApplicationError(422,"HANDOFF_BLOCKED","Resolve the current hold before handing back.")
            await session.execute(t.journeys.update().where(repo.where(t.journeys),t.journeys.c.customer_id==journey["customer_id"]).values(owner_id=None))
            # Restore only actions that were already approved; review-required proposals remain in review.
            actions=await planning.rows(session,repo,t.proposed_actions)
            for proposed in actions:
                if proposed["journey_id"]==journey["id"] and proposed["state"]=="held":
                    approved=await existing_approval(session,repo,"action",proposed["id"])
                    state="ready" if approved and approved["decision"]=="approve" else "awaiting_review"
                    await session.execute(t.proposed_actions.update().where(repo.where(t.proposed_actions),t.proposed_actions.c.id==proposed["id"]).values(state=state))
                    await session.execute(t.jobs.update().where(repo.where(t.jobs),t.jobs.c.action_id==proposed["id"],t.jobs.c.blocked_reason=="human_takeover").values(state="ready" if state=="ready" else "waiting_review",blocked_reason=None))
        else:
            if journey["owner_id"]!=scope.user_id: raise ApplicationError(403,"OWNER_REQUIRED","Take over before preparing a human reply.")
            draft=await scoped_one(session,repo,t.plan_revisions,journey["plan_revision_id"])
            policy=await scoped_one(session,repo,t.policies,draft["policy_id"])
            customer=await scoped_one(session,repo,t.customers,journey["customer_id"])
            variant=await scoped_one(session,repo,t.variants,journey["variant_id"])
            payload={"customer_id":str(customer["id"]),"variant_id":str(variant["id"]),"customer_alias":customer["display_alias"],"variant_title":variant["title"],
                "provider_variant_id":variant["provider_variant_id"],"kind":"human_acknowledgement","channel":"whatsapp","text":"Thanks for your reply. A team member is reviewing your request.",
                "actor_id":str(scope.user_id),"cost_minor":25,"currency":"INR","source_mode":"simulated","plan_revision_id":str(draft["id"]),"policy_id":str(policy["id"])}
            await create_action(session,scope,journey,policy,payload,datetime.now(timezone.utc),draft["expires_at"])
    elif action in ("assign_support","resolve_support"):
        case=await scoped_one(session,repo,t.support_cases,body.subject_id)
        if action=="resolve_support":
            if case["owner_id"]!=scope.user_id: raise ApplicationError(403,"OWNER_REQUIRED","Assign the case before resolving it.")
            journey=await scoped_one(session,repo,t.journeys,case["journey_id"])
            now=datetime.now(timezone.utc)
            await session.execute(t.customer_evidence.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
                customer_id=journey["customer_id"],kind="support",value={"open":False},effective_at=now,
                provenance={"source_mode":"simulated","classification":"source_verified","source_ref":str(case["id"]),"retrieved_at":now.isoformat()}))
            await session.execute(t.journeys.update().where(repo.where(t.journeys),t.journeys.c.customer_id==journey["customer_id"],t.journeys.c.state=="support").values(state="needs_plan_review"))
        await session.execute(t.support_cases.update().where(repo.where(t.support_cases),t.support_cases.c.id==case["id"]).values(owner_id=scope.user_id,state="resolved" if action=="resolve_support" else "assigned"))
    await session.execute(t.agents.update().where(repo.where(t.agents)).values(version=current["version"]+1,dispatch_epoch=current["dispatch_epoch"]+1))
    await session.execute(t.audit_events.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,actor_id=scope.user_id,
        event_type="execution."+action,target_id=body.subject_id or scope.workspace_id,correlation_id=correlation,details={"source_mode":"simulated"}))
    if compact:
        current=await agent(session,scope)
        result={'version':current['version'],'paused':current['paused']}
    else:result=jsonable_encoder(await view(session,scope))
    await session.execute(t.idempotency.update().where(t.idempotency.c.id==record["id"]).values(result_json=result))
    return result


async def event(session,scope,body,correlation):
    repo=ScopedRepository(session,scope)
    workspace=await repo.workspace(lock=True)
    if workspace["environment"]!="demo": raise ApplicationError(422,"SIMULATION_ONLY","Synthetic events are allowed only in Demo.")
    journey=await scoped_one(session,repo,t.journeys,body.journey_id)
    existing=(await session.execute(sa.select(t.event_inbox).where(repo.where(t.event_inbox),t.event_inbox.c.event_key==body.event_key))).mappings().first()
    hash_value=planning.digest(body)
    if existing:
        if existing["payload_hash"]!=hash_value: raise ApplicationError(409,"EVENT_CONFLICT","Event key was used for different content.")
        return await view(session,scope)
    if body.kind=="reminder" and (body.due_at<=datetime.now(timezone.utc) or body.due_at>datetime.now(timezone.utc)+timedelta(days=365)):
        raise ApplicationError(422,"DATE_INVALID","Confirm a future absolute reminder date within one year.")
    await session.execute(t.event_inbox.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
        event_key=body.event_key,payload_hash=hash_value,kind=body.kind,journey_id=journey["id"]))
    await hold_customer(session,scope,journey["customer_id"],body.kind,cancel=True)
    customer_journeys=[j["id"] for j in await planning.rows(session,repo,t.journeys) if j["customer_id"]==journey["customer_id"]]
    await session.execute(t.reminders.update().where(repo.where(t.reminders),t.reminders.c.journey_id.in_(customer_journeys),t.reminders.c.state=="scheduled").values(state="cancelled"))
    now=datetime.now(timezone.utc)
    evidence={"source_mode":"simulated","classification":"customer_stated","source_ref":str(body.event_key),"retrieved_at":now.isoformat()}
    state={"opt_out":"opted_out","support":"support","reminder":"reminder_scheduled","outside_purchase":"purchased"}[body.kind]
    await session.execute(t.journeys.update().where(repo.where(t.journeys),t.journeys.c.customer_id==journey["customer_id"]).values(state=state))
    if body.kind in ("opt_out","support"):
        kind,value=("suppression",{"active":True}) if body.kind=="opt_out" else ("support",{"open":True})
        await session.execute(t.customer_evidence.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
            customer_id=journey["customer_id"],kind=kind,value=value,effective_at=now,provenance=evidence))
        if body.kind=="support":
            await session.execute(insert(t.support_cases).values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
                journey_id=journey["id"],state="open").on_conflict_do_nothing(index_elements=[t.support_cases.c.merchant_id,t.support_cases.c.workspace_id,t.support_cases.c.journey_id]))
    elif body.kind=="reminder":
        await session.execute(t.customer_evidence.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
            customer_id=journey["customer_id"],kind="reminder",value={"date":body.due_at.isoformat(),"timezone":body.timezone,"channel":body.channel,"variant_id":str(journey["variant_id"])},effective_at=now,provenance=evidence))
        await session.execute(t.reminders.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,journey_id=journey["id"],
            event_key=body.event_key,due_at=body.due_at,timezone=body.timezone,channel=body.channel,state="scheduled"))
        draft=await scoped_one(session,repo,t.plan_revisions,journey["plan_revision_id"])
        policy=await scoped_one(session,repo,t.policies,draft["policy_id"])
        variant=await scoped_one(session,repo,t.variants,journey["variant_id"])
        customer=await scoped_one(session,repo,t.customers,journey["customer_id"])
        payload={"customer_id":str(customer["id"]),"variant_id":str(variant["id"]),"customer_alias":customer["display_alias"],"variant_title":variant["title"],
            "provider_variant_id":variant["provider_variant_id"],"kind":"reminder","channel":body.channel,"text":"As requested, here's your reminder about "+variant["title"]+". Would you like to reorder the same product?",
            "cost_minor":25,"currency":"INR","source_mode":"simulated","confirmed_event_key":str(body.event_key),"timezone":body.timezone,
            "plan_revision_id":str(draft["id"]),"policy_id":str(policy["id"])}
        await create_action(session,scope,journey,policy,payload,body.due_at,draft["expires_at"],auto=policy["config_json"]["mode"]=="bounded")
    elif body.kind=="outside_purchase":
        await session.execute(t.customer_evidence.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
            customer_id=journey["customer_id"],kind="purchase_hold",value={"active":True},effective_at=now,provenance=evidence))
    # An outside purchase event is a labelled demo signal; no payment or Shopify order is fabricated.
    if body.kind!="reminder":
        await session.execute(t.reminders.update().where(repo.where(t.reminders),t.reminders.c.journey_id==journey["id"],t.reminders.c.state=="scheduled").values(state="cancelled"))
    current=await agent(session,scope,True)
    await session.execute(t.agents.update().where(repo.where(t.agents)).values(version=current["version"]+1,dispatch_epoch=current["dispatch_epoch"]+1))
    await emit(session,scope,"customer."+body.kind,journey["customer_id"],{"event_key":str(body.event_key),"source_mode":"simulated"})
    await session.execute(t.audit_events.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,actor_id=scope.user_id,
        event_type="demo.customer."+body.kind,target_id=journey["id"],correlation_id=correlation,details={"event_key":str(body.event_key)}))
    return await view(session,scope)


async def view(session,scope):
    repo=ScopedRepository(session,scope)
    workspace=await repo.workspace();current=await agent(session,scope)
    review=await manifest(session,scope)
    if review:
        decided=await existing_approval(session,repo,"plan",uuid.UUID(review["id"]))
        review["decision"]=decided["decision"] if decided else None
    customers={str(c["id"]):c["display_alias"] for c in await planning.rows(session,repo,t.customers)}
    journeys=[{**dict(j),"customer_alias":customers.get(str(j["customer_id"]),"Unknown")} for j in await planning.rows(session,repo,t.journeys)]
    return ExecutionView(environment=workspace["environment"],version=current["version"] if current else 0,paused=current["paused"] if current else False,
        plan_review=jsonable_encoder(review),journeys=jsonable_encoder(journeys),
        actions=jsonable_encoder([dict(a) for a in await planning.rows(session,repo,t.proposed_actions)]),
        jobs=jsonable_encoder([{k:v for k,v in dict(j).items() if k!="lease_token"} for j in await planning.rows(session,repo,t.jobs)]),
        receipts=jsonable_encoder([dict(r) for r in await planning.rows(session,repo,t.action_receipts)]),
        support_cases=jsonable_encoder([dict(c) for c in await planning.rows(session,repo,t.support_cases)]),
        reminders=jsonable_encoder([dict(r) for r in await planning.rows(session,repo,t.reminders)]),
        budgets=jsonable_encoder([dict(b) for b in await planning.rows(session,repo,t.budget_buckets)]),
        cohort_count=len(await planning.rows(session,repo,t.cohort_assignments)),
        notice="Demo execution uses durable approvals and simulated receipts. No external message, call, checkout or charge is created.")
