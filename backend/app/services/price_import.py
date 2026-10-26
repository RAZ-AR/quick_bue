"""Price list import into the seller's own catalog (docs/07-roadmap.md, stage 1).

Stateless: the client sends the parsed rows and the column mapping twice — for the preview and to apply.
The plan is rebuilt on apply, so what is written is always checked against the current catalog.
Rows with problems are skipped; everything else is written in the caller's transaction.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.search import build_search_text
from app.domain import price_import as dom
from app.models import Product, TaxRegime, Unit
from app.platform.authz import Actor
from app.platform.errors import ValidationFailed
from app.services.seller_catalog import _seller


@dataclass
class ImportIn:
    mapping: dict[int, dom.Field]
    rows: list[list[object]]
    default_unit: Unit | None = None
    missing_out_of_stock: bool = False


def _check_mapping(data: ImportIn) -> None:
    fields = list(data.mapping.values())
    problems = []
    if len(fields) != len(set(fields)):
        problems.append({"field": "mapping", "code": "duplicate_mapping"})
    if dom.Field.sku not in fields and not any(f in dom.NAME_FIELDS for f in fields):
        problems.append({"field": "mapping", "code": "map_sku_or_name"})
    if len(data.rows) > dom.MAX_ROWS:
        problems.append({"field": "rows", "code": "too_many_rows"})
    if problems:
        raise ValidationFailed(problems)


async def _products(session: AsyncSession, seller_id: uuid.UUID) -> dict[uuid.UUID, Product]:
    rows = await session.scalars(
        select(Product).where(Product.seller_id == seller_id).options(selectinload(Product.tiers))
    )
    return {p.id: p for p in rows}


def _existing(p: Product) -> dom.Existing:
    return dom.Existing(
        id=p.id,
        sku=p.sku,
        name=dict(p.name),
        price_amd=p.base_price_amd,
        unit=p.unit,
        in_stock=p.in_stock,
        min_qty=p.min_qty,
        pack_size=p.pack_size,
        archived=p.archived_at is not None,
        top_tier_price_amd=max((t.price_amd for t in p.tiers), default=None),
    )


async def _plan(
    session: AsyncSession, actor: Actor, data: ImportIn
) -> tuple[list[dom.Item], dict[uuid.UUID, Product]]:
    _check_mapping(data)
    products = await _products(session, actor.org.id)
    rows = [
        row
        for i, cells in enumerate(data.rows)
        if (row := dom.read_row(i + 2, cells, data.mapping)) is not None  # line 1 is the header
    ]
    items = dom.plan(
        rows,
        [_existing(p) for p in products.values()],
        default_unit=data.default_unit,
        missing_out_of_stock=data.missing_out_of_stock,
    )
    return items, products


async def preview(session: AsyncSession, actor: Actor, data: ImportIn) -> list[dom.Item]:
    actor = _seller(actor)
    items, _ = await _plan(session, actor, data)
    return items


async def apply(session: AsyncSession, actor: Actor, data: ImportIn) -> list[dom.Item]:
    actor = _seller(actor)
    items, products = await _plan(session, actor, data)
    vat_rate = 2000 if actor.org.tax_regime == TaxRegime.vat else 0
    for item in items:
        if item.action == dom.Action.create and item.row is not None:
            r = item.row
            product = Product(
                seller_id=actor.org.id,
                sku=r.sku,
                name=r.name,
                unit=r.unit or data.default_unit,
                base_price_amd=r.price_amd,
                in_stock=True if r.in_stock is None else r.in_stock,
                min_qty=r.min_qty or 1,
                qty_step=1,
                pack_size=r.pack_size,
                vat_included=True,
                vat_rate_bp=vat_rate,
                allow_offers=False,
                images=[],
                search_text=build_search_text(r.name),
            )
            session.add(product)
            await session.flush()
            item.product_id = product.id
        elif item.action in (dom.Action.update, dom.Action.out_of_stock) and item.product_id:
            product = products[item.product_id]
            for c in item.changes:
                if c.field == "price_amd":
                    product.base_price_amd = c.new
                elif c.field == "name":
                    product.name = c.new
                    product.search_text = build_search_text(c.new)
                elif c.field == "archived":
                    product.archived_at = None
                else:
                    setattr(product, c.field, c.new)
    await session.flush()
    return items
