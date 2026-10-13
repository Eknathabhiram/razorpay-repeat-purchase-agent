from dataclasses import dataclass
from uuid import UUID
import sqlalchemy as sa
from . import schema as t
from .errors import ApplicationError


@dataclass(frozen=True)
class Scope:
    merchant_id: UUID
    workspace_id: UUID
    user_id: UUID
    role: str


async def resolve_scope(session, user_id, workspace_id, mutate=False):
    row = (await session.execute(sa.select(t.workspaces, t.memberships.c.role).select_from(
        t.workspaces.join(t.memberships, t.memberships.c.merchant_id == t.workspaces.c.merchant_id)
    ).where(t.workspaces.c.id == workspace_id, t.memberships.c.user_id == user_id))).mappings().first()
    if not row:
        raise ApplicationError(404, "NOT_FOUND", "Workspace not found.")
    if mutate and row["role"] not in ("owner", "operator"):
        raise ApplicationError(403, "ROLE_REQUIRED", "An operator role is required for this action.")
    return Scope(row["merchant_id"], row["id"], user_id, row["role"])


class ScopedRepository:
    def __init__(self, session, scope):
        self.session, self.scope = session, scope

    def where(self, table):
        return sa.and_(table.c.merchant_id == self.scope.merchant_id,
                       table.c.workspace_id == self.scope.workspace_id)

    async def workspace(self, lock=False):
        query = sa.select(t.workspaces).where(
            t.workspaces.c.merchant_id == self.scope.merchant_id,
            t.workspaces.c.id == self.scope.workspace_id)
        if lock:
            # Updates do not change keys. NO KEY UPDATE remains compatible with
            # FK KEY SHARE locks from concurrent idempotency/audit inserts.
            query = query.with_for_update(key_share=True)
        return (await self.session.execute(query)).mappings().one()

    async def connector(self, connector_id):
        row = (await self.session.execute(sa.select(t.connectors).where(
            self.where(t.connectors), t.connectors.c.id == connector_id).with_for_update())).mappings().first()
        if not row:
            raise ApplicationError(404, "NOT_FOUND", "Connector not found in this workspace.")
        return row

    async def connector_list(self):
        rows = (await self.session.execute(sa.select(t.connectors).where(self.where(t.connectors))
                                          .order_by(t.connectors.c.provider))).mappings().all()
        result = []
        for row in rows:
            caps = (await self.session.execute(sa.select(t.capabilities.c.capability,
                t.capabilities.c.status, t.capabilities.c.verified_at, t.capabilities.c.reason,
                t.capabilities.c.evidence_ref).where(self.where(t.capabilities),
                t.capabilities.c.connector_id == row["id"]))).mappings().all()
            result.append({k: row[k] for k in ("id", "provider", "source_mode", "provider_environment",
                                              "state", "last_checked_at", "version")})
            result[-1]["capabilities"] = [dict(c) for c in caps]
        return result
