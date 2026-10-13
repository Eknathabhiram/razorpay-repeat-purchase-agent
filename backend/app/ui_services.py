"""Stage 02 simulation read models. No provider sends or agent authority."""
import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from . import schema as t
from .errors import ApplicationError
from .repositories import ScopedRepository
from .ui_models import DemoState, UIReadModel, initial_demo


async def read_ui(session, scope):
    repo = ScopedRepository(session, scope)
    workspace = await repo.workspace()
    if workspace["environment"] != "demo":
        return UIReadModel(source_mode="unavailable", version=0, state=None,
                           notice="The agent engine is not connected in this environment. Store reads are available in Connections.")
    row = (await session.execute(sa.select(t.demo_ui_states).where(repo.where(t.demo_ui_states)))).mappings().first()
    return UIReadModel(source_mode="simulated", version=row["version"] if row else 0,
                       state=DemoState.model_validate(row["state_json"]) if row else initial_demo(),
                       notice="Synthetic customer journeys. Actions persist in this demo workspace; no outreach or payment occurs.")


async def demo_command(session, scope, command, key, correlation):
    repo = ScopedRepository(session, scope)
    workspace = await repo.workspace(lock=True)
    if workspace["environment"] != "demo":
        raise ApplicationError(422, "SIMULATION_ONLY", "Agent actions are available only in the Demo workspace at this stage.")
    request_hash = hashlib.sha256(json.dumps(command.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()
    await session.execute(insert(t.idempotency).values(
        merchant_id=scope.merchant_id, workspace_id=scope.workspace_id, actor_id=scope.user_id,
        operation="demo.ui.command", key=key, request_hash=request_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)).on_conflict_do_nothing(
        index_elements=[t.idempotency.c.merchant_id, t.idempotency.c.workspace_id,
                        t.idempotency.c.actor_id, t.idempotency.c.operation, t.idempotency.c.key]))
    record = (await session.execute(sa.select(t.idempotency).where(repo.where(t.idempotency),
        t.idempotency.c.actor_id == scope.user_id, t.idempotency.c.operation == "demo.ui.command",
        t.idempotency.c.key == key).with_for_update())).mappings().one()
    if record["request_hash"] != request_hash:
        raise ApplicationError(409, "IDEMPOTENCY_CONFLICT", "Request key was used for different content.")
    if record["result_json"]:
        return UIReadModel.model_validate(record["result_json"])
    current = await read_ui(session, scope)
    if current.version != command.expected_version:
        raise ApplicationError(409, "VERSION_CONFLICT", "This workspace changed. Refresh and review the current state.")
    state = current.state
    action = command.action
    if action == "reset":
        state = initial_demo(command.scenario or "operating")
    elif action == "pause":
        state.paused = True
    elif action == "resume":
        if state.disconnected or state.plan_needs_review:
            raise ApplicationError(422, "PREFLIGHT_BLOCKED", "Review the connection and current plan before resuming.")
        state.paused = False
    elif action in ("takeover", "handback"):
        if action == "handback" and (state.paused or state.disconnected or state.plan_needs_review):
            raise ApplicationError(422, "PREFLIGHT_BLOCKED", "Resolve current holds before handing back.")
        state.taken_over = action == "takeover"
    elif action == "assign_support":
        state.support_assigned = True
    elif action == "install":
        state.installed = True
        state.plan_approved = False
        if command.policy:
            state.policy = state.policy.model_copy(update={
                "mode": command.policy.mode, "version": state.policy.version + 1})
    elif action == "approve_plan":
        if state.paused or state.disconnected or not state.installed:
            raise ApplicationError(422, "PREFLIGHT_BLOCKED", "Finish setup and resolve holds before approval.")
        selected = list(dict.fromkeys(command.selected or []))
        if state.order_confirmed:
            selected = [s for s in selected if s != "meera"]
        if not selected:
            raise ApplicationError(422, "AUDIENCE_EMPTY", "Select at least one eligible customer.")
        state.selected, state.assigned = selected, list(dict.fromkeys(state.assigned + selected))
        state.plan_approved, state.plan_needs_review = True, False
    elif action == "reject_plan":
        state.plan_approved = False
    elif action == "save_policy":
        policy = command.policy
        if not policy or policy.end <= policy.start:
            raise ApplicationError(422, "INVALID_POLICY", "Contact end time must be later than start time.")
        if any(int(part) > maximum for time in (policy.start, policy.end)
               for part, maximum in zip(time.split(":"), (23, 59))):
            raise ApplicationError(422, "INVALID_POLICY", "Use valid contact hours.")
        state.policy = policy.model_copy(update={"version": state.policy.version + 1})
        state.plan_needs_review = state.plan_approved
    elif action == "approve_checkout":
        if (state.paused or state.disconnected or state.plan_needs_review or
            not state.plan_approved or "rahul" not in state.selected or state.scenario != "operating"):
            raise ApplicationError(422, "ACTION_BLOCKED", "Current plan, source and pause checks prevent this send.")
        state.checkout_sent = True
        # Message approval never creates a payment/order.
    state.events = (state.events + [action])[-50:]
    result = UIReadModel(source_mode="simulated", version=current.version + 1, state=state, notice=current.notice)
    await session.execute(insert(t.demo_ui_states).values(merchant_id=scope.merchant_id,
        workspace_id=scope.workspace_id, version=result.version, state_json=state.model_dump(mode="json")
    ).on_conflict_do_update(index_elements=[t.demo_ui_states.c.merchant_id, t.demo_ui_states.c.workspace_id],
        set_={"version": result.version, "state_json": state.model_dump(mode="json"), "updated_at": sa.func.now()}))
    await session.execute(t.audit_events.insert().values(merchant_id=scope.merchant_id,
        workspace_id=scope.workspace_id, actor_id=scope.user_id, event_type="demo." + action,
        target_id=scope.workspace_id, correlation_id=correlation,
        details={"source_mode": "simulated", "version": result.version}))
    await session.execute(t.idempotency.update().where(t.idempotency.c.id == record["id"])
                          .values(result_json=result.model_dump(mode="json")))
    return result
