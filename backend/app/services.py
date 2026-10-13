import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from fastapi.encoders import jsonable_encoder
from . import schema as t
from .errors import ApplicationError
from .repositories import ScopedRepository


async def rename_workspace(session, scope, name, expected_version, key, correlation_id):
    request_hash = hashlib.sha256(json.dumps(
        {"name": name, "expected_version": expected_version}, sort_keys=True).encode()).hexdigest()
    repository = ScopedRepository(session, scope)
    statement = insert(t.idempotency).values(
        merchant_id=scope.merchant_id, workspace_id=scope.workspace_id, actor_id=scope.user_id,
        operation="workspace.rename", key=key, request_hash=request_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    ).on_conflict_do_nothing(index_elements=[
        t.idempotency.c.merchant_id, t.idempotency.c.workspace_id, t.idempotency.c.actor_id,
        t.idempotency.c.operation, t.idempotency.c.key])
    await session.execute(statement)
    record = (await session.execute(sa.select(t.idempotency).where(
        repository.where(t.idempotency), t.idempotency.c.actor_id == scope.user_id,
        t.idempotency.c.operation == "workspace.rename", t.idempotency.c.key == key
    ).with_for_update())).mappings().one()
    if record["request_hash"] != request_hash:
        raise ApplicationError(409, "IDEMPOTENCY_CONFLICT", "This request key was used for different content.")
    if record["result_json"] is not None:
        return record["result_json"]
    before = await repository.workspace(lock=True)
    if before["version"] != expected_version:
        raise ApplicationError(409, "VERSION_CONFLICT", "Workspace changed. Refresh before saving.")
    version, receipt = before["version"] + 1, uuid.uuid4()
    await session.execute(t.workspaces.update().where(
        t.workspaces.c.id == scope.workspace_id, t.workspaces.c.merchant_id == scope.merchant_id
    ).values(name=name, version=version, updated_at=sa.func.now()))
    await session.execute(t.audit_events.insert().values(
        id=receipt, merchant_id=scope.merchant_id, workspace_id=scope.workspace_id,
        actor_id=scope.user_id, event_type="workspace.renamed", target_id=scope.workspace_id,
        correlation_id=correlation_id, details={"before": before["name"], "after": name, "version": version}))
    result = jsonable_encoder({"id": scope.workspace_id, "name": name, "version": version,
                               "receipt_id": receipt})
    await session.execute(t.idempotency.update().where(t.idempotency.c.id == record["id"])
                          .values(result_json=result))
    return result


async def record_shopify_check(session, scope, connector_id, snapshot, correlation_id):
    repository = ScopedRepository(session, scope)
    connector = await repository.connector(connector_id)
    if connector["provider"] != "shopify" or connector["source_mode"] != "test":
        raise ApplicationError(422, "MODE_MISMATCH", "A Shopify development connector is required.")
    if snapshot["shop"]["myshopifyDomain"] != connector["provider_account_id"]:
        raise ApplicationError(409, "ACCOUNT_MISMATCH", "Provider returned a different development store.")
    now, evidence = datetime.now(timezone.utc), uuid.uuid4()
    await session.execute(t.connectors.update().where(repository.where(t.connectors),
        t.connectors.c.id == connector_id).values(
        state="degraded" if snapshot["warnings"] else "healthy", last_checked_at=now,
        version=t.connectors.c.version + 1, updated_at=now))
    for capability, available in (("read_catalogue", snapshot["products"] is not None),
                                  ("read_customers", snapshot["customers"] is not None),
                                  ("read_orders", snapshot["orders"] is not None)):
        await session.execute(t.capabilities.update().where(repository.where(t.capabilities),
            t.capabilities.c.connector_id == connector_id, t.capabilities.c.capability == capability
        ).values(status="available" if available else "blocked", verified_at=now,
                 evidence_ref=str(evidence), reason=None if available else "Provider access unavailable",
                 updated_at=now))
    # Only capability counts are retained; snapshots/PII are not an audit payload.
    counts = {k: len(snapshot[k]) if snapshot[k] is not None else None
              for k in ("products", "customers", "orders", "draftOrders")}
    await session.execute(t.audit_events.insert().values(
        id=evidence, merchant_id=scope.merchant_id, workspace_id=scope.workspace_id,
        actor_id=scope.user_id, event_type="connector.checked", target_id=connector_id,
        correlation_id=correlation_id, details={"counts": counts, "mode": "test", "partial": bool(snapshot["warnings"])}))
    return {"counts": counts, "receipt_id": str(evidence), "source_mode": "test"}
