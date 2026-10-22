import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models import Locale, OrgKind, Role, Unit


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DevLoginIn(BaseModel):
    email: str


class OrgOut(ORM):
    id: uuid.UUID
    kind: OrgKind
    display_name: str


class MembershipOut(ORM):
    role: Role
    organization: OrgOut


class MeOut(ORM):
    id: uuid.UUID
    name: str
    email: str | None
    locale: Locale
    is_platform_admin: bool
    memberships: list[MembershipOut]


class CategoryOut(ORM):
    id: uuid.UUID
    parent_id: uuid.UUID | None
    slug: str
    name: dict[str, str]


class TierOut(ORM):
    min_qty: Decimal
    price_amd: int


class SellerBrief(BaseModel):
    id: uuid.UUID
    display_name: str


class ProductOut(ORM):
    id: uuid.UUID
    seller: SellerBrief
    category_id: uuid.UUID | None
    name: dict[str, str]
    unit: Unit
    pack_size: str | None
    base_price_amd: int
    vat_included: bool
    min_qty: Decimal
    qty_step: Decimal
    in_stock: bool
    allow_offers: bool
    images: list[str]
    tiers: list[TierOut]


class ProductPage(BaseModel):
    items: list[ProductOut]
    total: int
