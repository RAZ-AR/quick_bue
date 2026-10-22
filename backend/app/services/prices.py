"""Loads what price resolution and the autopilot need: tiers, active contract prices, seller offer rules."""

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.domain.negotiation import AutoRule
from app.domain.pricing import Tier, UnitPrice, resolve_unit_price
from app.models import (
    AgreementStatus,
    ClientLink,
    OfferRule,
    PriceAgreement,
    PriceTier,
    Product,
    RuleScope,
)


@dataclass
class PriceBook:
    tiers: dict[uuid.UUID, list[Tier]] = field(default_factory=dict)
    agreements: dict[uuid.UUID, int] = field(default_factory=dict)  # product_id -> contract unit price

    def price(self, product: Product, qty: Decimal, negotiated: int | None = None) -> UnitPrice:
        return resolve_unit_price(
            product.base_price_amd,
            qty,
            self.tiers.get(product.id, []),
            agreement_price_amd=self.agreements.get(product.id),
            negotiated_price_amd=negotiated,
        )


async def load_price_book(
    session: AsyncSession, buyer_id: uuid.UUID, product_ids: list[uuid.UUID], today: date
) -> PriceBook:
    book = PriceBook()
    if not product_ids:
        return book
    for t in await session.scalars(select(PriceTier).where(PriceTier.product_id.in_(product_ids))):
        book.tiers.setdefault(t.product_id, []).append(Tier(Decimal(t.min_qty), t.price_amd))
    rows = await session.execute(
        select(PriceAgreement.product_id, PriceAgreement.price_amd)
        .join(ClientLink, ClientLink.id == PriceAgreement.client_link_id)
        .where(
            ClientLink.buyer_id == buyer_id,
            PriceAgreement.product_id.in_(product_ids),
            PriceAgreement.status == AgreementStatus.active,
            PriceAgreement.valid_from <= today,
            PriceAgreement.valid_until >= today,
        )
        .order_by(PriceAgreement.created_at)  # the newest wins
    )
    for product_id, price in rows:
        book.agreements[product_id] = price
    return book


@dataclass
class RuleBook:
    """Seller autopilot rules; the most specific one applies: product > category > seller."""

    by_product: dict[uuid.UUID, OfferRule] = field(default_factory=dict)
    by_category: dict[uuid.UUID, OfferRule] = field(default_factory=dict)
    seller_wide: OfferRule | None = None

    def rule_for(self, product: Product) -> OfferRule | None:
        return (
            self.by_product.get(product.id)
            or (self.by_category.get(product.category_id) if product.category_id else None)
            or self.seller_wide
        )

    def min_line_amd(self, product: Product) -> int:
        rule = self.rule_for(product)
        if rule is not None and rule.min_line_amd is not None:
            return rule.min_line_amd
        return get_settings().offer_min_line_amd

    def auto_rule(self, product: Product) -> AutoRule | None:
        r = self.rule_for(product)
        if r is None or not r.enabled:
            return None
        return AutoRule(
            floor_price_amd=r.floor_price_amd if r.scope == RuleScope.product else None,
            floor_pct_bp=r.floor_pct_bp,
            accept_price_amd=r.auto_accept_price_amd if r.scope == RuleScope.product else None,
            accept_pct_bp=r.auto_accept_pct_bp,
            auto_counter=r.auto_counter,
            only_regulars=r.only_regulars,
            min_qty=Decimal(r.min_qty) if r.min_qty is not None else None,
            min_line_amd=r.min_line_amd,
        )


async def load_rule_book(session: AsyncSession, seller_id: uuid.UUID) -> RuleBook:
    book = RuleBook()
    for r in await session.scalars(select(OfferRule).where(OfferRule.seller_id == seller_id)):
        if r.scope == RuleScope.product and r.scope_id:
            book.by_product[r.scope_id] = r
        elif r.scope == RuleScope.category and r.scope_id:
            book.by_category[r.scope_id] = r
        elif r.scope == RuleScope.seller:
            book.seller_wide = r
    return book
