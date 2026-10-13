"""Frozen Stage 01 relational foundation."""
import os
from alembic import op
from sqlalchemy.engine import make_url
from sqlalchemy.dialects.postgresql import dialect

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None

UPGRADE_SQL = [
    '\nCREATE TABLE login_limits (\n\tbucket VARCHAR(64) NOT NULL, \n\tattempts INTEGER NOT NULL, \n\twindow_start TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_login_limits PRIMARY KEY (bucket)\n)\n\n',
    '\nCREATE TABLE merchants (\n\tid UUID NOT NULL, \n\tname VARCHAR(120) NOT NULL, \n\tdefault_timezone VARCHAR(64) NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_merchants PRIMARY KEY (id)\n)\n\n',
    '\nCREATE TABLE users (\n\tid UUID NOT NULL, \n\tlogin_identifier VARCHAR(120) NOT NULL, \n\tpassword_digest TEXT NOT NULL, \n\tdisabled_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_users PRIMARY KEY (id), \n\tCONSTRAINT uq_users_login_identifier UNIQUE (login_identifier)\n)\n\n',
    "\nCREATE TABLE memberships (\n\tmerchant_id UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\trole VARCHAR(16) NOT NULL, \n\tCONSTRAINT pk_memberships PRIMARY KEY (merchant_id, user_id), \n\tCONSTRAINT ck_memberships_role CHECK (role IN ('owner','operator','viewer')), \n\tCONSTRAINT fk_memberships_merchant_id_merchants FOREIGN KEY(merchant_id) REFERENCES merchants (id), \n\tCONSTRAINT fk_memberships_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)\n)\n\n",
    '\nCREATE TABLE sessions (\n\tid UUID NOT NULL, \n\tuser_id UUID NOT NULL, \n\ttoken_hash VARCHAR(64) NOT NULL, \n\tcsrf_hash VARCHAR(64) NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevoked_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_sessions PRIMARY KEY (id), \n\tCONSTRAINT fk_sessions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id), \n\tCONSTRAINT uq_sessions_token_hash UNIQUE (token_hash)\n)\n\n',
    "\nCREATE TABLE workspaces (\n\tid UUID NOT NULL, \n\tmerchant_id UUID NOT NULL, \n\tenvironment VARCHAR(16) NOT NULL, \n\tname VARCHAR(120) NOT NULL, \n\tversion INTEGER DEFAULT '1' NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_workspaces PRIMARY KEY (id), \n\tCONSTRAINT uq_workspaces_merchant_id_id UNIQUE (merchant_id, id), \n\tCONSTRAINT uq_workspaces_merchant_id_environment UNIQUE (merchant_id, environment), \n\tCONSTRAINT ck_workspaces_environment CHECK (environment IN ('demo','development','live')), \n\tCONSTRAINT fk_workspaces_merchant_id_merchants FOREIGN KEY(merchant_id) REFERENCES merchants (id)\n)\n\n",
    '\nCREATE TABLE audit_events (\n\tid UUID NOT NULL, \n\tmerchant_id UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tactor_id UUID NOT NULL, \n\tevent_type VARCHAR(80) NOT NULL, \n\ttarget_id UUID NOT NULL, \n\tcorrelation_id UUID NOT NULL, \n\tdetails JSONB NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_audit_events PRIMARY KEY (id), \n\tCONSTRAINT fk_audit_events_merchant_id_workspaces FOREIGN KEY(merchant_id, workspace_id) REFERENCES workspaces (merchant_id, id), \n\tCONSTRAINT uq_audit_events_merchant_id_workspace_id_id UNIQUE (merchant_id, workspace_id, id), \n\tCONSTRAINT fk_audit_events_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)\n)\n\n',
    "\nCREATE TABLE connectors (\n\tid UUID NOT NULL, \n\tmerchant_id UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tprovider VARCHAR(30) NOT NULL, \n\tprovider_account_id VARCHAR(160), \n\tsource_mode VARCHAR(16) NOT NULL, \n\tprovider_environment VARCHAR(30) NOT NULL, \n\tcredential_ref VARCHAR(120), \n\tstate VARCHAR(24) NOT NULL, \n\tlast_checked_at TIMESTAMP WITH TIME ZONE, \n\tversion INTEGER DEFAULT '1' NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_connectors PRIMARY KEY (id), \n\tCONSTRAINT fk_connectors_merchant_id_workspaces FOREIGN KEY(merchant_id, workspace_id) REFERENCES workspaces (merchant_id, id), \n\tCONSTRAINT uq_connectors_merchant_id_workspace_id_id UNIQUE (merchant_id, workspace_id, id), \n\tCONSTRAINT uq_connectors_merchant_id_workspace_id_provider UNIQUE (merchant_id, workspace_id, provider), \n\tCONSTRAINT ck_connectors_source_mode CHECK (source_mode IN ('simulated','test','live'))\n)\n\n",
    '\nCREATE TABLE idempotency_records (\n\tid UUID NOT NULL, \n\tmerchant_id UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tactor_id UUID NOT NULL, \n\toperation VARCHAR(120) NOT NULL, \n\tkey UUID NOT NULL, \n\trequest_hash VARCHAR(64) NOT NULL, \n\tresult_json JSONB, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_idempotency_records PRIMARY KEY (id), \n\tCONSTRAINT fk_idempotency_records_merchant_id_workspaces FOREIGN KEY(merchant_id, workspace_id) REFERENCES workspaces (merchant_id, id), \n\tCONSTRAINT uq_idempotency_records_merchant_id_workspace_id_id UNIQUE (merchant_id, workspace_id, id), \n\tCONSTRAINT uq_idempotency_records_merchant_id_workspace_id_actor_i_6b01 UNIQUE (merchant_id, workspace_id, actor_id, operation, key), \n\tCONSTRAINT fk_idempotency_records_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)\n)\n\n',
    "\nCREATE TABLE connector_capabilities (\n\tid UUID NOT NULL, \n\tmerchant_id UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tconnector_id UUID NOT NULL, \n\tcapability VARCHAR(64) NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tverified_at TIMESTAMP WITH TIME ZONE, \n\tevidence_ref VARCHAR(160), \n\treason VARCHAR(250), \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_connector_capabilities PRIMARY KEY (id), \n\tCONSTRAINT fk_connector_capabilities_merchant_id_workspaces FOREIGN KEY(merchant_id, workspace_id) REFERENCES workspaces (merchant_id, id), \n\tCONSTRAINT uq_connector_capabilities_merchant_id_workspace_id_id UNIQUE (merchant_id, workspace_id, id), \n\tCONSTRAINT fk_connector_capabilities_merchant_id_connectors FOREIGN KEY(merchant_id, workspace_id, connector_id) REFERENCES connectors (merchant_id, workspace_id, id), \n\tCONSTRAINT uq_connector_capabilities_merchant_id_workspace_id_conn_49f6 UNIQUE (merchant_id, workspace_id, connector_id, capability), \n\tCONSTRAINT ck_connector_capabilities_status CHECK (status IN ('unverified','available','blocked','revoked'))\n)\n\n"
]
TABLES = ['login_limits', 'merchants', 'users', 'memberships', 'sessions', 'workspaces', 'audit_events', 'connectors', 'idempotency_records', 'connector_capabilities']

def upgrade():
    for statement in UPGRADE_SQL:
        op.execute(statement)
    url = os.getenv("APP_DATABASE_URL")
    if url:
        role = dialect().identifier_preparer.quote(make_url(url).username)
        mutable = [t for t in TABLES if t != "audit_events"]
        op.execute("GRANT USAGE ON SCHEMA public TO " + role)
        op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON " + ", ".join(mutable) + " TO " + role)
        op.execute("GRANT SELECT, INSERT ON audit_events TO " + role)
        op.execute("GRANT SELECT ON alembic_version TO " + role)


def downgrade():
    for name in reversed(TABLES):
        op.drop_table(name)
