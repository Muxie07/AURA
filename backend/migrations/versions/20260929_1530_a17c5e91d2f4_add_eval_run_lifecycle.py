"""Add an explicit lifecycle state to evaluation runs."""

import sqlalchemy as sa
from alembic import op

revision = "a17c5e91d2f4"
down_revision = "53a80d3bc908"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "eval_runs",
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
    )
    op.execute("UPDATE eval_runs SET status = 'completed' WHERE sample_count > 0")


def downgrade() -> None:
    op.drop_column("eval_runs", "status")
