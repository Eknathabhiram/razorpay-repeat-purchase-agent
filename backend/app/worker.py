"""PostgreSQL leased worker. Demo adapter only; uncertain attempts are never replayed."""
import asyncio
import argparse
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from . import schema as t, planning, execution
from .db import Database
from .errors import ApplicationError
from .repositories import ScopedRepository, Scope
from .settings import Settings
from .runtime import run
from .interaction_content import choices, followup_text


async def validate(session,scope,action,now,check_contact_hours=True,require_action_approval=True):
    repo=ScopedRepository(session,scope)
    workspace=await repo.workspace()
    if workspace["environment"]!="demo" or action["payload"]["source_mode"]!="simulated": return "mode_blocked"
    agent=await execution.agent(session,scope)
    if not agent or agent["paused"]: return "agent_paused"
    if action["expires_at"]<=now: return "approval_expired"
    journey=await execution.scoped_one(session,repo,t.journeys,action["journey_id"])
    if journey["state"] in ("opted_out","support","purchased","unknown_outcome","purchase_under_review","refused"): return "customer_"+journey["state"]
    if journey["state"]=="reply_review" and (action["payload"].get("kind") not in ("human_acknowledgement","checkout_link","choice_followup") or action["payload"].get("actor_id")!=str(journey["owner_id"])): return "customer_reply_review"
    variant=await execution.scoped_one(session,repo,t.variants,journey["variant_id"])
    if action["payload"].get("provider_variant_id")!=variant["provider_variant_id"] or action["payload"].get("variant_id")!=str(variant["id"]): return "variant_scope_changed"
    templates={"reorder_check":"Would you like to reorder your "+variant["title"]+"? You can tell us if you need more time. Reply STOP to opt out.",
        "reminder":"As requested, here's your reminder about "+variant["title"]+". Would you like to reorder the same product?",
        "human_acknowledgement":"Thanks for your reply. A team member is reviewing your request."}
    if action["payload"].get("kind")=="checkout_link":
        from .commerce import validate_link
        reason=await validate_link(session,scope,action,now)
        if reason:return reason
    elif action['payload'].get('kind') == 'automated_reply':
        from .automation import validate_reply
        reason=await validate_reply(session,scope,action,journey,variant,now)
        if reason:return reason
    elif action['payload'].get('kind') == 'choice_followup':
        payload=action['payload'];quantity=payload.get('quantity',1)
        if not isinstance(quantity,int) or not 1 <= quantity <= 20: return 'quantity_invalid'
        expected=followup_text(payload.get('interaction_step'),variant['title'],quantity)
        if not expected or payload.get('text') != expected: return 'content_unsupported'
        if payload.get('reply_buttons',[]) != choices(payload.get('interaction_step'),quantity): return 'buttons_changed'
        proof=(await session.execute(sa.select(t.event_outbox).where(repo.where(t.event_outbox),
            t.event_outbox.c.event_type=='whatsapp.choice', t.event_outbox.c.subject_id==journey['customer_id'],
            t.event_outbox.c.details['message_ref'].astext==payload.get('reply_ref')))).mappings().first()
        if not proof or proof['details'].get('journey_id') != str(journey['id']): return 'reply_context_missing'
    elif action["payload"].get("kind") not in templates or action["payload"].get("text")!=templates[action["payload"]["kind"]]: return "content_unsupported"
    if action['payload'].get('kind') in ('reorder_check','reminder') and 'reply_buttons' in action['payload'] and action['payload']['reply_buttons'] != choices(action['payload']['kind']): return 'buttons_changed'
    if action['payload'].get('conversation_event_id') and action['payload'].get('kind')!='automated_reply':
        from .automation import validate_reply
        reason=await validate_reply(session,scope,action,journey,variant,now)
        if reason:return reason
    if journey["owner_id"]:
        if action["payload"].get("kind") not in ("human_acknowledgement","checkout_link","choice_followup") or action["payload"].get("actor_id")!=str(journey["owner_id"]): return "human_takeover"
    elif action["payload"].get("kind")=="human_acknowledgement" or action["payload"].get("kind")=="checkout_link" and action["payload"].get("actor_id"): return "human_owner_changed"
    draft=await planning.latest(session,repo,t.plan_revisions)
    policy=await planning.latest(session,repo,t.policies)
    if not draft or draft["id"]!=journey["plan_revision_id"] or draft["expires_at"]<=now: return "plan_stale"
    if not policy or action["policy_id"]!=policy["id"]: return "policy_changed"
    decision=await execution.existing_approval(session,repo,"plan",draft["id"])
    if not decision or decision["decision"]!="approve": return "plan_not_approved"
    if require_action_approval:
        decision=await execution.existing_approval(session,repo,"action",action["id"])
        if not decision or decision["decision"]!="approve" or decision["digest"]!=action["digest"]: return "action_not_approved"
    if planning.digest(action["payload"])!=action["digest"]: return "payload_changed"
    # Current facts determine authority, not the approval-time read model.
    fresh=await planning.compute(session,scope,customer_id=journey['customer_id'])
    match=next((i for i in fresh if i["customer_id"]==str(journey["customer_id"]) and i["variant_id"]==str(journey["variant_id"])),None)
    if not match or not match["eligible"]: return "facts_changed:"+",".join(match["exclusion_codes"] if match else ["scope_missing"])
    point=(await planning.rows(session,repo,t.sync_checkpoints))[0]
    if point["facts_version"]!=draft["facts_version"]: return "facts_generation_changed"
    if point["synced_at"]<now-timedelta(hours=24): return "facts_stale"
    if action["payload"]["channel"]!="whatsapp": return "channel_unverified"
    if check_contact_hours:
        local=now.astimezone(ZoneInfo(policy["config_json"]["timezone"]))
        clock=local.strftime("%H:%M")
        if not policy["config_json"]["contact_start"]<=clock<policy["config_json"]["contact_end"]: return "quiet_hours"
    guard=(await session.execute(sa.select(t.contact_guards).where(repo.where(t.contact_guards),t.contact_guards.c.customer_id==journey["customer_id"]).with_for_update())).mappings().first()
    if guard and guard["inflight_action_id"]: return "contact_inflight_or_unknown"
    count=await session.scalar(sa.select(sa.func.count()).select_from(t.contact_ledger).where(repo.where(t.contact_ledger),
        t.contact_ledger.c.customer_id==journey["customer_id"],t.contact_ledger.c.created_at>now-timedelta(days=7),t.contact_ledger.c.state.in_(("submitting","submitted","unknown"))))
    if count>=policy["config_json"]["contact_cap"]: return "weekly_contact_cap"
    bucket=(await session.execute(sa.select(t.budget_buckets).where(repo.where(t.budget_buckets),t.budget_buckets.c.policy_id==policy["id"]).with_for_update())).mappings().first()
    cost=action["payload"].get("cost_minor")
    if not isinstance(cost,int) or cost<0: return "cost_unknown"
    if not bucket or bucket["reserved_minor"]+bucket["spent_minor"]+cost>bucket["cap_minor"]: return "budget_cap"
    return None


async def claim(db,scope,now):
    repo_scope=scope
    async with db.unit_of_work() as session:
        repo=ScopedRepository(session,repo_scope)
        # Claims do not authorize dispatch; preflight rechecks all guards under the workspace lock.
        agent=await execution.agent(session,scope)
        if not agent or agent["paused"]: return None
        conversation=sa.exists(sa.select(t.proposed_actions.c.id).where(repo.where(t.proposed_actions),t.proposed_actions.c.id==t.jobs.c.action_id,
            t.proposed_actions.c.payload['kind'].astext.in_(('automated_reply','checkout_link','human_acknowledgement','choice_followup'))))
        job=(await session.execute(sa.select(t.jobs).where(repo.where(t.jobs),t.jobs.c.state=="ready",t.jobs.c.due_at<=now)
            .order_by(conversation.desc(),t.jobs.c.due_at,t.jobs.c.id).with_for_update(skip_locked=True).limit(1))).mappings().first()
        if not job: return None
        token=uuid.uuid4()
        await session.execute(t.jobs.update().where(repo.where(t.jobs),t.jobs.c.id==job["id"]).values(state="leased",lease_token=token,
            lease_until=now+timedelta(seconds=60),attempts=job["attempts"]+1))
        return {"id":job["id"],"action_id":job["action_id"],"lease_token":token}


async def prepare(db,scope,claim_row,now):
    async with db.unit_of_work() as session:
        repo=ScopedRepository(session,scope);await repo.workspace(lock=True)
        job=await execution.scoped_one(session,repo,t.jobs,claim_row["id"],True)
        if job["state"]!="leased" or job["lease_token"]!=claim_row["lease_token"] or job["lease_until"]<=now:
            return None
        action=await execution.scoped_one(session,repo,t.proposed_actions,job["action_id"])
        if action["state"]!="ready":
            await session.execute(t.jobs.update().where(repo.where(t.jobs),t.jobs.c.id==job["id"]).values(state="held",blocked_reason="action_not_ready",lease_token=None,lease_until=None));return None
        reason=await validate(session,scope,action,now)
        if reason:
            values={"state":"held","blocked_reason":reason,"lease_token":None,"lease_until":None}
            if reason=="quiet_hours":
                policy=await execution.scoped_one(session,repo,t.policies,action["policy_id"])
                local=now.astimezone(ZoneInfo(policy["config_json"]["timezone"]))
                hour,minute=map(int,policy["config_json"]["contact_start"].split(":"))
                due=local.replace(hour=hour,minute=minute,second=0,microsecond=0)
                if due<=local: due+=timedelta(days=1)
                values.update(state="ready",due_at=due.astimezone(timezone.utc))
            else:
                await session.execute(t.proposed_actions.update().where(repo.where(t.proposed_actions),t.proposed_actions.c.id==action["id"]).values(state="held"))
                if (await execution.scoped_one(session,repo,t.policies,action['policy_id']))['config_json'].get('conversation_automation'):
                    from .automation import exception
                    journey=await execution.scoped_one(session,repo,t.journeys,action['journey_id'])
                    await exception(session,scope,journey,reason)
            await session.execute(t.jobs.update().where(repo.where(t.jobs),t.jobs.c.id==job["id"]).values(**values));return None
        journey=await execution.scoped_one(session,repo,t.journeys,action["journey_id"])
        bucket=(await session.execute(sa.select(t.budget_buckets).where(repo.where(t.budget_buckets),t.budget_buckets.c.policy_id==action["policy_id"]))).mappings().one()
        cost=action["payload"]["cost_minor"]
        identifier=uuid.uuid4();agent=await execution.agent(session,scope)
        await session.execute(t.reservations.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,action_id=action["id"],bucket_id=bucket["id"],amount_minor=cost,state="held"))
        await session.execute(t.budget_buckets.update().where(repo.where(t.budget_buckets),t.budget_buckets.c.id==bucket["id"]).values(reserved_minor=bucket["reserved_minor"]+cost))
        await session.execute(t.contact_ledger.insert().values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,customer_id=journey["customer_id"],action_id=action["id"],channel=action["payload"]["channel"],state="submitting"))
        await session.execute(t.contact_guards.update().where(repo.where(t.contact_guards),t.contact_guards.c.customer_id==journey["customer_id"]).values(inflight_action_id=action["id"]))
        await session.execute(t.dispatch_attempts.insert().values(id=identifier,merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,action_id=action["id"],lease_token=claim_row["lease_token"],epoch=agent["dispatch_epoch"],state="submitting"))
        await session.execute(t.proposed_actions.update().where(repo.where(t.proposed_actions),t.proposed_actions.c.id==action["id"]).values(state="submitting"))
        await session.execute(t.jobs.update().where(repo.where(t.jobs),t.jobs.c.id==job["id"]).values(state="submitting"))
        await execution.emit(session,scope,"dispatch.submitting",action["id"],{"attempt_id":str(identifier),"source_mode":"simulated"})
        return identifier


async def demo_submit(db,scope,attempt_id,outcome):
    """Separate durable simulated transport evidence, never an external provider call."""
    if outcome=="unknown": return None
    async with db.unit_of_work() as session:
        repo=ScopedRepository(session,scope)
        attempt=await execution.scoped_one(session,repo,t.dispatch_attempts,attempt_id)
        if attempt["state"]!="submitting": return None
        action=await execution.scoped_one(session,repo,t.proposed_actions,attempt["action_id"])
        if (await repo.workspace())["environment"]!="demo" or action["payload"]["source_mode"]!="simulated":
            raise ApplicationError(422,"MODE_BLOCKED","Simulation adapter cannot dispatch real workspace actions.")
        status="submitted" if outcome=="accepted" else "definite_failure"
        reference="demo:"+str(attempt_id) if outcome=="accepted" else None
        await session.execute(insert(t.demo_transport).values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
            attempt_id=attempt_id,status=status,provider_ref=reference).on_conflict_do_nothing(index_elements=[t.demo_transport.c.merchant_id,t.demo_transport.c.workspace_id,t.demo_transport.c.attempt_id]))
        return {"status":status,"provider_ref":reference}


async def finish(db,scope,attempt_id,result):
    async with db.unit_of_work() as session:
        repo=ScopedRepository(session,scope);await repo.workspace(lock=True)
        attempt=await execution.scoped_one(session,repo,t.dispatch_attempts,attempt_id,True)
        if attempt["state"] in ("submitted","definite_failure"):return
        if attempt["state"]=="unknown" and not result:return
        action=await execution.scoped_one(session,repo,t.proposed_actions,attempt["action_id"])
        journey=await execution.scoped_one(session,repo,t.journeys,action["journey_id"])
        status=result["status"] if result else "unknown"
        await session.execute(insert(t.action_receipts).values(merchant_id=scope.merchant_id,workspace_id=scope.workspace_id,
            attempt_id=attempt_id,status=status,provider_ref=result["provider_ref"] if result else None,source_mode="simulated").on_conflict_do_nothing(
                index_elements=[t.action_receipts.c.merchant_id,t.action_receipts.c.workspace_id,t.action_receipts.c.attempt_id,t.action_receipts.c.status]))
        await session.execute(t.dispatch_attempts.update().where(repo.where(t.dispatch_attempts),t.dispatch_attempts.c.id==attempt_id).values(state=status))
        await session.execute(t.proposed_actions.update().where(repo.where(t.proposed_actions),t.proposed_actions.c.id==action["id"]).values(state=status))
        await session.execute(t.contact_ledger.update().where(repo.where(t.contact_ledger),t.contact_ledger.c.action_id==action["id"]).values(state=status))
        await session.execute(t.jobs.update().where(repo.where(t.jobs),t.jobs.c.action_id==action["id"]).values(state="unknown" if status=="unknown" else "done",
            blocked_reason="unknown_outcome_requires_review" if status=="unknown" else None,lease_token=None,lease_until=None))
        if action["payload"].get("kind")=="checkout_link" and status=="submitted":
            await session.execute(t.checkout_preparations.update().where(repo.where(t.checkout_preparations),t.checkout_preparations.c.id==uuid.UUID(action["payload"]["preparation_id"]),t.checkout_preparations.c.state=="link_proposed").values(state="link_submitted"))
        if status!="unknown":
            reservation=(await session.execute(sa.select(t.reservations).where(repo.where(t.reservations),t.reservations.c.action_id==action["id"]).with_for_update())).mappings().one()
            if reservation["state"]=="held":
                bucket=await execution.scoped_one(session,repo,t.budget_buckets,reservation["bucket_id"],True)
                await session.execute(t.budget_buckets.update().where(repo.where(t.budget_buckets),t.budget_buckets.c.id==bucket["id"]).values(
                    reserved_minor=bucket["reserved_minor"]-reservation["amount_minor"],spent_minor=bucket["spent_minor"]+(reservation["amount_minor"] if status=="submitted" else 0)))
                await session.execute(t.reservations.update().where(repo.where(t.reservations),t.reservations.c.id==reservation["id"]).values(state="committed" if status=="submitted" else "released"))
            await session.execute(t.contact_guards.update().where(repo.where(t.contact_guards),t.contact_guards.c.customer_id==journey["customer_id"],t.contact_guards.c.inflight_action_id==action["id"]).values(inflight_action_id=None))
            # Protective states/ownership accepted during submission remain intact.
            if journey["state"] not in ("opted_out","support","purchased","purchase_under_review","refused","reply_review"):
                next_state="checkout_pending" if action["payload"].get("kind")=="checkout_link" else "awaiting_reply"
                await session.execute(t.journeys.update().where(repo.where(t.journeys),t.journeys.c.id==journey["id"]).values(state=next_state if status=="submitted" else "dispatch_failed"))
            if action["payload"].get("confirmed_event_key"):
                await session.execute(t.reminders.update().where(repo.where(t.reminders),t.reminders.c.event_key==uuid.UUID(action["payload"]["confirmed_event_key"]),t.reminders.c.state=="scheduled").values(state="sent" if status=="submitted" else "failed"))
        elif journey["state"] not in ("opted_out","support","purchased","purchase_under_review","refused","reply_review"):
            await session.execute(t.journeys.update().where(repo.where(t.journeys),t.journeys.c.id==journey["id"]).values(state="unknown_outcome",owner_id=journey["owner_id"] or scope.user_id))
        if status=="submitted":
            from .whatsapp import materialize_demo
            await materialize_demo(session,scope)
        await execution.emit(session,scope,"dispatch."+status,action["id"],{"attempt_id":str(attempt_id),"source_mode":"simulated"})


async def recover(db,scope,now):
    async with db.unit_of_work() as session:
        repo=ScopedRepository(session,scope);await repo.workspace(lock=True)
        jobs=await planning.rows(session,repo,t.jobs)
        for job in jobs:
            if job["state"]=="leased" and job["lease_until"] and job["lease_until"]<=now:
                await session.execute(t.jobs.update().where(repo.where(t.jobs),t.jobs.c.id==job["id"]).values(state="ready",lease_token=None,lease_until=None))
        attempts=[dict(a) for a in await planning.rows(session,repo,t.dispatch_attempts) if a["state"] in ("submitting","unknown")]
        transport={r["attempt_id"]:dict(r) for r in await planning.rows(session,repo,t.demo_transport)}
        recoverable=[]
        for attempt in attempts:
            job=next((j for j in jobs if j["action_id"]==attempt["action_id"]),None)
            if attempt["id"] in transport or attempt["state"]=="unknown" or (job and job["lease_until"] and job["lease_until"]<=now):
                recoverable.append((attempt["id"],transport.get(attempt["id"])))
        # Deduplicated local read-model consumer; no external publish side effect.
        consumed=sa.exists(sa.select(t.event_consumptions.c.id).where(repo.where(t.event_consumptions),t.event_consumptions.c.event_id==t.event_outbox.c.id,t.event_consumptions.c.consumer=='execution.read_model'))
        pending=sa.select(sa.func.gen_random_uuid(),t.event_outbox.c.merchant_id,t.event_outbox.c.workspace_id,t.event_outbox.c.id,sa.literal('execution.read_model')).where(repo.where(t.event_outbox),~consumed).order_by(t.event_outbox.c.created_at).limit(1000)
        await session.execute(insert(t.event_consumptions).from_select(['id','merchant_id','workspace_id','event_id','consumer'],pending).on_conflict_do_nothing(index_elements=[t.event_consumptions.c.merchant_id,t.event_consumptions.c.workspace_id,t.event_consumptions.c.event_id,t.event_consumptions.c.consumer]))
    for attempt_id,result in recoverable: await finish(db,scope,attempt_id,result)


async def run_once(db,scope,outcome="accepted",limit=10,now=None,crash=None):
    now=now or datetime.now(timezone.utc)
    async with db.unit_of_work() as session:
        if (await ScopedRepository(session,scope).workspace())["environment"]!="demo":
            raise ApplicationError(422,"SIMULATION_ONLY","Execution remains blocked outside Demo.")
    await recover(db,scope,now)
    processed=0
    for _ in range(limit):
        claimed=await claim(db,scope,now)
        if not claimed:break
        if crash=="after_claim":return
        attempt_id=await prepare(db,scope,claimed,now)
        if not attempt_id:continue
        if crash=="after_submitting":return
        result=await demo_submit(db,scope,attempt_id,outcome)
        if crash=="after_acceptance":return
        await finish(db,scope,attempt_id,result);processed+=1
    return processed


async def main(workspace_id,once):
    db=Database(Settings.from_environment().database_url)
    try:
        async with db.unit_of_work() as session:
            workspace=(await session.execute(sa.select(t.workspaces).where(t.workspaces.c.id==workspace_id,t.workspaces.c.environment=="demo"))).mappings().one()
            user=(await session.execute(sa.select(t.memberships.c.user_id).join(t.users,t.users.c.id==t.memberships.c.user_id).where(t.memberships.c.merchant_id==workspace["merchant_id"],t.memberships.c.role=="owner",t.users.c.disabled_at.is_(None)))).scalar_one()
            scope=Scope(workspace["merchant_id"],workspace_id,user,"operator")
        while True:
            await run_once(db,scope)
            if once:break
            await asyncio.sleep(1)
    finally:await db.close()


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--workspace",type=uuid.UUID,required=True);parser.add_argument("--once",action="store_true")
    args=parser.parse_args();run(main(args.workspace,args.once))
