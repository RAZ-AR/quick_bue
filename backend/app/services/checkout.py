"""Send the cart: one order per seller, all or nothing (docs/03-architecture.md §2.3)."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.domain import negotiation as neg
from app.models import CartItem, Checkout, Order, OrderLine, OrderStatus, Role
from app.platform.authz import Action, Actor
from app.platform.errors import ValidationFailed
from app.services import orders as order_svc
from app.services.cart import build_cart
from app.services.negotiation import open_negotiation


async def checkout(
    session: AsyncSession,
    actor: Actor,
    now: datetime,
    address_id: uuid.UUID | None = None,
    order_offers: dict[uuid.UUID, int] | None = None,
    note: str | None = None,
) -> list[Order]:
    """order_offers: seller_id -> requested discount on the whole order, in basis points."""
    actor.require(Action.order_place)
    order_offers = order_offers or {}
    view = await build_cart(session, actor, now, address_id, lock=True)
    if not view.groups:
        raise ValidationFailed([{"code": "cart_empty"}])
    if view.address is None:
        raise ValidationFailed([{"code": "address_required"}])

    problems = view.problems
    groups = {g.seller.id: g for g in view.groups}
    for seller_id, percent in order_offers.items():
        group = groups.get(seller_id)
        if group is None:
            problems.append({"seller_id": str(seller_id), "code": "seller_not_in_cart"})
        elif not actor.can(Action.offer_make):
            problems.append({"seller_id": str(seller_id), "code": "not_allowed_to_negotiate"})
        elif any(li.item.offer_price_amd is not None for li in group.lines):
            problems.append({"seller_id": str(seller_id), "code": "line_and_order_offers_together"})
        elif problem := neg.check_buyer_percent(
            percent, group.totals.subtotal_amd, get_settings().offer_min_line_amd
        ):
            problems.append({"seller_id": str(seller_id), "code": problem})
    limit = actor.membership.order_limit_amd
    if actor.role == Role.buyer_staff and limit is not None and view.total_amd > limit:
        problems.append({"code": "over_staff_limit", "limit_amd": limit, "total_amd": view.total_amd})
    if problems:
        raise ValidationFailed(problems)

    co = Checkout(buyer_id=actor.org.id, user_id=actor.user.id, address_id=view.address.id)
    session.add(co)
    created: list[Order] = []
    for group in view.groups:
        line_offers_by_position: dict[int, int] = {}
        lines: list[OrderLine] = []
        for pos, li in enumerate(group.lines):
            offered = li.item.offer_price_amd
            if offered is not None:
                line_offers_by_position[pos] = offered
            lines.append(
                OrderLine(
                    position=pos,
                    product_id=li.product.id,
                    name_snapshot=li.product.name,
                    unit=li.product.unit,
                    qty_ordered=Decimal(li.item.qty),
                    list_price_amd=li.unit_price.amount_amd,
                    price_source=li.unit_price.source,
                    final_price_amd=None if offered is not None else li.unit_price.amount_amd,
                )
            )
        percent = order_offers.get(group.seller.id)
        negotiating = bool(line_offers_by_position) or percent is not None
        order = Order(
            checkout=co,
            buyer_id=actor.org.id,
            seller_id=group.seller.id,
            placed_by=actor.user.id,
            address_id=view.address.id,
            status=OrderStatus.negotiating if negotiating else OrderStatus.placed,
            delivery_date=group.delivery_date,
            buyer_note=note,
            lines=lines,
        )
        session.add(order)
        await session.flush()
        await order_svc.ensure_client_link(session, group.seller.id, actor.org.id)
        await order_svc.recompute(session, order)
        order_svc.log(
            session, order, "created", actor.user.id, total=order.total_amd, negotiating=negotiating
        )
        if negotiating:
            await open_negotiation(
                session,
                order,
                actor,
                now,
                line_offers={lines[pos].id: price for pos, price in line_offers_by_position.items()} or None,
                percent_bp=percent,
            )
        else:
            order_svc.log(session, order, "placed", actor.user.id)
        created.append(order)

    await session.execute(delete(CartItem).where(CartItem.buyer_id == actor.org.id))
    return created
