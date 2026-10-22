"""Buyer cart: one cart per buyer organization, grouped by seller at read time.

`build_cart` is the single source of truth for prices and problems: the cart screen shows what it returns,
and checkout refuses to proceed while it reports any problem.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import negotiation as neg
from app.domain.orders import LineAmount, Totals, compute_totals, delivery_date, is_valid_qty
from app.domain.pricing import UnitPrice, line_total_amd
from app.models import (
    Address,
    CartItem,
    DeliveryZone,
    Organization,
    OrgStatus,
    Product,
    SellerProfile,
)
from app.platform.authz import Action, Actor
from app.platform.clock import local
from app.platform.errors import NotFound, ValidationFailed
from app.services.prices import PriceBook, RuleBook, load_price_book, load_rule_book


@dataclass
class CartLine:
    item: CartItem
    product: Product
    unit_price: UnitPrice
    line_total_amd: int
    offer_min_line_amd: int
    problems: list[str] = field(default_factory=list)


@dataclass
class CartGroup:
    seller: Organization
    profile: SellerProfile | None
    lines: list[CartLine]
    totals: Totals  # at current prices, before any offer is answered
    delivery_date: date | None
    problems: list[str] = field(default_factory=list)
    missing_amd: int = 0  # how much is missing up to the seller's minimum order
    rules: RuleBook | None = None


@dataclass
class CartView:
    groups: list[CartGroup]
    address: Address | None

    @property
    def problems(self) -> list[dict]:
        out: list[dict] = []
        for g in self.groups:
            out += [{"seller_id": str(g.seller.id), "code": c} for c in g.problems]
            for li in g.lines:
                out += [{"product_id": str(li.product.id), "code": c} for c in li.problems]
        return out

    @property
    def total_amd(self) -> int:
        return sum(g.totals.total_amd for g in self.groups)


async def _buyer_address(session: AsyncSession, actor: Actor, address_id: uuid.UUID | None) -> Address | None:
    stmt = select(Address).where(Address.organization_id == actor.org.id)
    if address_id:
        address = await session.scalar(stmt.where(Address.id == address_id))
        if address is None:
            raise NotFound("address_not_found")
        return address
    return await session.scalar(stmt.order_by(Address.created_at).limit(1))


async def build_cart(
    session: AsyncSession,
    actor: Actor,
    now: datetime,
    address_id: uuid.UUID | None = None,
    lock: bool = False,
) -> CartView:
    stmt = select(CartItem).where(CartItem.buyer_id == actor.org.id).order_by(CartItem.created_at)
    if lock:
        stmt = stmt.with_for_update()
    items = list(await session.scalars(stmt))
    address = await _buyer_address(session, actor, address_id)
    if not items:
        return CartView([], address)

    products = {
        p.id: p
        for p in await session.scalars(select(Product).where(Product.id.in_([i.product_id for i in items])))
    }
    seller_ids = {p.seller_id for p in products.values()}
    sellers = {
        o.id: o for o in await session.scalars(select(Organization).where(Organization.id.in_(seller_ids)))
    }
    profiles = {
        sp.organization_id: sp
        for sp in await session.scalars(
            select(SellerProfile).where(SellerProfile.organization_id.in_(seller_ids))
        )
    }
    zones: dict[uuid.UUID, list[DeliveryZone]] = {}
    for z in await session.scalars(select(DeliveryZone).where(DeliveryZone.seller_id.in_(seller_ids))):
        zones.setdefault(z.seller_id, []).append(z)

    today = local(now).date()
    prices: PriceBook = await load_price_book(session, actor.org.id, list(products), today)
    can_offer = actor.can(Action.offer_make)

    by_seller: dict[uuid.UUID, list[CartItem]] = {}
    for item in items:
        by_seller.setdefault(products[item.product_id].seller_id, []).append(item)

    groups: list[CartGroup] = []
    for seller_id, seller_items in by_seller.items():
        seller, profile = sellers[seller_id], profiles.get(seller_id)
        rules = await load_rule_book(session, seller_id)
        lines: list[CartLine] = []
        for item in seller_items:
            product = products[item.product_id]
            qty = Decimal(item.qty)
            unit = prices.price(product, qty)
            line = CartLine(
                item, product, unit, line_total_amd(unit.amount_amd, qty), rules.min_line_amd(product)
            )
            if product.archived_at is not None:
                line.problems.append("product_archived")
            elif not product.in_stock:
                line.problems.append("out_of_stock")
            if not is_valid_qty(qty, Decimal(product.min_qty), Decimal(product.qty_step)):
                line.problems.append("bad_qty")
            if item.offer_price_amd is not None:
                if not can_offer:
                    line.problems.append("not_allowed_to_negotiate")
                elif not product.allow_offers:
                    line.problems.append("offers_not_allowed")
                elif problem := neg.check_buyer_price(
                    item.offer_price_amd, unit.amount_amd, qty, line.offer_min_line_amd
                ):
                    line.problems.append(problem)
            lines.append(line)

        totals = compute_totals(
            [LineAmount(Decimal(li.item.qty), li.unit_price.amount_amd) for li in lines],
            delivery_fee_amd=profile.delivery_fee_amd if profile else 0,
            free_delivery_from_amd=profile.free_delivery_from_amd if profile else None,
        )
        group = CartGroup(seller, profile, lines, totals, None, rules=rules)
        if seller.status != OrgStatus.active:
            group.problems.append("seller_unavailable")
        min_order = profile.min_order_amd if profile else 0
        if totals.subtotal_amd < min_order:
            group.problems.append("min_order_not_reached")
            group.missing_amd = min_order - totals.subtotal_amd

        seller_zones = zones.get(seller_id, [])
        weekdays: set[int] | None = None
        if seller_zones:
            district = address.district if address else None
            matching = [z for z in seller_zones if district is None or z.district == district]
            if not matching:
                group.problems.append("no_delivery_to_district")
            weekdays = {d for z in (matching or seller_zones) for d in z.weekdays}
        if profile:
            group.delivery_date = delivery_date(local(now), profile.cutoff_time, profile.lead_days, weekdays)
        groups.append(group)
    return CartView(groups, address)


async def set_item(
    session: AsyncSession,
    actor: Actor,
    product_id: uuid.UUID,
    qty: Decimal,
    offer_price_amd: int | None = None,
    note: str | None = None,
) -> None:
    """Put a product in the cart (qty 0 removes it). Prices and offers are checked when the cart is read."""
    actor.require(Action.cart_edit)
    if qty <= 0:
        await remove_item(session, actor, product_id)
        return
    product = await session.get(Product, product_id)
    if product is None or product.archived_at is not None:
        raise NotFound("product_not_found")
    if offer_price_amd is not None and not actor.can(Action.offer_make):
        raise ValidationFailed([{"product_id": str(product_id), "code": "not_allowed_to_negotiate"}])
    item = await session.scalar(
        select(CartItem).where(CartItem.buyer_id == actor.org.id, CartItem.product_id == product_id)
    )
    if item is None:
        item = CartItem(buyer_id=actor.org.id, product_id=product_id, user_id=actor.user.id, qty=qty)
        session.add(item)
    item.qty = qty
    item.offer_price_amd = offer_price_amd
    item.note = note
    item.user_id = actor.user.id


async def remove_item(session: AsyncSession, actor: Actor, product_id: uuid.UUID) -> None:
    actor.require(Action.cart_edit)
    await session.execute(
        delete(CartItem).where(CartItem.buyer_id == actor.org.id, CartItem.product_id == product_id)
    )


async def clear(session: AsyncSession, actor: Actor) -> None:
    actor.require(Action.cart_edit)
    await session.execute(delete(CartItem).where(CartItem.buyer_id == actor.org.id))
