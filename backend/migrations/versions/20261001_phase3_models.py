"""Phase 3: Data model hardening.

Incremental migration: only adds new structures on top of the existing schema.

- New tables: quotation_items, llm_usage, refresh_tokens, outbox_events
- New columns on existing tables (customers.code, products.currency, 
  quotations.code/total_numeric/currency/version/valid_until/created_by/
  approved_by/approval_id, approval_requests.args_hash/requested_by_id/
  tool_call_id + make expires_at NOT NULL, agent_runs.organization_id,
  tool_execution_audits.args_hash/request_id/approval_id)
- New indexes and unique constraints

Revision ID: phase3_models
Revises: phase2_auth
Create Date: 2026-10-01

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "phase3_models"
down_revision = "phase2_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. customers: add `code` column + unique constraint
    # ------------------------------------------------------------------
    op.add_column("customers", sa.Column("code", sa.String(50), nullable=True))
    # Backfill code from existing id values (they were string PKs before)
    op.execute("UPDATE customers SET code = id WHERE code IS NULL")
    op.alter_column("customers", "code", nullable=False)
    op.create_unique_constraint("uq_customer_org_code", "customers", ["organization_id", "code"])

    # ------------------------------------------------------------------
    # 2. products: add currency, fix base_price to numeric
    # ------------------------------------------------------------------
    op.add_column("products", sa.Column("currency", sa.String(3), nullable=True, server_default="USD"))
    op.execute("UPDATE products SET currency = 'USD' WHERE currency IS NULL")
    op.alter_column("products", "currency", nullable=False)
    op.execute("ALTER TABLE products ALTER COLUMN base_price TYPE NUMERIC(14,2) USING base_price::NUMERIC(14,2)")
    op.create_unique_constraint("uq_product_org_sku", "products", ["organization_id", "sku"])

    # ------------------------------------------------------------------
    # 3. quotations: add new columns, migrate total to numeric
    # ------------------------------------------------------------------
    op.add_column("quotations", sa.Column("code", sa.String(50), nullable=True))
    op.execute("UPDATE quotations SET code = id WHERE code IS NULL")
    op.alter_column("quotations", "code", nullable=False)

    op.add_column("quotations", sa.Column("total_numeric", sa.Numeric(14, 2), nullable=True))
    op.execute("UPDATE quotations SET total_numeric = CASE WHEN total ~ '^[0-9]+(\\.[0-9]+)?$' THEN total::NUMERIC ELSE 0 END")

    op.add_column("quotations", sa.Column("currency", sa.String(3), nullable=True, server_default="USD"))
    op.execute("UPDATE quotations SET currency = 'USD' WHERE currency IS NULL")
    op.alter_column("quotations", "currency", nullable=False)

    op.add_column("quotations", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("quotations", sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("quotations", sa.Column("created_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("quotations", sa.Column("approved_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("quotations", sa.Column("approval_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))

    op.create_unique_constraint("uq_quotation_org_code", "quotations", ["organization_id", "code"])
    op.create_index(
        "ix_quotation_idempotency",
        "quotations",
        ["organization_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.create_index("ix_quotations_code", "quotations", ["code"])

    # Add FK constraints for new UUID columns on quotations
    op.create_foreign_key("fk_quotations_created_by_users", "quotations", "users", ["created_by"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_quotations_approved_by_users", "quotations", "users", ["approved_by"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_quotations_approval_id", "quotations", "approval_requests", ["approval_id"], ["id"], ondelete="SET NULL")

    # ------------------------------------------------------------------
    # 4. quotation_items (new table)
    # ------------------------------------------------------------------
    op.create_table(
        "quotation_items",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("quotation_id", sa.String(50), nullable=False),
        sa.Column("product_id", sa.String(50), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("discount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("tax", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quotation_items_quotation_id", "quotation_items", ["quotation_id"])

    # ------------------------------------------------------------------
    # 5. approval_requests: add args_hash, requested_by_id, tool_call_id;
    #    make expires_at NOT NULL (backfill first)
    # ------------------------------------------------------------------
    op.add_column("approval_requests", sa.Column("args_hash", sa.String(64), nullable=True))
    op.execute("UPDATE approval_requests SET args_hash = 'legacy' WHERE args_hash IS NULL")
    op.alter_column("approval_requests", "args_hash", nullable=False)

    op.add_column("approval_requests", sa.Column("requested_by_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("approval_requests", sa.Column("tool_call_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_approval_requested_by", "approval_requests", "users", ["requested_by_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_approval_tool_call", "approval_requests", "tool_calls", ["tool_call_id"], ["id"], ondelete="SET NULL")

    # Backfill expires_at with a 24h default so we can make NOT NULL
    op.execute("UPDATE approval_requests SET expires_at = created_at + interval '24 hours' WHERE expires_at IS NULL")
    op.alter_column("approval_requests", "expires_at", existing_type=sa.DateTime(), nullable=False)

    # Make actioned_at timezone-aware
    op.execute("ALTER TABLE approval_requests ALTER COLUMN actioned_at TYPE TIMESTAMP WITH TIME ZONE USING actioned_at AT TIME ZONE 'UTC'")

    op.create_index("ix_approval_org_status", "approval_requests", ["organization_id", "status"])
    op.create_index(
        "ix_approval_pending",
        "approval_requests",
        ["organization_id", "status"],
        postgresql_where=sa.text("status = 'pending'"),
    )

    # ------------------------------------------------------------------
    # 6. agent_runs: add organization_id
    # ------------------------------------------------------------------
    op.add_column("agent_runs", sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    # Backfill from conversations join
    op.execute("""
        UPDATE agent_runs ar
        SET organization_id = c.organization_id
        FROM conversations c
        WHERE ar.conversation_id = c.id
    """)
    op.alter_column("agent_runs", "organization_id", nullable=False)
    op.create_index("ix_agent_runs_organization_id", "agent_runs", ["organization_id"])
    op.create_index("ix_agent_run_org_created", "agent_runs", ["organization_id", "created_at"])
    op.create_foreign_key("fk_agent_runs_organization_id", "agent_runs", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")

    # ------------------------------------------------------------------
    # 7. tool_execution_audits: add args_hash, request_id, approval_id
    # ------------------------------------------------------------------
    op.add_column("tool_execution_audits", sa.Column("args_hash", sa.String(64), nullable=True))
    op.add_column("tool_execution_audits", sa.Column("request_id", sa.String(64), nullable=True))
    op.add_column("tool_execution_audits", sa.Column("approval_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_tool_exec_request_id", "tool_execution_audits", ["request_id"])
    op.create_index("ix_audit_run_started", "tool_execution_audits", ["agent_run_id", "started_at"])
    op.create_index("ix_audit_org_started", "tool_execution_audits", ["organization_id", "started_at"])
    op.create_index(
        "ix_audit_idempotency",
        "tool_execution_audits",
        ["organization_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    # ------------------------------------------------------------------
    # 8. agent_trace_events: add unique constraint (run_id, sequence)
    # ------------------------------------------------------------------
    op.create_unique_constraint("uq_trace_run_seq", "agent_trace_events", ["run_id", "sequence"])

    # ------------------------------------------------------------------
    # 9. New tables: llm_usage, refresh_tokens, outbox_events
    # ------------------------------------------------------------------
    op.create_table(
        "llm_usage",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_run_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(14, 6), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_usage_organization_id", "llm_usage", ["organization_id"])
    op.create_index("ix_llm_usage_agent_run_id", "llm_usage", ["agent_run_id"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token", name="uq_refresh_tokens_token"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token", "refresh_tokens", ["token"])

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", sa.dialects.postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outbox_events_event_type", "outbox_events", ["event_type"])
    op.create_index("ix_outbox_events_status", "outbox_events", ["status"])

    # ------------------------------------------------------------------
    # 10. Conversations: add composite index
    # ------------------------------------------------------------------
    op.create_index("ix_conv_org_created", "conversations", ["organization_id", "created_at"])

    # ------------------------------------------------------------------
    # 11. AuditEvents: add composite index
    # ------------------------------------------------------------------
    op.create_index("ix_audit_ev_org_created", "audit_events", ["organization_id", "created_at"])

    # ------------------------------------------------------------------
    # 12. EvalRun: add started_at, make completed_at nullable
    # ------------------------------------------------------------------
    op.add_column("eval_runs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("eval_runs", "completed_at", existing_type=sa.DateTime(timezone=True), nullable=True, server_default=None)


def downgrade() -> None:
    # Remove in reverse order
    op.alter_column("eval_runs", "completed_at", existing_type=sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    op.drop_column("eval_runs", "started_at")

    op.drop_index("ix_audit_ev_org_created", table_name="audit_events")
    op.drop_index("ix_conv_org_created", table_name="conversations")

    op.drop_table("outbox_events")
    op.drop_table("refresh_tokens")
    op.drop_table("llm_usage")

    op.drop_index("uq_trace_run_seq", table_name="agent_trace_events")

    op.drop_index("ix_audit_idempotency", table_name="tool_execution_audits")
    op.drop_index("ix_audit_org_started", table_name="tool_execution_audits")
    op.drop_index("ix_audit_run_started", table_name="tool_execution_audits")
    op.drop_index("ix_tool_exec_request_id", table_name="tool_execution_audits")
    op.drop_column("tool_execution_audits", "approval_id")
    op.drop_column("tool_execution_audits", "request_id")
    op.drop_column("tool_execution_audits", "args_hash")

    op.drop_constraint("fk_agent_runs_organization_id", "agent_runs", type_="foreignkey")
    op.drop_index("ix_agent_run_org_created", table_name="agent_runs")
    op.drop_index("ix_agent_runs_organization_id", table_name="agent_runs")
    op.drop_column("agent_runs", "organization_id")

    op.drop_index("ix_approval_pending", table_name="approval_requests")
    op.drop_index("ix_approval_org_status", table_name="approval_requests")
    op.drop_constraint("fk_approval_tool_call", "approval_requests", type_="foreignkey")
    op.drop_constraint("fk_approval_requested_by", "approval_requests", type_="foreignkey")
    op.drop_column("approval_requests", "tool_call_id")
    op.drop_column("approval_requests", "requested_by_id")
    op.drop_column("approval_requests", "args_hash")

    op.drop_table("quotation_items")

    op.drop_constraint("fk_quotations_approval_id", "quotations", type_="foreignkey")
    op.drop_constraint("fk_quotations_approved_by_users", "quotations", type_="foreignkey")
    op.drop_constraint("fk_quotations_created_by_users", "quotations", type_="foreignkey")
    op.drop_index("ix_quotations_code", table_name="quotations")
    op.drop_index("ix_quotation_idempotency", table_name="quotations")
    op.drop_constraint("uq_quotation_org_code", "quotations", type_="unique")
    op.drop_column("quotations", "approval_id")
    op.drop_column("quotations", "approved_by")
    op.drop_column("quotations", "created_by")
    op.drop_column("quotations", "valid_until")
    op.drop_column("quotations", "version")
    op.drop_column("quotations", "currency")
    op.drop_column("quotations", "total_numeric")
    op.drop_column("quotations", "code")

    op.drop_constraint("uq_product_org_sku", "products", type_="unique")
    op.drop_column("products", "currency")

    op.drop_constraint("uq_customer_org_code", "customers", type_="unique")
    op.drop_column("customers", "code")
