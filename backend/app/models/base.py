import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, Enum, MetaData, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from uuid6 import uuid7

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Money: whole drams (AMD has no subunit in use). Quantities: up to 3 decimals (kg, l).
Amd = BigInteger
Qty = Numeric(12, 3)
# Catalog texts: {"hy": "...", "ru": "...", "en": "..."}
I18nText = JSONB


def str_enum(cls: type[StrEnum]) -> Enum:
    """Store enums as VARCHAR + CHECK: portable and cheap to extend in migrations."""
    return Enum(
        cls,
        native_enum=False,
        length=32,
        values_callable=lambda e: [m.value for m in e],
        name=cls.__name__.lower(),
        create_constraint=True,
    )


def new_id() -> uuid.UUID:
    # UUID v7: time-ordered, so new rows land at the end of the index
    return uuid.UUID(str(uuid7()))


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


class UUIDPk:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
