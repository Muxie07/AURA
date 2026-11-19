"""Add UTCP Integration and Credential Tables.

Revision ID: utcp_integration
Revises: phase3_models
Create Date: 2026-10-15

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "utcp_integration"
down_revision = "phase3_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create integration_credentials table
    op.create_table(
        "integration_credentials",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("credential_type", sa.String(50), nullable=False),
        sa.Column("encrypted_payload", sa.LargeBinary(), nullable=False),
        sa.Column("header_name", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", "name", name="uq_org_credential_name"),
    )

    # 2. Create external_tool_endpoints table
    op.create_table(
        "external_tool_endpoints",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("protocol", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("manifest_url", sa.String(500), nullable=True),
        sa.Column("manifest_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "credential_id",
            sa.UUID(),
            sa.ForeignKey("integration_credentials.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("health_status", sa.String(20), server_default="unknown", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", "name", name="uq_org_endpoint_name"),
    )


def downgrade() -> None:
    op.drop_table("external_tool_endpoints")
    op.drop_table("integration_credentials")
