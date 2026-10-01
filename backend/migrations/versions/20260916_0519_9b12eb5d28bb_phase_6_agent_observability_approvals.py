"""phase_6_agent_observability_approvals

Revision ID: 9b12eb5d28bb
Revises: 61591430610a
Create Date: 2026-09-16 05:19:38.857127+00:00
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9b12eb5d28bb'
down_revision: str | None = '61591430610a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add new columns to agent_runs
    op.add_column('agent_runs', sa.Column('task_type', sa.String(length=50), nullable=True))
    op.add_column('agent_runs', sa.Column('selected_model', sa.String(length=100), nullable=True))
    op.add_column('agent_runs', sa.Column('tool_call_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('agent_runs', sa.Column('retries', sa.Integer(), server_default='0', nullable=False))
    op.add_column('agent_runs', sa.Column('replans', sa.Integer(), server_default='0', nullable=False))

    # 2. Create agent_trace_events table
    op.create_table(
        'agent_trace_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('component', sa.String(length=100), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_agent_trace_events_organization_id'), 'agent_trace_events', ['organization_id'], unique=False)
    op.create_index(op.f('ix_agent_trace_events_run_id'), 'agent_trace_events', ['run_id'], unique=False)
    op.create_index(op.f('ix_agent_trace_events_event_type'), 'agent_trace_events', ['event_type'], unique=False)



def downgrade() -> None:


    op.drop_index(op.f('ix_agent_trace_events_event_type'), table_name='agent_trace_events')
    op.drop_index(op.f('ix_agent_trace_events_run_id'), table_name='agent_trace_events')
    op.drop_index(op.f('ix_agent_trace_events_organization_id'), table_name='agent_trace_events')
    op.drop_table('agent_trace_events')

    op.drop_column('agent_runs', 'replans')
    op.drop_column('agent_runs', 'retries')
    op.drop_column('agent_runs', 'tool_call_count')
    op.drop_column('agent_runs', 'selected_model')
    op.drop_column('agent_runs', 'task_type')
