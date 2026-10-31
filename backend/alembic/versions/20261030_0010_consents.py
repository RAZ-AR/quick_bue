"""consents to the public offer and the personal data policy

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-30 09:10:32.223637
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0010'
down_revision: str | None = '0009'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('consents',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=True),
    sa.Column('document', sa.Enum('terms', 'privacy', name='legaldoc', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('version', sa.String(length=32), nullable=False),
    sa.Column('accepted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('ip', sa.String(length=64), nullable=True),
    sa.Column('user_agent', sa.String(length=300), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_consents_organization_id_organizations'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_consents_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_consents')),
    sa.UniqueConstraint('user_id', 'document', 'version', name=op.f('uq_consents_user_id_document_version'))
    )
    op.create_index(op.f('ix_consents_user_id'), 'consents', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_consents_user_id'), table_name='consents')
    op.drop_table('consents')
