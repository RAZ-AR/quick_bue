"""Cart suggestions (cross-sell): what to add to this cart and why. Rules live in domain/suggestions.py.

A product is suggested once, under its most useful reason: fill a gap > volume price > seller's service >
usually bought > goes with the order.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain import suggestions as rules
from app.models import (
    Category,
    DeliveryZone,
    Order,
    OrderLine,
    OrderStatus,
    Organization,
    OrgStatus,
    PriceSource,
    Product,
    VerificationStatus,
)
from app.platform.authz import Actor
from app.platform.clock import local
from app.services.cart import build_cart
from app.services.prices import load_price_book

LOOKBACK = timedelta(days=90)
_LIVE = (
    OrderStatus.placed,
    OrderStatus.confirmed,
    OrderStatus.delivering,
    OrderStatus.delivered,
    OrderStatus.accepted,
)
MAX_USUAL = 6
MAX_COMPLEMENT = 4


@dataclass
class Suggestion:
    kind: str  # fill_min | fill_free_delivery | tier | service | usual | complement
    seller: Organization
    product: Product
    price_amd: int  # per unit, for this buyer
    qty: Decimal  # what to put in the cart (the whole line quantity for "tier")
    gap_amd: int | None = None
    saving_amd: int | None = None
    last_qty: Decimal | None = None


def _sellable():
    """Products a buyer can order: live product of a verified, not blocked seller."""
    return (
        select(Product, Organization)
        .join(Organization, Organization.id == Product.seller_id)
        .where(
            Organization.is_seller.is_(True),
            Organization.verification_status == VerificationStatus.verified,
            Organization.status != OrgStatus.blocked,
            Product.archived_at.is_(None),
            Product.in_stock.is_(True),
        )
    )


async def _popularity(session: AsyncSession, product_ids: list[uuid.UUID], since: datetime) -> dict:
    if not product_ids:
        return {}
    rows = await session.execute(
        select(OrderLine.product_id, func.count(OrderLine.id))
        .join(Order, Order.id == OrderLine.order_id)
        .where(OrderLine.product_id.in_(product_ids), Order.created_at >= since, Order.status.in_(_LIVE))
        .group_by(OrderLine.product_id)
    )
    return dict(rows.all())


async def for_cart(
    session: AsyncSession, actor: Actor, now: datetime, address_id: uuid.UUID | None = None
) -> list[Suggestion]:
    view = await build_cart(session, actor, now, address_id)
    today = local(now).date()
    in_cart = {li.product.id for g in view.groups for li in g.lines}
    since = now - LOOKBACK

    # What this venue bought lately: product -> the last quantity
    history: dict[uuid.UUID, Decimal] = {}
    rows = await session.execute(
        select(OrderLine.product_id, OrderLine.qty_ordered)
        .join(Order, Order.id == OrderLine.order_id)
        .where(Order.buyer_id == actor.org.id, Order.created_at >= since, Order.status.in_(_LIVE))
        .order_by(Order.created_at)
    )
    for pid, qty in rows.all():
        if pid:
            history[pid] = Decimal(qty)

    out: list[Suggestion] = []
    seen = set(in_cart)

    def add(s: Suggestion) -> None:
        if s.product.id not in seen:
            seen.add(s.product.id)
            out.append(s)

    for g in view.groups:
        seller_products = [
            p
            for p, _ in (await session.execute(_sellable().where(Product.seller_id == g.seller.id))).all()
            if p.id not in in_cart
        ]
        prices = await load_price_book(session, actor.org.id, [p.id for p in seller_products], today)

        # 1. Close the gap to the minimum order or to free delivery
        free_from = g.profile.free_delivery_from_amd if g.profile else None
        if g.missing_amd > 0:
            kind, gap = "fill_min", g.missing_amd
        elif free_from and g.totals.delivery_fee_amd > 0 and g.totals.subtotal_amd < free_from:
            kind, gap = "fill_free_delivery", free_from - g.totals.subtotal_amd
        else:
            kind, gap = None, 0
        goods = [p for p in seller_products if not p.is_service]
        if kind:
            popular = await _popularity(session, [p.id for p in goods], since)
            by_id = {p.id: p for p in goods}
            unit = {p.id: prices.price(p, Decimal(p.min_qty)).amount_amd for p in goods}
            ranked = rules.rank_fillers(
                [
                    rules.Candidate(
                        p.id, int(unit[p.id] * Decimal(p.min_qty)), p.id in history, popular.get(p.id, 0)
                    )
                    for p in goods
                ],
                gap,
            )
            for c in ranked:
                p = by_id[c.product_id]
                add(Suggestion(kind, g.seller, p, unit[p.id], Decimal(p.min_qty), gap_amd=gap))

        # 2. Volume prices just above the quantity in the cart
        tiers = await load_price_book(session, actor.org.id, [li.product.id for li in g.lines], today)
        for li in g.lines:
            if li.unit_price.source not in (PriceSource.list, PriceSource.tier):
                continue  # contract or agreed prices already beat the volume price
            step = rules.next_tier(
                Decimal(li.item.qty),
                li.unit_price.amount_amd,
                tiers.tiers.get(li.product.id, []),
            )
            if step:
                out.append(
                    Suggestion(
                        "tier", g.seller, li.product, step.price_amd, step.min_qty, saving_amd=step.saving_amd
                    )
                )

        # 3. The seller's paid extras
        for p in seller_products:
            if p.is_service:
                add(
                    Suggestion(
                        "service", g.seller, p, prices.price(p, Decimal(1)).amount_amd, Decimal(p.min_qty)
                    )
                )

    # 4. What the venue usually buys
    if history:
        rows = (
            await session.execute(
                _sellable().where(
                    Product.id.in_(list(history)),
                    Product.is_service.is_(False),
                    Product.seller_id != actor.org.id,
                )
            )
        ).all()
        cart_sellers = {g.seller.id for g in view.groups}
        rows.sort(key=lambda r: (r[1].id not in cart_sellers,))
        prices = await load_price_book(session, actor.org.id, [p.id for p, _ in rows], today)
        for p, seller in rows[: MAX_USUAL * 2]:
            if len([s for s in out if s.kind == "usual"]) >= MAX_USUAL:
                break
            qty = max(history[p.id], Decimal(p.min_qty))
            add(Suggestion("usual", seller, p, prices.price(p, qty).amount_amd, qty, last_qty=history[p.id]))

    # 5. Goes with the order: related categories, from sellers delivering to this district
    slugs = {
        s
        for s in await session.scalars(
            select(Category.slug).where(
                Category.id.in_(
                    [li.product.category_id for g in view.groups for li in g.lines if li.product.category_id]
                )
            )
        )
    }
    wanted = rules.complement_categories(slugs)[:3]
    if wanted:
        stmt = (
            _sellable()
            .join(Category, Category.id == Product.category_id)
            .where(
                Category.slug.in_(wanted),
                Product.is_service.is_(False),
                Product.seller_id != actor.org.id,
            )
            .options(selectinload(Product.tiers))
        )
        district = view.address.district if view.address else None
        if district:
            stmt = stmt.where(
                select(DeliveryZone.id)
                .where(DeliveryZone.seller_id == Product.seller_id, DeliveryZone.district == district)
                .exists()
            )
        rows = (await session.execute(stmt.add_columns(Category.slug))).all()
        popular = await _popularity(session, [p.id for p, _, _ in rows], since)
        rows.sort(key=lambda r: (wanted.index(r[2]), -popular.get(r[0].id, 0)))
        prices = await load_price_book(session, actor.org.id, [p.id for p, _, _ in rows], today)
        per_category: dict[str, int] = {}
        for p, seller, slug in rows:
            if len([s for s in out if s.kind == "complement"]) >= MAX_COMPLEMENT:
                break
            if per_category.get(slug, 0) >= 2:
                continue
            if p.id in seen:
                continue
            per_category[slug] = per_category.get(slug, 0) + 1
            add(
                Suggestion(
                    "complement",
                    seller,
                    p,
                    prices.price(p, Decimal(p.min_qty)).amount_amd,
                    Decimal(p.min_qty),
                )
            )
    return out
