"""Platform money and plumbing: commission rules and statements, notifications, audit log, tax documents."""

import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Amd, Base, I18nText, Timestamped, UUIDPk, str_enum
from app.models.catalog import ClientSource


class StatementStatus(StrEnum):
    draft = "draft"
    issued = "issued"
    paid = "paid"


class Channel(StrEnum):
    telegram = "telegram"
    push = "push"
    email = "email"


class DocumentKind(StrEnum):
    tax_invoice = "tax_invoice"  # SRC e-invoice (calculation document)
    waybill = "waybill"


class DocumentStatus(StrEnum):
    draft = "draft"
    issued = "issued"
    failed = "failed"
    cancelled = "cancelled"


class CommissionRule(UUIDPk, Timestamped, Base):
    """Rate in basis points. category_id null = default for all categories."""

    __tablename__ = "commission_rules"

    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))
    client_source: Mapped[ClientSource] = mapped_column(str_enum(ClientSource))
    rate_bp: Mapped[int] = mapped_column(Integer)
    first_order_bonus_bp: Mapped[int] = mapped_column(Integer, default=0)
    valid_from: Mapped[date] = mapped_column(Date)


class CommissionStatement(UUIDPk, Timestamped, Base):
    """Monthly commission invoice from QB to a seller."""

    __tablename__ = "commission_statements"
    __table_args__ = (UniqueConstraint("seller_id", "period"),)

    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    period: Mapped[date] = mapped_column(Date)  # first day of the month
    turnover_amd: Mapped[int] = mapped_column(Amd, default=0)
    commission_amd: Mapped[int] = mapped_column(Amd, default=0)
    status: Mapped[StatementStatus] = mapped_column(str_enum(StatementStatus), default=StatementStatus.draft)
    file_url: Mapped[str | None] = mapped_column(String(500))


class Notification(UUIDPk, Timestamped, Base):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    channel: Mapped[Channel] = mapped_column(str_enum(Channel))
    type: Mapped[str] = mapped_column(String(48))
    payload: Mapped[dict | None] = mapped_column(I18nText)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(UUIDPk, Timestamped, Base):
    __tablename__ = "audit_log"

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # Set when an operator acts "as" a customer
    impersonated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(64))
    entity: Mapped[str] = mapped_column(String(48))
    entity_id: Mapped[uuid.UUID | None] = mapped_column()
    payload: Mapped[dict | None] = mapped_column(I18nText)


class Document(UUIDPk, Timestamped, Base):
    """Placeholder for SRC e-invoices and waybills (second stage, law HO-309-N). Not filled in the MVP."""

    __tablename__ = "documents"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    kind: Mapped[DocumentKind] = mapped_column(str_enum(DocumentKind))
    external_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[DocumentStatus] = mapped_column(str_enum(DocumentStatus), default=DocumentStatus.draft)
    payload: Mapped[dict | None] = mapped_column(I18nText)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
