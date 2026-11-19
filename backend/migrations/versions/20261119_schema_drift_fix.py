"""Add columns that exist on the models but were never migrated.

Tests build tables with ``Base.metadata.create_all`` so this drift went unnoticed;
a database built only from migrations lacked these columns and queries against
``agent_runs``/``messages``/``documents`` etc. failed at runtime.

Revision ID: schema_drift_fix
Revises: utcp_integration
Create Date: 2026-11-19

"""
from __future__ import annotations

from alembic import op

# revision identifiers
revision = "schema_drift_fix"
down_revision = "utcp_integration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # api_keys.updated_at
    op.execute(
        "ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS updated_at "
        "TIMESTAMPTZ NOT NULL DEFAULT now()"
    )

    # agent_trace_events.created_at / updated_at
    op.execute(
        "ALTER TABLE agent_trace_events ADD COLUMN IF NOT EXISTS created_at "
        "TIMESTAMPTZ NOT NULL DEFAULT now()"
    )
    op.execute(
        "ALTER TABLE agent_trace_events ADD COLUMN IF NOT EXISTS updated_at "
        "TIMESTAMPTZ NOT NULL DEFAULT now()"
    )

    # agent_runs.legal_hold
    op.execute(
        "ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS legal_hold "
        "BOOLEAN NOT NULL DEFAULT false"
    )

    # messages.organization_id: add nullable, backfill from the conversation, then enforce.
    op.execute(
        "ALTER TABLE messages ADD COLUMN IF NOT EXISTS organization_id UUID "
        "REFERENCES organizations(id) ON DELETE CASCADE"
    )
    op.execute(
        "UPDATE messages m SET organization_id = c.organization_id "
        "FROM conversations c WHERE m.conversation_id = c.id AND m.organization_id IS NULL"
    )
    op.execute("ALTER TABLE messages ALTER COLUMN organization_id SET NOT NULL")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_messages_organization_id ON messages (organization_id)"
    )

    # tool_calls.audit_id
    op.execute(
        "ALTER TABLE tool_calls ADD COLUMN IF NOT EXISTS audit_id UUID "
        "REFERENCES tool_execution_audits(id) ON DELETE SET NULL"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_tool_calls_audit_id ON tool_calls (audit_id)")

    # documents ACL columns
    op.execute(
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS visibility "
        "VARCHAR(10) NOT NULL DEFAULT 'public'"
    )
    op.execute(
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS allowed_roles "
        "JSONB NOT NULL DEFAULT '[]'::jsonb"
    )
    op.execute(
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS allowed_user_ids "
        "JSONB NOT NULL DEFAULT '[]'::jsonb"
    )

    # document_chunks full-text search vector
    op.execute(
        "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS content_tsvector TSVECTOR "
        "GENERATED ALWAYS AS (to_tsvector('english', content)) STORED"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunks_tsvector ON document_chunks "
        "USING gin (content_tsvector)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_tsvector")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS content_tsvector")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS allowed_user_ids")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS allowed_roles")
    op.execute("ALTER TABLE documents DROP COLUMN IF EXISTS visibility")
    op.execute("DROP INDEX IF EXISTS ix_tool_calls_audit_id")
    op.execute("ALTER TABLE tool_calls DROP COLUMN IF EXISTS audit_id")
    op.execute("DROP INDEX IF EXISTS ix_messages_organization_id")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS organization_id")
    op.execute("ALTER TABLE agent_runs DROP COLUMN IF EXISTS legal_hold")
    op.execute("ALTER TABLE agent_trace_events DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE agent_trace_events DROP COLUMN IF EXISTS created_at")
    op.execute("ALTER TABLE api_keys DROP COLUMN IF EXISTS updated_at")
