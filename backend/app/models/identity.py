"""People and organizations: users, buyer/seller orgs, memberships, addresses, seller terms, invites."""

import uuid
from datetime import datetime, time
from enum import StrEnum

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Amd, Base, I18nText, Timestamped, UUIDPk, str_enum


class Locale(StrEnum):
    hy = "hy"
    ru = "ru"
    en = "en"


class OrgKind(StrEnum):
    buyer = "buyer"
    seller = "seller"


class OrgStatus(StrEnum):
    pending = "pending"  # seller waiting for moderation
    active = "active"
    blocked = "blocked"


class TaxRegime(StrEnum):
    vat = "vat"
    turnover = "turnover"
    micro = "micro"


class VenueType(StrEnum):
    cafe = "cafe"
    restaurant = "restaurant"
    bar = "bar"
    bakery = "bakery"
    hotel = "hotel"
    catering = "catering"
    other = "other"


class Role(StrEnum):
    owner = "owner"
    manager = "manager"  # seller-side sales manager
    buyer_staff = "buyer_staff"  # chef, barman: builds carts, limited ordering


class User(UUIDPk, Timestamped, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    locale: Mapped[Locale] = mapped_column(str_enum(Locale), default=Locale.hy)
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="user")


class Organization(UUIDPk, Timestamped, Base):
    __tablename__ = "organizations"

    kind: Mapped[OrgKind] = mapped_column(str_enum(OrgKind), index=True)
    legal_name: Mapped[str] = mapped_column(String(300))
    display_name: Mapped[str] = mapped_column(String(200))
    # Armenian taxpayer ID (ՀՎՀՀ), 8 digits
    tin: Mapped[str | None] = mapped_column(String(16), unique=True)
    tax_regime: Mapped[TaxRegime | None] = mapped_column(str_enum(TaxRegime))
    status: Mapped[OrgStatus] = mapped_column(str_enum(OrgStatus), default=OrgStatus.active)
    venue_type: Mapped[VenueType | None] = mapped_column(str_enum(VenueType))

    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization")
    seller_profile: Mapped["SellerProfile | None"] = relationship(back_populates="organization")


class Membership(UUIDPk, Timestamped, Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "organization_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[Role] = mapped_column(str_enum(Role))
    # Buyer staff: max order total they may place alone; null = no limit
    order_limit_amd: Mapped[int | None] = mapped_column(Amd)
    can_negotiate: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship(back_populates="memberships")
    organization: Mapped[Organization] = relationship(back_populates="memberships")


class Address(UUIDPk, Timestamped, Base):
    __tablename__ = "addresses"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(120))
    text: Mapped[str] = mapped_column(Text)
    district: Mapped[str | None] = mapped_column(String(64))
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6))
    lng: Mapped[float | None] = mapped_column(Numeric(9, 6))
    delivery_notes: Mapped[str | None] = mapped_column(Text)


class SellerProfile(Timestamped, Base):
    __tablename__ = "seller_profiles"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    description: Mapped[dict | None] = mapped_column(I18nText)
    min_order_amd: Mapped[int] = mapped_column(Amd, default=0)
    # Orders placed before cutoff_time are delivered after lead_days
    cutoff_time: Mapped[time] = mapped_column(Time, default=time(16, 0))
    lead_days: Mapped[int] = mapped_column(SmallInteger, default=1)
    delivery_fee_amd: Mapped[int] = mapped_column(Amd, default=0)
    free_delivery_from_amd: Mapped[int | None] = mapped_column(Amd)
    offer_response_hours: Mapped[int] = mapped_column(SmallInteger, default=24)
    logo_url: Mapped[str | None] = mapped_column(String(500))

    organization: Mapped[Organization] = relationship(back_populates="seller_profile")


class DeliveryZone(UUIDPk, Timestamped, Base):
    __tablename__ = "delivery_zones"
    __table_args__ = (UniqueConstraint("seller_id", "district"),)

    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    district: Mapped[str] = mapped_column(String(64))
    # ISO weekdays 1..7
    weekdays: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=lambda: [1, 2, 3, 4, 5, 6])


class Invite(UUIDPk, Timestamped, Base):
    """A seller's link/QR: buyers who join through it become the seller's own clients (0% commission)."""

    __tablename__ = "invites"

    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(32), unique=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    used_by_org_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL")
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
