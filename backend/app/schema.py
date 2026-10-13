"""SQLAlchemy Core mappings. Authority is relational, never a browser state blob."""
import uuid
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = sa.MetaData(naming_convention={
    "pk": "pk_%(table_name)s", "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "ix": "ix_%(table_name)s_%(column_0_name)s", "ck": "ck_%(table_name)s_%(constraint_name)s",
})


def identifier(name="id"):
    return sa.Column(name, UUID(as_uuid=True), primary_key=name == "id",
                     default=uuid.uuid4 if name == "id" else None, nullable=False)


def timestamps():
    return [sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)]


merchants = sa.Table("merchants", metadata, identifier(), sa.Column("name", sa.String(120), nullable=False),
                     sa.Column("default_timezone", sa.String(64), nullable=False),
                     sa.Column("currency", sa.String(3), nullable=False), *timestamps())
users = sa.Table("users", metadata, identifier(),
                 sa.Column("login_identifier", sa.String(120), nullable=False, unique=True),
                 sa.Column("password_digest", sa.Text, nullable=False),
                 sa.Column("disabled_at", sa.DateTime(timezone=True)), *timestamps())
memberships = sa.Table("memberships", metadata,
                       sa.Column("merchant_id", UUID, sa.ForeignKey("merchants.id"), primary_key=True),
                       sa.Column("user_id", UUID, sa.ForeignKey("users.id"), primary_key=True),
                       sa.Column("role", sa.String(16), nullable=False),
                       sa.CheckConstraint("role IN ('owner','operator','viewer')", name="role"))
workspaces = sa.Table("workspaces", metadata, identifier(),
                      sa.Column("merchant_id", UUID, sa.ForeignKey("merchants.id"), nullable=False),
                      sa.Column("environment", sa.String(16), nullable=False),
                      sa.Column("name", sa.String(120), nullable=False),
                      sa.Column("version", sa.Integer, nullable=False, server_default="1"),
                      *timestamps(),
                      sa.UniqueConstraint("merchant_id", "id"),
                      sa.UniqueConstraint("merchant_id", "environment"),
                      sa.CheckConstraint("environment IN ('demo','development','live')", name="environment"))
sessions = sa.Table("sessions", metadata, identifier(),
                    sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
                    sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
                    sa.Column("csrf_hash", sa.String(64), nullable=False),
                    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
                    sa.Column("revoked_at", sa.DateTime(timezone=True)), *timestamps())
login_limits = sa.Table("login_limits", metadata,
                        sa.Column("bucket", sa.String(64), primary_key=True),
                        sa.Column("attempts", sa.Integer, nullable=False),
                        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False))


def scoped_columns():
    return [identifier(), sa.Column("merchant_id", UUID, nullable=False),
            sa.Column("workspace_id", UUID, nullable=False)]


def scoped_constraints():
    return [sa.ForeignKeyConstraint(["merchant_id", "workspace_id"],
                                    ["workspaces.merchant_id", "workspaces.id"]),
            sa.UniqueConstraint("merchant_id", "workspace_id", "id")]


connectors = sa.Table("connectors", metadata, *scoped_columns(),
                      sa.Column("provider", sa.String(30), nullable=False),
                      sa.Column("provider_account_id", sa.String(160)),
                      sa.Column("source_mode", sa.String(16), nullable=False),
                      sa.Column("provider_environment", sa.String(30), nullable=False),
                      sa.Column("credential_ref", sa.String(120)),
                      sa.Column("state", sa.String(24), nullable=False),
                      sa.Column("last_checked_at", sa.DateTime(timezone=True)),
                      sa.Column("version", sa.Integer, server_default="1", nullable=False),
                      *timestamps(), *scoped_constraints(),
                      sa.UniqueConstraint("merchant_id", "workspace_id", "provider"),
                      sa.CheckConstraint("source_mode IN ('simulated','test','live')", name="source_mode"))
capabilities = sa.Table("connector_capabilities", metadata, *scoped_columns(),
                        sa.Column("connector_id", UUID, nullable=False),
                        sa.Column("capability", sa.String(64), nullable=False),
                        sa.Column("status", sa.String(16), nullable=False),
                        sa.Column("verified_at", sa.DateTime(timezone=True)),
                        sa.Column("evidence_ref", sa.String(160)),
                        sa.Column("reason", sa.String(250)),
                        *timestamps(), *scoped_constraints(),
                        sa.ForeignKeyConstraint(["merchant_id", "workspace_id", "connector_id"],
                                                ["connectors.merchant_id", "connectors.workspace_id", "connectors.id"]),
                        sa.UniqueConstraint("merchant_id", "workspace_id", "connector_id", "capability"),
                        sa.CheckConstraint("status IN ('unverified','available','blocked','revoked')", name="status"))
audit_events = sa.Table("audit_events", metadata, *scoped_columns(),
                        sa.Column("actor_id", UUID, sa.ForeignKey("users.id"), nullable=False),
                        sa.Column("event_type", sa.String(80), nullable=False),
                        sa.Column("target_id", UUID, nullable=False),
                        sa.Column("correlation_id", UUID, nullable=False),
                        sa.Column("details", JSONB, nullable=False),
                        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
                        *scoped_constraints())
idempotency = sa.Table("idempotency_records", metadata, *scoped_columns(),
                       sa.Column("actor_id", UUID, sa.ForeignKey("users.id"), nullable=False),
                       sa.Column("operation", sa.String(120), nullable=False),
                       sa.Column("key", UUID, nullable=False),
                       sa.Column("request_hash", sa.String(64), nullable=False),
                       sa.Column("result_json", JSONB),
                       sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
                       *timestamps(), *scoped_constraints(),
                       sa.UniqueConstraint("merchant_id", "workspace_id", "actor_id", "operation", "key"))

demo_ui_states = sa.Table("demo_ui_states", metadata, *scoped_columns(),
                         sa.Column("version", sa.Integer, nullable=False, server_default="0"),
                         sa.Column("state_json", JSONB, nullable=False),
                         *timestamps(), *scoped_constraints(),
                         sa.UniqueConstraint("merchant_id", "workspace_id"))

# Stage 03 domain authority; typed snapshots hold provenance, never session/UI state.
def domain_table(name, *columns, parent=None, immutable=False, unique=()):
    constraints = scoped_constraints()
    if parent:
        field, target = parent
        constraints.append(sa.ForeignKeyConstraint(["merchant_id", "workspace_id", field],
                           [target + ".merchant_id", target + ".workspace_id", target + ".id"]))
    if unique:
        constraints.append(sa.UniqueConstraint("merchant_id", "workspace_id", *unique))
    return sa.Table(name, metadata, *scoped_columns(), *columns, *timestamps(), *constraints)

sync_checkpoints = domain_table("sync_checkpoints",
    sa.Column("resource", sa.String(40), nullable=False), sa.Column("cursor", sa.Text),
    sa.Column("facts_version", sa.Integer, nullable=False), sa.Column("coverage_complete", sa.Boolean, nullable=False),
    sa.Column("notes", JSONB, nullable=False), sa.Column("source_mode", sa.String(16), nullable=False),
    sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False), unique=("resource",))
variants = domain_table("variants", sa.Column("provider_variant_id", sa.Text, nullable=False),
    sa.Column("provider_product_id", sa.Text, nullable=False), sa.Column("title", sa.Text, nullable=False),
    sa.Column("sku", sa.Text), sa.Column("price_minor", sa.BigInteger), sa.Column("currency", sa.String(3)),
    sa.Column("stock", sa.Integer), sa.Column("active", sa.Boolean, nullable=False),
    sa.Column("provenance", JSONB, nullable=False), unique=("provider_variant_id",))
customers = domain_table("customers", sa.Column("provider_customer_id", sa.Text, nullable=False),
    sa.Column("display_alias", sa.Text, nullable=False), sa.Column("identity_state", sa.String(30), nullable=False),
    unique=("provider_customer_id",))
customer_evidence = domain_table("customer_evidence", sa.Column("customer_id", UUID, nullable=False),
    sa.Column("kind", sa.String(30), nullable=False), sa.Column("value", JSONB, nullable=False),
    sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("provenance", JSONB, nullable=False), parent=("customer_id", "customers"))
commerce_orders = domain_table("commerce_orders", sa.Column("provider_order_id", sa.Text, nullable=False),
    sa.Column("customer_id", UUID), sa.Column("placed_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("financial_state", sa.Text, nullable=False), sa.Column("fulfilment_state", sa.Text, nullable=False),
    sa.Column("total_minor", sa.BigInteger), sa.Column("currency", sa.String(3)),
    sa.Column("provenance", JSONB, nullable=False), parent=("customer_id", "customers"), unique=("provider_order_id",))
order_lines = domain_table("order_lines", sa.Column("order_id", UUID, nullable=False),
    sa.Column("provider_line_id", sa.Text, nullable=False), sa.Column("variant_id", UUID),
    sa.Column("quantity", sa.Integer, nullable=False), sa.Column("refunded_quantity", sa.Integer, nullable=False),
    sa.Column("delivery_at", sa.DateTime(timezone=True)), sa.Column("return_state", sa.String(30), nullable=False),
    sa.Column("coverage_complete", sa.Boolean, nullable=False), sa.Column("provenance", JSONB, nullable=False),
    parent=("order_id", "commerce_orders"), unique=("order_id", "provider_line_id"))
sa.ForeignKeyConstraint([order_lines.c.merchant_id, order_lines.c.workspace_id, order_lines.c.variant_id],
                       [variants.c.merchant_id, variants.c.workspace_id, variants.c.id])
policies = domain_table("policies", sa.Column("revision", sa.Integer, nullable=False),
    sa.Column("config_json", JSONB, nullable=False), sa.Column("digest", sa.String(64), nullable=False),
    sa.Column("creator_id", UUID, sa.ForeignKey("users.id"), nullable=False), unique=("revision",))
opportunities = domain_table("opportunities", sa.Column("customer_id", UUID, nullable=False),
    sa.Column("variant_id", UUID, nullable=False), sa.Column("policy_id", UUID, nullable=False),
    sa.Column("facts_version", sa.Integer, nullable=False), sa.Column("eligible", sa.Boolean, nullable=False),
    sa.Column("exclusion_codes", JSONB, nullable=False), sa.Column("evidence_json", JSONB, nullable=False),
    sa.Column("window_start", sa.DateTime(timezone=True)), sa.Column("window_end", sa.DateTime(timezone=True)),
    sa.Column("basis", sa.Text, nullable=False), parent=("customer_id", "customers"))
for field, target in (("variant_id", variants), ("policy_id", policies)):
    sa.ForeignKeyConstraint([opportunities.c.merchant_id, opportunities.c.workspace_id, opportunities.c[field]],
                           [target.c.merchant_id, target.c.workspace_id, target.c.id])
plan_revisions = domain_table("plan_revisions", sa.Column("revision", sa.Integer, nullable=False),
    sa.Column("policy_id", UUID, nullable=False), sa.Column("facts_version", sa.Integer, nullable=False),
    sa.Column("scope_json", JSONB, nullable=False), sa.Column("digest", sa.String(64), nullable=False),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    parent=("policy_id", "policies"), unique=("revision",))
plan_members = domain_table("plan_members", sa.Column("plan_revision_id", UUID, nullable=False),
    sa.Column("opportunity_id", UUID, nullable=False), sa.Column("selected", sa.Boolean, nullable=False),
    parent=("plan_revision_id", "plan_revisions"), unique=("plan_revision_id", "opportunity_id"))
sa.ForeignKeyConstraint([plan_members.c.merchant_id, plan_members.c.workspace_id, plan_members.c.opportunity_id],
                       [opportunities.c.merchant_id, opportunities.c.workspace_id, opportunities.c.id])

agents = domain_table("agents", sa.Column("version",sa.Integer,nullable=False),
    sa.Column("paused",sa.Boolean,nullable=False),sa.Column("dispatch_epoch",sa.Integer,nullable=False),
    unique=())
sa.UniqueConstraint(agents.c.merchant_id,agents.c.workspace_id)
approvals = domain_table("approvals",sa.Column("resource_type",sa.String(20),nullable=False),
    sa.Column("resource_id",UUID,nullable=False),sa.Column("digest",sa.String(64),nullable=False),
    sa.Column("decision",sa.String(12),nullable=False),sa.Column("actor_id",UUID,sa.ForeignKey("users.id"),nullable=False),
    unique=("resource_type","resource_id"))
cohort_assignments = domain_table("cohort_assignments",sa.Column("plan_revision_id",UUID,nullable=False),
    sa.Column("customer_id",UUID,nullable=False),sa.Column("variant_id",UUID,nullable=False),
    parent=("plan_revision_id","plan_revisions"),unique=("plan_revision_id","customer_id","variant_id"))
journeys = domain_table("journeys",sa.Column("plan_revision_id",UUID,nullable=False),
    sa.Column("customer_id",UUID,nullable=False),sa.Column("variant_id",UUID,nullable=False),
    sa.Column("state",sa.String(30),nullable=False),sa.Column("owner_id",UUID,sa.ForeignKey("users.id")),
    parent=("plan_revision_id","plan_revisions"),unique=("plan_revision_id","customer_id","variant_id"))
proposed_actions = domain_table("proposed_actions",sa.Column("journey_id",UUID,nullable=False),
    sa.Column("policy_id",UUID,nullable=False),sa.Column("payload",JSONB,nullable=False),
    sa.Column("digest",sa.String(64),nullable=False),sa.Column("state",sa.String(30),nullable=False),
    sa.Column("due_at",sa.DateTime(timezone=True),nullable=False),sa.Column("expires_at",sa.DateTime(timezone=True),nullable=False),
    parent=("journey_id","journeys"))
jobs = domain_table("jobs",sa.Column("action_id",UUID,nullable=False),sa.Column("due_at",sa.DateTime(timezone=True),nullable=False),
    sa.Column("state",sa.String(30),nullable=False),sa.Column("lease_token",UUID),sa.Column("lease_until",sa.DateTime(timezone=True)),
    sa.Column("attempts",sa.Integer,nullable=False),sa.Column("blocked_reason",sa.Text),
    parent=("action_id","proposed_actions"),unique=("action_id",))
contact_guards = domain_table("contact_guards",sa.Column("customer_id",UUID,nullable=False),
    sa.Column("inflight_action_id",UUID),parent=("customer_id","customers"),unique=("customer_id",))
budget_buckets = domain_table("budget_buckets",sa.Column("policy_id",UUID,nullable=False),
    sa.Column("cap_minor",sa.BigInteger,nullable=False),sa.Column("reserved_minor",sa.BigInteger,nullable=False),
    sa.Column("spent_minor",sa.BigInteger,nullable=False),parent=("policy_id","policies"),unique=("policy_id",))
sa.CheckConstraint(budget_buckets.c.reserved_minor>=0,name="reserved_nonnegative")
sa.CheckConstraint(budget_buckets.c.spent_minor>=0,name="spent_nonnegative")
sa.CheckConstraint(budget_buckets.c.reserved_minor+budget_buckets.c.spent_minor<=budget_buckets.c.cap_minor,name="within_cap")
reservations = domain_table("reservations",sa.Column("action_id",UUID,nullable=False),sa.Column("bucket_id",UUID,nullable=False),
    sa.Column("amount_minor",sa.BigInteger,nullable=False),sa.Column("state",sa.String(20),nullable=False),
    parent=("action_id","proposed_actions"),unique=("action_id",))
contact_ledger = domain_table("contact_ledger",sa.Column("customer_id",UUID,nullable=False),sa.Column("action_id",UUID,nullable=False),
    sa.Column("channel",sa.String(30),nullable=False),sa.Column("state",sa.String(30),nullable=False),
    parent=("action_id","proposed_actions"),unique=("action_id",))
dispatch_attempts = domain_table("dispatch_attempts",sa.Column("action_id",UUID,nullable=False),
    sa.Column("lease_token",UUID,nullable=False),sa.Column("epoch",sa.Integer,nullable=False),
    sa.Column("state",sa.String(30),nullable=False),parent=("action_id","proposed_actions"),unique=("action_id",))
action_receipts = domain_table("action_receipts",sa.Column("attempt_id",UUID,nullable=False),
    sa.Column("status",sa.String(30),nullable=False),sa.Column("provider_ref",sa.Text),sa.Column("source_mode",sa.String(16),nullable=False),
    parent=("attempt_id","dispatch_attempts"),unique=("attempt_id","status"))
demo_transport = domain_table("demo_transport",sa.Column("attempt_id",UUID,nullable=False),sa.Column("status",sa.String(30),nullable=False),
    sa.Column("provider_ref",sa.Text),parent=("attempt_id","dispatch_attempts"),unique=("attempt_id",))
support_cases = domain_table("support_cases",sa.Column("journey_id",UUID,nullable=False),sa.Column("state",sa.String(30),nullable=False),
    sa.Column("owner_id",UUID,sa.ForeignKey("users.id")),parent=("journey_id","journeys"),unique=("journey_id",))
reminders = domain_table("reminders",sa.Column("journey_id",UUID,nullable=False),sa.Column("event_key",UUID,nullable=False),
    sa.Column("due_at",sa.DateTime(timezone=True),nullable=False),sa.Column("timezone",sa.String(64),nullable=False),
    sa.Column("channel",sa.String(30),nullable=False),sa.Column("state",sa.String(30),nullable=False),
    parent=("journey_id","journeys"),unique=("event_key",))
event_inbox = domain_table("event_inbox",sa.Column("event_key",UUID,nullable=False),sa.Column("payload_hash",sa.String(64),nullable=False),
    sa.Column("kind",sa.String(30),nullable=False),sa.Column("journey_id",UUID,nullable=False),
    parent=("journey_id","journeys"),unique=("event_key",))
event_outbox = domain_table("event_outbox",sa.Column("event_type",sa.String(40),nullable=False),
    sa.Column("subject_id",UUID,nullable=False),sa.Column("details",JSONB,nullable=False))
event_consumptions = domain_table("event_consumptions",sa.Column("event_id",UUID,nullable=False),
    sa.Column("consumer",sa.String(40),nullable=False),parent=("event_id","event_outbox"),unique=("event_id","consumer"))

for table,field,parent_table in ((cohort_assignments,"customer_id",customers),(cohort_assignments,"variant_id",variants),
    (journeys,"customer_id",customers),(journeys,"variant_id",variants),(proposed_actions,"policy_id",policies),
    (reservations,"bucket_id",budget_buckets),(contact_ledger,"customer_id",customers),(contact_guards,"inflight_action_id",proposed_actions)):
    sa.ForeignKeyConstraint([table.c.merchant_id,table.c.workspace_id,table.c[field]],
                           [parent_table.c.merchant_id,parent_table.c.workspace_id,parent_table.c.id])
sa.Index("ix_jobs_due",jobs.c.state,jobs.c.due_at)

checkout_preparations = domain_table("checkout_preparations",sa.Column("journey_id",UUID,nullable=False),
    sa.Column("terms_json",JSONB,nullable=False),sa.Column("digest",sa.String(64),nullable=False),
    sa.Column("checkout_url",sa.Text,nullable=False),sa.Column("expires_at",sa.DateTime(timezone=True),nullable=False),
    sa.Column("state",sa.String(30),nullable=False),sa.Column("link_action_id",UUID),
    parent=("journey_id","journeys"))
payments = domain_table("payments",sa.Column("provider_payment_id",sa.Text,nullable=False),
    sa.Column("provider_order_id",sa.Text),sa.Column("account_ref",sa.Text,nullable=False),
    sa.Column("source_mode",sa.String(16),nullable=False),sa.Column("status",sa.String(30),nullable=False),
    sa.Column("captured",sa.Boolean,nullable=False),sa.Column("amount_minor",sa.BigInteger,nullable=False),
    sa.Column("refunded_minor",sa.BigInteger,nullable=False),sa.Column("currency",sa.String(3),nullable=False),
    sa.Column("order_receipt",sa.Text),sa.Column("provider_order_paid",sa.Boolean,nullable=False),
    sa.Column("observed_at",sa.DateTime(timezone=True),nullable=False),unique=("account_ref","provider_payment_id"))
commerce_transactions = domain_table("commerce_transactions",sa.Column("order_id",UUID,nullable=False),
    sa.Column("provider_transaction_id",sa.Text,nullable=False),sa.Column("payment_ref",sa.Text),
    sa.Column("gateway",sa.Text,nullable=False),sa.Column("kind",sa.String(30),nullable=False),
    sa.Column("status",sa.String(30),nullable=False),sa.Column("test",sa.Boolean,nullable=False),
    sa.Column("amount_minor",sa.BigInteger,nullable=False),sa.Column("currency",sa.String(3),nullable=False),
    sa.Column("mapping_version",sa.String(70),nullable=False),sa.Column("preparation_id",UUID),
    parent=("order_id","commerce_orders"),unique=("provider_transaction_id",))
payment_order_matches = domain_table("payment_order_matches",sa.Column("payment_id",UUID,nullable=False),
    sa.Column("order_id",UUID,nullable=False),sa.Column("transaction_id",UUID,nullable=False),
    sa.Column("mapping_version",sa.String(70),nullable=False),sa.Column("evidence",JSONB,nullable=False),
    parent=("payment_id","payments"),unique=("payment_id",))
sa.UniqueConstraint(payment_order_matches.c.merchant_id,payment_order_matches.c.workspace_id,payment_order_matches.c.order_id)
confirmed_purchases = domain_table("confirmed_purchases",sa.Column("order_id",UUID,nullable=False),
    sa.Column("match_id",UUID,nullable=False),sa.Column("source_mode",sa.String(16),nullable=False),
    sa.Column("total_minor",sa.BigInteger,nullable=False),sa.Column("currency",sa.String(3),nullable=False),
    parent=("order_id","commerce_orders"),unique=("order_id",))
reconciliation_cases = domain_table("reconciliation_cases",sa.Column("subject_ref",sa.Text,nullable=False),
    sa.Column("reason",sa.String(60),nullable=False),sa.Column("state",sa.String(30),nullable=False),
    sa.Column("owner_id",UUID,sa.ForeignKey("users.id"),nullable=False),unique=("subject_ref","reason"))
commerce_adjustments = domain_table("commerce_adjustments",sa.Column("provider_ref",sa.Text,nullable=False),
    sa.Column("order_id",UUID),sa.Column("payment_id",UUID),sa.Column("kind",sa.String(30),nullable=False),
    sa.Column("amount_minor",sa.BigInteger),sa.Column("currency",sa.String(3)),sa.Column("evidence",JSONB,nullable=False),
    unique=("provider_ref",))
approved_offers = domain_table("approved_offers",sa.Column("provider_ref",sa.String(80),nullable=False),
    sa.Column("variant_id",UUID,nullable=False),sa.Column("discount_minor",sa.BigInteger,nullable=False),
    sa.Column("expires_at",sa.DateTime(timezone=True),nullable=False),sa.Column("evidence",JSONB,nullable=False),
    parent=("variant_id","variants"),unique=("provider_ref",))
offer_policies = domain_table("offer_policies",sa.Column("revision",sa.Integer,nullable=False),
    sa.Column("config_json",JSONB,nullable=False),sa.Column("digest",sa.String(64),nullable=False),
    unique=("revision",))
provider_notifications = domain_table("provider_notifications",sa.Column("connector_id",UUID,nullable=False),
    sa.Column("event_key",sa.String(160),nullable=False),sa.Column("payload_hash",sa.String(64),nullable=False),
    sa.Column("event_type",sa.String(100),nullable=False),sa.Column("state",sa.String(30),nullable=False),
    parent=("connector_id","connectors"),unique=("connector_id","event_key"))
for table,field,parent_table in ((checkout_preparations,"link_action_id",proposed_actions),
    (commerce_transactions,"preparation_id",checkout_preparations),(payment_order_matches,"order_id",commerce_orders),
    (payment_order_matches,"transaction_id",commerce_transactions),(confirmed_purchases,"match_id",payment_order_matches),
    (commerce_adjustments,"order_id",commerce_orders),(commerce_adjustments,"payment_id",payments)):
    sa.ForeignKeyConstraint([table.c.merchant_id,table.c.workspace_id,table.c[field]],
                           [parent_table.c.merchant_id,parent_table.c.workspace_id,parent_table.c.id])

# Stage 06 account-bound identities and callback evidence.
whatsapp_identities = domain_table('whatsapp_identities',sa.Column('connector_id',UUID,nullable=False),sa.Column('customer_id',UUID,nullable=False),sa.Column('address',sa.String(80),nullable=False),sa.Column('source_mode',sa.String(16),nullable=False),sa.Column('verification_ref',sa.String(160),nullable=False),parent=('customer_id','customers'),unique=('connector_id','address'))
whatsapp_identities.append_constraint(sa.ForeignKeyConstraint(['merchant_id','workspace_id','connector_id'],['connectors.merchant_id','connectors.workspace_id','connectors.id']))
whatsapp_deliveries = domain_table('whatsapp_deliveries',sa.Column('receipt_id',UUID,nullable=False),sa.Column('connector_id',UUID,nullable=False),sa.Column('provider_ref',sa.String(80),nullable=False),sa.Column('status',sa.String(30),nullable=False),sa.Column('source_mode',sa.String(16),nullable=False),sa.Column('error_code',sa.String(30)),parent=('receipt_id','action_receipts'),unique=('receipt_id',))
whatsapp_deliveries.append_constraint(sa.ForeignKeyConstraint(['merchant_id','workspace_id','connector_id'],['connectors.merchant_id','connectors.workspace_id','connectors.id']))
whatsapp_deliveries.append_constraint(sa.UniqueConstraint('merchant_id','workspace_id','connector_id','provider_ref'))
whatsapp_events = domain_table('whatsapp_events',sa.Column('connector_id',UUID,nullable=False),sa.Column('event_key',sa.String(200),nullable=False),sa.Column('payload_hash',sa.String(64),nullable=False),sa.Column('kind',sa.String(30),nullable=False),sa.Column('customer_id',UUID),sa.Column('message_ref',sa.String(80),nullable=False),sa.Column('text',sa.Text),sa.Column('classification',sa.String(30),nullable=False),sa.Column('source_mode',sa.String(16),nullable=False),sa.Column('state',sa.String(40),nullable=False),parent=('connector_id','connectors'),unique=('connector_id','event_key'))
whatsapp_events.append_constraint(sa.ForeignKeyConstraint(['merchant_id','workspace_id','customer_id'],['customers.merchant_id','customers.workspace_id','customers.id']))

# Stage 07: consented operator browser tests and immutable interpreted turns.
voice_sessions = domain_table('voice_sessions',sa.Column('journey_id',UUID,nullable=False),sa.Column('actor_id',UUID,sa.ForeignKey('users.id'),nullable=False),sa.Column('provider',sa.String(20),nullable=False),sa.Column('consent',JSONB,nullable=False),sa.Column('state',sa.String(30),nullable=False),sa.Column('version',sa.Integer,nullable=False),sa.Column('last_sequence',sa.Integer,nullable=False),sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),parent=('journey_id','journeys'))
intelligence_turns = domain_table('intelligence_turns',sa.Column('session_id',UUID,nullable=False),sa.Column('sequence',sa.Integer,nullable=False),sa.Column('input_hash',sa.String(64),nullable=False),sa.Column('input_kind',sa.String(20),nullable=False),sa.Column('transcript',sa.Text),sa.Column('state',sa.String(40),nullable=False),sa.Column('proposal',JSONB),sa.Column('reply',sa.Text),sa.Column('facts',JSONB,nullable=False),sa.Column('receipt',JSONB,nullable=False),sa.Column('error_code',sa.String(60)),sa.Column('confirmed_action',sa.String(40)),parent=('session_id','voice_sessions'),unique=('session_id','sequence'))
intelligence_turns.append_constraint(sa.CheckConstraint('sequence BETWEEN 1 AND 20',name='sequence'))

# Stage 08: immutable accounting reviews and policy suggestions.
accounting_reviews = domain_table('accounting_reviews',sa.Column('purchase_id',UUID,nullable=False),sa.Column('revision',sa.Integer,nullable=False),sa.Column('costs',JSONB,nullable=False),sa.Column('returns_mature',sa.Boolean,nullable=False),sa.Column('actor_id',UUID,sa.ForeignKey('users.id'),nullable=False),sa.Column('source_mode',sa.String(16),nullable=False),parent=('purchase_id','confirmed_purchases'),unique=('purchase_id','revision'))
learning_records = domain_table('learning_records',sa.Column('customer_id',UUID,nullable=False),sa.Column('variant_id',UUID,nullable=False),sa.Column('turn_id',UUID,nullable=False),sa.Column('kind',sa.String(40),nullable=False),sa.Column('value',JSONB,nullable=False),sa.Column('provenance',JSONB,nullable=False),parent=('customer_id','customers'),unique=('turn_id','kind'))
learning_records.append_constraint(sa.ForeignKeyConstraint(['merchant_id','workspace_id','variant_id'],['variants.merchant_id','variants.workspace_id','variants.id']))
learning_records.append_constraint(sa.ForeignKeyConstraint(['merchant_id','workspace_id','turn_id'],['intelligence_turns.merchant_id','intelligence_turns.workspace_id','intelligence_turns.id']))
policy_suggestions = domain_table('policy_suggestions',sa.Column('policy_id',UUID,nullable=False),sa.Column('kind',sa.String(40),nullable=False),sa.Column('proposed_diff',JSONB,nullable=False),sa.Column('evidence',JSONB,nullable=False),sa.Column('digest',sa.String(64),nullable=False),parent=('policy_id','policies'),unique=('policy_id','kind','digest'))
suggestion_decisions = domain_table('suggestion_decisions',sa.Column('suggestion_id',UUID,nullable=False),sa.Column('decision',sa.String(20),nullable=False),sa.Column('actor_id',UUID,sa.ForeignKey('users.id'),nullable=False),sa.Column('result_policy_id',UUID),parent=('suggestion_id','policy_suggestions'),unique=('suggestion_id',))
suggestion_decisions.append_constraint(sa.ForeignKeyConstraint(['merchant_id','workspace_id','result_policy_id'],['policies.merchant_id','policies.workspace_id','policies.id']))
