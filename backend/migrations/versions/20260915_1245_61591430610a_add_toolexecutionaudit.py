"""Add ToolExecutionAudit

Revision ID: 61591430610a
Revises: 002_add_rag_tables
Create Date: 2026-09-15 12:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "61591430610a"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tool_execution_audits",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("agent_run_id", sa.UUID(), nullable=False),
        sa.Column("execution_id", sa.String(length=100), nullable=False),
        sa.Column("tool_name", sa.String(length=255), nullable=False),
        sa.Column("tool_version", sa.String(length=50), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("risk_level", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("input_hash", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_type", sa.String(length=255), nullable=True),
        sa.Column("error_code", sa.String(length=255), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tool_execution_audits_agent_run_id"),
        "tool_execution_audits",
        ["agent_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tool_execution_audits_execution_id"),
        "tool_execution_audits",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tool_execution_audits_idempotency_key"),
        "tool_execution_audits",
        ["idempotency_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tool_execution_audits_organization_id"),
        "tool_execution_audits",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tool_execution_audits_status"), "tool_execution_audits", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_tool_execution_audits_tool_name"),
        "tool_execution_audits",
        ["tool_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tool_execution_audits_tool_name"), table_name="tool_execution_audits")
    op.drop_index(op.f("ix_tool_execution_audits_status"), table_name="tool_execution_audits")
    op.drop_index(
        op.f("ix_tool_execution_audits_organization_id"), table_name="tool_execution_audits"
    )
    op.drop_index(
        op.f("ix_tool_execution_audits_idempotency_key"), table_name="tool_execution_audits"
    )
    op.drop_index(op.f("ix_tool_execution_audits_execution_id"), table_name="tool_execution_audits")
    op.drop_index(op.f("ix_tool_execution_audits_agent_run_id"), table_name="tool_execution_audits")
    op.drop_table("tool_execution_audits")
