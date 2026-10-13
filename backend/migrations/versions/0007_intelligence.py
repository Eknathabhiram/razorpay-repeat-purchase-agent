"""Frozen browser test consent and interpretation records."""
import os
from alembic import op
from sqlalchemy.engine import make_url
from sqlalchemy.dialects.postgresql import dialect
revision="0007_intelligence"
down_revision="0006_whatsapp"
branch_labels=None
depends_on=None
DDL=['\nCREATE TABLE voice_sessions (\n\tid UUID NOT NULL, \n\tmerchant_id UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tjourney_id UUID NOT NULL, \n\tactor_id UUID NOT NULL, \n\tprovider VARCHAR(20) NOT NULL, \n\tconsent JSONB NOT NULL, \n\tstate VARCHAR(30) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tlast_sequence INTEGER NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_voice_sessions PRIMARY KEY (id), \n\tCONSTRAINT fk_voice_sessions_merchant_id_workspaces FOREIGN KEY(merchant_id, workspace_id) REFERENCES workspaces (merchant_id, id), \n\tCONSTRAINT uq_voice_sessions_merchant_id_workspace_id_id UNIQUE (merchant_id, workspace_id, id), \n\tCONSTRAINT fk_voice_sessions_merchant_id_journeys FOREIGN KEY(merchant_id, workspace_id, journey_id) REFERENCES journeys (merchant_id, workspace_id, id), \n\tCONSTRAINT fk_voice_sessions_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)\n)\n\n', '\nCREATE TABLE intelligence_turns (\n\tid UUID NOT NULL, \n\tmerchant_id UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tsession_id UUID NOT NULL, \n\tsequence INTEGER NOT NULL, \n\tinput_hash VARCHAR(64) NOT NULL, \n\tinput_kind VARCHAR(20) NOT NULL, \n\ttranscript TEXT, \n\tstate VARCHAR(40) NOT NULL, \n\tproposal JSONB, \n\treply TEXT, \n\tfacts JSONB NOT NULL, \n\treceipt JSONB NOT NULL, \n\terror_code VARCHAR(60), \n\tconfirmed_action VARCHAR(40), \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tCONSTRAINT pk_intelligence_turns PRIMARY KEY (id), \n\tCONSTRAINT fk_intelligence_turns_merchant_id_workspaces FOREIGN KEY(merchant_id, workspace_id) REFERENCES workspaces (merchant_id, id), \n\tCONSTRAINT uq_intelligence_turns_merchant_id_workspace_id_id UNIQUE (merchant_id, workspace_id, id), \n\tCONSTRAINT fk_intelligence_turns_merchant_id_voice_sessions FOREIGN KEY(merchant_id, workspace_id, session_id) REFERENCES voice_sessions (merchant_id, workspace_id, id), \n\tCONSTRAINT uq_intelligence_turns_merchant_id_workspace_id_session__6482 UNIQUE (merchant_id, workspace_id, session_id, sequence), \n\tCONSTRAINT ck_intelligence_turns_sequence CHECK (sequence BETWEEN 1 AND 20)\n)\n\n']
TABLES=['voice_sessions', 'intelligence_turns']
def upgrade():
    for statement in DDL: op.execute(statement)
    url=os.getenv("APP_DATABASE_URL")
    if url:
        role=dialect().identifier_preparer.quote(make_url(url).username)
        for name in TABLES: op.execute("GRANT SELECT,INSERT,UPDATE ON "+name+" TO "+role)
def downgrade():
    for name in reversed(TABLES): op.drop_table(name)
