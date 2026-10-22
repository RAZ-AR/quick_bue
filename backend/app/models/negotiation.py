"""Price negotiation attached to an order: rounds of offers, per-line decisions (docs/02-mvp.md §6)."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Amd, Base, Timestamped, UUIDPk, str_enum


class NegotiationStatus(StrEnum):
    awaiting_seller = "awaiting_seller"
    awaiting_buyer = "awaiting_buyer"
    agreed = "agreed"
    declined = "declined"
    expired = "expired"


class NegotiationScope(StrEnum):
    lines = "lines"  # price per line
    order = "order"  # one offer for the whole order


class Side(StrEnum):
    buyer = "buyer"
    seller = "seller"


class OfferKind(StrEnum):
    price = "price"  # per-line prices in offer_lines
    percent = "percent"  # discount on the whole order
    order_total = "order_total"  # "everything for X"


class OfferResponse(StrEnum):
    accepted = "accepted"
    countered = "countered"
    declined = "declined"
    expired = "expired"
    superseded = "superseded"  # replaced by a newer offer from the same side


class LineDecision(StrEnum):
    accepted = "accepted"
    declined = "declined"
    countered = "countered"


class Negotiation(UUIDPk, Timestamped, Base):
    __tablename__ = "negotiations"

    # One negotiation per order
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), unique=True)
    status: Mapped[NegotiationStatus] = mapped_column(str_enum(NegotiationStatus), index=True)
    scope: Mapped[NegotiationScope] = mapped_column(str_enum(NegotiationScope))
    round: Mapped[int] = mapped_column(SmallInteger, default=1)
    # The scheduler expires negotiations past this moment
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    offers: Mapped[list["Offer"]] = relationship(
        back_populates="negotiation", order_by="Offer.created_at", cascade="all, delete-orphan"
    )


class Offer(UUIDPk, Timestamped, Base):
    __tablename__ = "offers"
    __table_args__ = (
        CheckConstraint(
            "(kind = 'price') OR (kind = 'percent' AND percent_bp IS NOT NULL) "
            "OR (kind = 'order_total' AND order_total_amd IS NOT NULL)",
            name="kind_payload",
        ),
    )

    negotiation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("negotiations.id", ondelete="CASCADE"), index=True
    )
    from_side: Mapped[Side] = mapped_column(str_enum(Side))
    # Null author + is_auto = seller autopilot
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    is_auto: Mapped[bool] = mapped_column(Boolean, default=False)
    kind: Mapped[OfferKind] = mapped_column(str_enum(OfferKind))
    order_total_amd: Mapped[int | None] = mapped_column(Amd)
    percent_bp: Mapped[int | None] = mapped_column(Integer)  # 700 = -7%
    message: Mapped[str | None] = mapped_column(Text)
    response: Mapped[OfferResponse | None] = mapped_column(str_enum(OfferResponse))

    negotiation: Mapped[Negotiation] = relationship(back_populates="offers")
    lines: Mapped[list["OfferLine"]] = relationship(back_populates="offer", cascade="all, delete-orphan")


class OfferLine(UUIDPk, Base):
    __tablename__ = "offer_lines"

    offer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offers.id", ondelete="CASCADE"), index=True)
    order_line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("order_lines.id", ondelete="CASCADE"), index=True
    )
    proposed_price_amd: Mapped[int] = mapped_column(Amd)
    decision: Mapped[LineDecision | None] = mapped_column(str_enum(LineDecision))

    offer: Mapped[Offer] = relationship(back_populates="lines")
