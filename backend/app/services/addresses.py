"""Delivery addresses of a buying company: several per company, each with the person who receives the goods.

Added after sign-up from the company cabinet. Removing an address archives it: old orders and their
delivery notes keep pointing at it.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.contacts import normalize_phone
from app.models import Address
from app.platform.authz import Action, Actor
from app.platform.errors import NotFound, ValidationFailed


@dataclass
class AddressIn:
    label: str
    text: str
    district: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    delivery_notes: str | None = None
    lat: float | None = None
    lng: float | None = None


def _clean(value: str | None, limit: int) -> str | None:
    value = (value or "").strip()
    return value[:limit] or None


def _validate(data: AddressIn) -> AddressIn:
    problems = []
    text = _clean(data.text, 500)
    if not text:
        problems.append({"field": "text", "code": "required"})
    phone = None
    if (data.contact_phone or "").strip():
        phone = normalize_phone(data.contact_phone)
        if phone is None:
            problems.append({"field": "contact_phone", "code": "bad_phone"})
    if problems:
        raise ValidationFailed(problems)
    return AddressIn(
        label=_clean(data.label, 120) or (text or "")[:60],
        text=text or "",
        district=_clean(data.district, 64),
        contact_name=_clean(data.contact_name, 120),
        contact_phone=phone,
        delivery_notes=_clean(data.delivery_notes, 500),
        lat=data.lat,
        lng=data.lng,
    )


async def list_for(session: AsyncSession, actor: Actor) -> list[Address]:
    rows = await session.scalars(
        select(Address)
        .where(Address.organization_id == actor.org.id, Address.archived_at.is_(None))
        .order_by(Address.created_at)
    )
    return list(rows)


async def create(session: AsyncSession, actor: Actor, data: AddressIn) -> Address:
    actor.require(Action.org_staff)
    clean = _validate(data)
    address = Address(organization_id=actor.org.id, **clean.__dict__)
    session.add(address)
    await session.flush()
    return address


async def _own(session: AsyncSession, actor: Actor, address_id: uuid.UUID) -> Address:
    address = await session.get(Address, address_id)
    if address is None or address.organization_id != actor.org.id or address.archived_at is not None:
        raise NotFound("address_not_found")
    return address


async def update(session: AsyncSession, actor: Actor, address_id: uuid.UUID, data: AddressIn) -> Address:
    actor.require(Action.org_staff)
    address = await _own(session, actor, address_id)
    for key, value in _validate(data).__dict__.items():
        setattr(address, key, value)
    return address


async def archive(session: AsyncSession, actor: Actor, address_id: uuid.UUID, now: datetime) -> None:
    actor.require(Action.org_staff)
    address = await _own(session, actor, address_id)
    address.archived_at = now
