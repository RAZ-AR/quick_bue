"""Self sign-up of a company: look it up by TIN, confirm the prefilled requisites, become its owner."""

from dataclasses import dataclass, field
from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.registry import CompanyInfo, get_registry, normalize_tin
from app.models import (
    Address,
    Membership,
    Organization,
    OrgKind,
    OrgStatus,
    Role,
    SellerProfile,
    TaxRegime,
    User,
    VenueType,
)
from app.platform.authz import Action, Actor
from app.platform.errors import Conflict, ValidationFailed


@dataclass
class LookupResult:
    tin: str
    company: CompanyInfo | None
    already_registered: bool
    provider: str


async def lookup(session: AsyncSession, raw_tin: str) -> LookupResult:
    tin = normalize_tin(raw_tin)
    if tin is None:
        raise ValidationFailed([{"code": "bad_tin"}])
    registry = get_registry()
    company = await registry.lookup(tin)
    taken = await session.scalar(select(Organization.id).where(Organization.tin == tin)) is not None
    return LookupResult(tin, company, taken, registry.name)


@dataclass
class NewOrganization:
    kind: OrgKind
    tin: str
    legal_name: str
    display_name: str
    tax_regime: TaxRegime | None = None
    registration_number: str | None = None
    legal_address: str | None = None
    director_name: str | None = None
    bank_name: str | None = None
    bank_account: str | None = None
    phone: str | None = None
    email: str | None = None
    venue_type: VenueType | None = None
    delivery_address: str | None = None
    district: str | None = None
    extra: dict = field(default_factory=dict)


async def create_organization(session: AsyncSession, user: User, data: NewOrganization) -> Organization:
    tin = normalize_tin(data.tin)
    problems = []
    if tin is None:
        problems.append({"field": "tin", "code": "bad_tin"})
    if not data.legal_name.strip():
        problems.append({"field": "legal_name", "code": "required"})
    if data.kind == OrgKind.buyer and not (data.delivery_address or "").strip():
        problems.append({"field": "delivery_address", "code": "required"})
    if problems:
        raise ValidationFailed(problems)
    if await session.scalar(select(Organization.id).where(Organization.tin == tin)):
        # Joining an existing company needs an invite from its owner (not built yet)
        raise Conflict("tin_taken", "this company is already on QB")

    # Requisites match the registry? Remember the source, so the operator knows what was typed by hand
    registry = get_registry()
    found = await registry.lookup(tin)  # type: ignore[arg-type]
    source = registry.name if found and found.legal_name == data.legal_name else "manual"
    if found and not found.active:
        raise ValidationFailed([{"field": "tin", "code": "company_inactive"}])

    org = Organization(
        kind=data.kind,
        tin=tin,
        legal_name=data.legal_name.strip(),
        display_name=(data.display_name or data.legal_name).strip(),
        tax_regime=data.tax_regime,
        registration_number=data.registration_number,
        legal_address=data.legal_address,
        director_name=data.director_name,
        bank_name=data.bank_name,
        bank_account=data.bank_account,
        phone=data.phone,
        email=data.email,
        venue_type=data.venue_type if data.kind == OrgKind.buyer else None,
        # Sellers trade only after an operator checks their documents
        status=OrgStatus.pending if data.kind == OrgKind.seller else OrgStatus.active,
        registry_source=source,
    )
    session.add(org)
    await session.flush()
    session.add(Membership(user_id=user.id, organization_id=org.id, role=Role.owner))
    if data.kind == OrgKind.seller:
        session.add(SellerProfile(organization_id=org.id, cutoff_time=time(16, 0), lead_days=1))
    else:
        session.add(
            Address(
                organization_id=org.id,
                label="Main",
                text=data.delivery_address.strip(),
                district=data.district,
            )
        )
    return org


REQUISITE_FIELDS = (
    "display_name",
    "legal_address",
    "director_name",
    "bank_name",
    "bank_account",
    "phone",
    "email",
    "registration_number",
    "tax_regime",
)


async def update_requisites(session: AsyncSession, actor: Actor, changes: dict) -> Organization:
    actor.require(Action.org_staff)
    for key, value in changes.items():
        if key in REQUISITE_FIELDS:
            setattr(actor.org, key, value)
    return actor.org
