"""reusable supplier invite links

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-31 07:18:20.021302
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0011'
down_revision: str | None = '0010'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('client_links', sa.Column('invite_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(op.f('fk_client_links_invite_id_invites'), 'client_links', 'invites', ['invite_id'], ['id'], ondelete='SET NULL')
    op.add_column('invites', sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True))
    # Old invites were one-off: remember who came through them, then retire them
    op.execute(
        "UPDATE client_links SET invite_id = i.id FROM invites i "
        "WHERE i.seller_id = client_links.seller_id AND i.used_by_org_id = client_links.buyer_id"
    )
    op.execute("UPDATE invites SET revoked_at = now() WHERE used_by_org_id IS NOT NULL")
    op.drop_constraint(op.f('fk_invites_used_by_org_id_organizations'), 'invites', type_='foreignkey')
    op.drop_column('invites', 'used_at')
    op.drop_column('invites', 'used_by_org_id')


def downgrade() -> None:
    op.add_column('invites', sa.Column('used_by_org_id', sa.UUID(), autoincrement=False, nullable=True))
    op.add_column('invites', sa.Column('used_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True))
    op.create_foreign_key(op.f('fk_invites_used_by_org_id_organizations'), 'invites', 'organizations', ['used_by_org_id'], ['id'], ondelete='SET NULL')
    op.drop_column('invites', 'revoked_at')
    op.drop_constraint(op.f('fk_client_links_invite_id_invites'), 'client_links', type_='foreignkey')
    op.drop_column('client_links', 'invite_id')
