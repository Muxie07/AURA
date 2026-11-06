"""Add UserRole and APIKey

Revision ID: phase2_auth
Revises: 9f0f162b8a67
Create Date: 2026-10-01 14:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'phase2_auth'
down_revision = '9f0f162b8a67'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Create API keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('key_hash', sa.String(length=128), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_api_keys_organization_id_organizations'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_api_keys'))
    )
    op.create_index(op.f('ix_api_keys_organization_id'), 'api_keys', ['organization_id'], unique=False)

    # 2. Add role enum to users, handle existing rows
    user_role_enum = postgresql.ENUM('owner', 'admin', 'member', 'viewer', name='user_role_enum')
    user_role_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('users', sa.Column('role', user_role_enum, server_default='member', nullable=False))

    # Optional: map is_superuser to owner if needed, but here we just drop is_superuser
    op.drop_column('users', 'is_superuser')

def downgrade() -> None:
    op.add_column('users', sa.Column('is_superuser', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False))
    op.drop_column('users', 'role')
    op.drop_index(op.f('ix_api_keys_organization_id'), table_name='api_keys')
    op.drop_table('api_keys')

    user_role_enum = postgresql.ENUM('owner', 'admin', 'member', 'viewer', name='user_role_enum')
    user_role_enum.drop(op.get_bind(), checkfirst=True)
