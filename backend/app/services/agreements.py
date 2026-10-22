"""Contract prices: a negotiated price fixed for one buyer for N days (docs/03-architecture.md §2.8)."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.orders import By
from app.models import AgreementStatus, ClientLink, OrderLine, OrgKind, PriceAgreement, PriceSource
from app.platform.authz import Action, Actor
from app.platform.clock import local
from app.platform.errors import Conflict, NotFound, ValidationFailed
from app.services import negotiation as nego_svc
from app.services import orders as order_svc


async def create_from_line(
    session: AsyncSession, actor: Actor, order_line_id: uuid.UUID, days: int, now: datetime
) -> PriceAgreement:
    actor = actor.with_mode(OrgKind.seller)
    actor.require(Action.agreement_create)
    if not 1 <= days <= 365:
        raise ValidationFailed([{"code": "bad_days"}])
    line = await session.get(OrderLine, order_line_id)
    if line is None:
        raise NotFound("order_line_not_found")
    order = await order_svc.get_for_actor(session, actor, line.order_id)
    if order_svc.side_of(actor, order) != By.seller:
        raise NotFound("order_line_not_found")
    if line.price_source != PriceSource.negotiated or line.final_price_amd is None or line.product_id is None:
        raise Conflict("line_not_negotiated")
    link = await order_svc.ensure_client_link(session, order.seller_id, order.buyer_id)
    # One active contract per product and buyer: the new one replaces the old
    await session.execute(
        update(PriceAgreement)
        .where(
            PriceAgreement.client_link_id == link.id,
            PriceAgreement.product_id == line.product_id,
            PriceAgreement.status == AgreementStatus.active,
        )
        .values(status=AgreementStatus.cancelled)
    )
    nego = await nego_svc.load_for_order(session, order.id)
    today = local(now).date()
    agreement = PriceAgreement(
        client_link_id=link.id,
        product_id=line.product_id,
        price_amd=line.final_price_amd,
        valid_from=today,
        valid_until=today + timedelta(days=days),
        source_negotiation_id=nego.id if nego else None,
    )
    session.add(agreement)
    order_svc.log(session, order, "agreement_created", actor.user.id, product_id=line.product_id, days=days)
    return agreement


async def expire_due(session: AsyncSession, now: datetime) -> int:
    result = await session.execute(
        update(PriceAgreement)
        .where(
            PriceAgreement.status == AgreementStatus.active, PriceAgreement.valid_until < local(now).date()
        )
        .values(status=AgreementStatus.expired)
    )
    return result.rowcount or 0


async def list_for_actor(session: AsyncSession, actor: Actor) -> list[PriceAgreement]:
    column = ClientLink.buyer_id if actor.is_buyer else ClientLink.seller_id
    rows = await session.scalars(
        select(PriceAgreement)
        .join(ClientLink, ClientLink.id == PriceAgreement.client_link_id)
        .where(column == actor.org.id, PriceAgreement.status == AgreementStatus.active)
        .order_by(PriceAgreement.valid_until)
    )
    return list(rows)
