"""Persist explicitly simulated Stage 02 interface state, separate from real providers."""
import os
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, dialect
from sqlalchemy.engine import make_url
from alembic import op

revision = "0002_demo_ui"
down_revision = "0001_foundation"
branch_labels = depends_on = None


def upgrade():
    op.create_table("demo_ui_states",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("merchant_id", UUID, nullable=False),
        sa.Column("workspace_id", UUID, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="0"),
        sa.Column("state_json", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["merchant_id", "workspace_id"], ["workspaces.merchant_id", "workspaces.id"]),
        sa.UniqueConstraint("merchant_id", "workspace_id", "id"),
        sa.UniqueConstraint("merchant_id", "workspace_id"))
    url = os.getenv("APP_DATABASE_URL")
    if url:
        role = dialect().identifier_preparer.quote(make_url(url).username)
        op.execute("GRANT SELECT,INSERT,UPDATE,DELETE ON demo_ui_states TO " + role)


def downgrade():
    op.drop_table("demo_ui_states")
