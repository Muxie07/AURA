"""Initial schema — all Phase 1 tables.

Revision ID: 001
Revises:
Create Date: 2026-09-13 00:00:00.000000
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass

    # ==========================================================================
    # ORGANIZATIONS
    # ==========================================================================
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])
    op.create_index("ix_organizations_is_active", "organizations", ["is_active"])

    # ==========================================================================
    # USERS
    # ==========================================================================
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("full_name", sa.String(500), nullable=False),
        sa.Column("hashed_password", sa.String(128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_users_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("organization_id", "email", name="uq_users_org_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_index("ix_users_is_active", "users", ["is_active"])

    # ==========================================================================
    # CONVERSATIONS
    # ==========================================================================
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "completed", "archived", "failed", name="conversation_status_enum"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_conversations"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_conversations_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_conversations_user_id_users",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_conversations_organization_id", "conversations", ["organization_id"])
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index("ix_conversations_status", "conversations", ["status"])
    op.create_index("ix_conversations_created_at", "conversations", ["created_at"])

    # ==========================================================================
    # AGENT RUNS (before messages — messages FK to agent_runs)
    # ==========================================================================
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "completed",
                "failed",
                "timed_out",
                "awaiting_approval",
                "cancelled",
                name="agent_run_status_enum",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_request", sa.Text(), nullable=False),
        sa.Column("intent_analysis", postgresql.JSONB(), nullable=True),
        sa.Column("plan", postgresql.JSONB(), nullable=True),
        sa.Column("final_response", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("iteration_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens_input", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_tokens_output", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("model_provider", sa.String(50), nullable=True),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agent_runs"),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_agent_runs_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_agent_runs_user_id_users",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_agent_runs_conversation_id", "agent_runs", ["conversation_id"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])
    op.create_index("ix_agent_runs_user_id", "agent_runs", ["user_id"])
    op.create_index("ix_agent_runs_created_at", "agent_runs", ["created_at"])

    # ==========================================================================
    # APPROVAL REQUESTS (before tool_calls — tool_calls FK to approval_requests)
    # ==========================================================================
    op.create_table(
        "approval_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("action_summary", sa.Text(), nullable=False),
        sa.Column("action_details", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "status",
            sa.Enum("pending", "approved", "denied", "expired", name="approval_status_enum"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("actioned_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("denial_reason", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_approval_requests"),
        sa.ForeignKeyConstraint(
            ["agent_run_id"],
            ["agent_runs.id"],
            name="fk_approval_requests_agent_run_id_agent_runs",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_approval_requests_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actioned_by_id"],
            ["users.id"],
            name="fk_approval_requests_actioned_by_id_users",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_approval_requests_agent_run_id", "approval_requests", ["agent_run_id"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])
    op.create_index(
        "ix_approval_requests_organization_id", "approval_requests", ["organization_id"]
    )

    # ==========================================================================
    # MESSAGES
    # ==========================================================================
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role",
            sa.Enum("user", "assistant", "system", "tool", name="message_role_enum"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("structured_content", postgresql.JSONB(), nullable=True),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_messages"),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_messages_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["agent_run_id"],
            ["agent_runs.id"],
            name="fk_messages_agent_run_id_agent_runs",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_role", "messages", ["role"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])

    # ==========================================================================
    # TOOL CALLS
    # ==========================================================================
    op.create_table(
        "tool_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("tool_version", sa.String(20), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "success",
                "failed",
                "skipped",
                "awaiting_approval",
                name="tool_call_status_enum",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("iteration", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("input_args", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("output", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("approval_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tool_calls"),
        sa.ForeignKeyConstraint(
            ["agent_run_id"],
            ["agent_runs.id"],
            name="fk_tool_calls_agent_run_id_agent_runs",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["approval_id"],
            ["approval_requests.id"],
            name="fk_tool_calls_approval_id_approval_requests",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_tool_calls_agent_run_id", "tool_calls", ["agent_run_id"])
    op.create_index("ix_tool_calls_tool_name", "tool_calls", ["tool_name"])
    op.create_index("ix_tool_calls_status", "tool_calls", ["status"])

    # ==========================================================================
    # AUDIT EVENTS
    # ==========================================================================
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "event_type",
            sa.Enum(
                "user.login",
                "user.logout",
                "user.created",
                "conversation.created",
                "conversation.completed",
                "agent.run_started",
                "agent.run_completed",
                "agent.run_failed",
                "tool.executed",
                "tool.failed",
                "approval.requested",
                "approval.granted",
                "approval.denied",
                "document.ingested",
                name="audit_event_type_enum",
            ),
            nullable=False,
        ),
        sa.Column("event_data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_audit_events_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_audit_events_user_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["agent_run_id"],
            ["agent_runs.id"],
            name="fk_audit_events_agent_run_id_agent_runs",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_audit_events_organization_id", "audit_events", ["organization_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"])
    op.create_index("ix_audit_events_agent_run_id", "audit_events", ["agent_run_id"])
    op.create_index("ix_audit_events_request_id", "audit_events", ["request_id"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])

    # ==========================================================================
    # SEED: Default organization and user (for Phase 1 development)
    # ==========================================================================
    op.execute("""
        INSERT INTO organizations (id, name, slug, is_active, settings, created_at, updated_at)
        VALUES (
            '00000000-0000-0000-0000-000000000001',
            'AURA Demo Organization',
            'aura-demo',
            true,
            '{}',
            now(),
            now()
        )
        ON CONFLICT DO NOTHING;
    """)

    op.execute("""
        INSERT INTO users (id, organization_id, email, full_name, is_active, is_superuser, metadata, created_at, updated_at)
        VALUES (
            '00000000-0000-0000-0000-000000000002',
            '00000000-0000-0000-0000-000000000001',
            'demo@aura.example.com',
            'AURA Demo User',
            true,
            true,
            '{}',
            now(),
            now()
        )
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    # Drop in reverse order of creation
    op.drop_table("audit_events")
    op.drop_table("tool_calls")
    op.drop_table("messages")
    op.drop_table("approval_requests")
    op.drop_table("agent_runs")
    op.drop_table("conversations")
    op.drop_table("users")
    op.drop_table("organizations")

    # Drop enum types
    for enum_name in [
        "approval_status_enum",
        "audit_event_type_enum",
        "tool_call_status_enum",
        "agent_run_status_enum",
        "message_role_enum",
        "conversation_status_enum",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
