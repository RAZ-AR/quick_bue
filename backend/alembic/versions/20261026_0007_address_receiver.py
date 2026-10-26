"""address receiver contact and archive

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-26 22:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("addresses", sa.Column("contact_name", sa.String(length=120), nullable=True))
    op.add_column("addresses", sa.Column("contact_phone", sa.String(length=32), nullable=True))
    op.add_column("addresses", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("addresses", "archived_at")
    op.drop_column("addresses", "contact_phone")
    op.drop_column("addresses", "contact_name")
