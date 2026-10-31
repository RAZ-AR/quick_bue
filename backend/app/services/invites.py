"""A seller's standing invite link (/s/<code>): the supplier's public page and the way to bring own clients.

A buyer who joins through it becomes the seller's client with source `seller_invited` (0% commission). A pair
that already exists keeps its source: a client the platform brought does not turn into an invited one.
"""

import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ClientLink, ClientSource, Invite, Order, Organization, OrgKind, OrgStatus
from app.platform.authz import Action, Actor
from app.platform.clock import utcnow
from app.platform.errors import NotAllowed, NotFound

# No 0/O, 1/I/L: the code is read off a QR caption or typed from a business card
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LEN = 8
_CODE_RE = re.compile(r"^[A-Z0-9]{4,32}$")


class JoinResult(StrEnum):
    joined = "joined"  # new client of this seller, no commission
    already = "already"  # was a client before; nothing changed


def new_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LEN))


def normalize(code: str) -> str | None:
    c = (code or "").strip().upper().replace("-", "")
    return c if _CODE_RE.match(c) else None


async def _active(session: AsyncSession, seller_id: uuid.UUID) -> Invite | None:
    return await session.scalar(
        select(Invite)
        .where(Invite.seller_id == seller_id, Invite.revoked_at.is_(None))
        .order_by(Invite.created_at.desc())
        .limit(1)
    )


async def _create(session: AsyncSession, seller_id: uuid.UUID, user_id: uuid.UUID) -> Invite:
    while True:
        code = new_code()
        if await session.scalar(select(Invite.id).where(Invite.code == code)) is None:
            break
    invite = Invite(seller_id=seller_id, code=code, created_by=user_id)
    session.add(invite)
    await session.flush()
    return invite


def _seller(actor: Actor) -> Actor:
    seller = actor.with_mode(OrgKind.seller)
    seller.require(Action.catalog_edit)  # sharing the link is allowed before verification, like the catalog
    return seller


async def current(session: AsyncSession, actor: Actor) -> Invite:
    """The seller's link; made on first request."""
    seller = _seller(actor)
    return await _active(session, seller.org.id) or await _create(session, seller.org.id, seller.user.id)


async def rotate(session: AsyncSession, actor: Actor) -> Invite:
    """A new code; the old link stops working. Clients who joined stay clients."""
    seller = _seller(actor)
    old = await _active(session, seller.org.id)
    if old is not None:
        old.revoked_at = utcnow()
    return await _create(session, seller.org.id, seller.user.id)


async def resolve(session: AsyncSession, code: str) -> tuple[Invite, Organization] | None:
    """An active link of a seller that is not blocked. The seller may still be waiting for verification."""
    c = normalize(code)
    if c is None:
        return None
    row = (
        await session.execute(
            select(Invite, Organization)
            .join(Organization, Organization.id == Invite.seller_id)
            .where(
                Invite.code == c,
                Invite.revoked_at.is_(None),
                Organization.is_seller.is_(True),
                Organization.status != OrgStatus.blocked,
            )
        )
    ).first()
    return (row[0], row[1]) if row else None


async def join(session: AsyncSession, buyer: Organization, code: str) -> JoinResult:
    found = await resolve(session, code)
    if found is None:
        raise NotFound("invite_not_found")
    invite, seller = found
    if not buyer.is_buyer:
        raise NotAllowed("not_a_buyer")
    if buyer.id == seller.id:
        raise NotAllowed("own_invite")
    link = await session.scalar(
        select(ClientLink).where(ClientLink.seller_id == seller.id, ClientLink.buyer_id == buyer.id)
    )
    if link is not None:
        return JoinResult.already
    session.add(
        ClientLink(
            seller_id=seller.id,
            buyer_id=buyer.id,
            source=ClientSource.seller_invited,
            invite_id=invite.id,
            orders_count=0,
        )
    )
    await session.flush()
    return JoinResult.joined


async def client_of(session: AsyncSession, seller_id: uuid.UUID, buyer_ids: list[uuid.UUID]) -> bool:
    if not buyer_ids:
        return False
    found = await session.scalar(
        select(ClientLink.id).where(ClientLink.seller_id == seller_id, ClientLink.buyer_id.in_(buyer_ids))
    )
    return found is not None


@dataclass(frozen=True)
class ClientRow:
    buyer_id: uuid.UUID
    display_name: str
    source: ClientSource
    since: datetime
    orders: int  # orders placed with this seller, any status
    last_order_at: datetime | None


async def clients(session: AsyncSession, actor: Actor) -> list[ClientRow]:
    """The seller's clients: invited ones and those the platform brought, newest activity first."""
    seller = _seller(actor)
    stats = (
        select(
            Order.buyer_id.label("buyer_id"),
            func.count(Order.id).label("orders"),
            func.max(Order.created_at).label("last_at"),
        )
        .where(Order.seller_id == seller.org.id)
        .group_by(Order.buyer_id)
        .subquery()
    )
    rows = await session.execute(
        select(ClientLink, Organization.display_name, stats.c.orders, stats.c.last_at)
        .join(Organization, Organization.id == ClientLink.buyer_id)
        .outerjoin(stats, stats.c.buyer_id == ClientLink.buyer_id)
        .where(ClientLink.seller_id == seller.org.id)
        .order_by(func.coalesce(stats.c.last_at, ClientLink.created_at).desc())
    )
    return [
        ClientRow(link.buyer_id, name, link.source, link.created_at, orders or 0, last_at)
        for link, name, orders, last_at in rows.all()
    ]


async def invited_count(session: AsyncSession, invite_seller_id: uuid.UUID) -> int:
    return (
        await session.scalar(
            select(func.count(ClientLink.id)).where(
                ClientLink.seller_id == invite_seller_id, ClientLink.source == ClientSource.seller_invited
            )
        )
        or 0
    )
