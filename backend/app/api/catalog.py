import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.auth.deps import CurrentUser, Session
from app.models import Category, Organization, OrgStatus, Product
from app.schemas import CategoryOut, ProductOut, ProductPage, SellerBrief

router = APIRouter(tags=["catalog"])


@router.get("/categories", response_model=list[CategoryOut])
async def categories(session: Session, _: CurrentUser) -> list[Category]:
    rows = await session.scalars(select(Category).order_by(Category.sort, Category.slug))
    return list(rows)


@router.get("/products", response_model=ProductPage)
async def products(
    session: Session,
    _: CurrentUser,
    q: Annotated[str | None, Query(max_length=100)] = None,
    category_id: uuid.UUID | None = None,
    seller_id: uuid.UUID | None = None,
    offers_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProductPage:
    stmt = (
        select(Product, Organization)
        .join(Organization, Organization.id == Product.seller_id)
        .where(Organization.status == OrgStatus.active)
    )
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if seller_id:
        stmt = stmt.where(Product.seller_id == seller_id)
    if offers_only:
        stmt = stmt.where(Product.allow_offers.is_(True))
    order = [Product.in_stock.desc(), Product.created_at.desc()]
    if q and q.strip():
        term = q.strip().lower()
        # Substring match (pg_trgm GIN index makes ILIKE fast), best trigram similarity first
        similarity = func.similarity(Product.search_text, term)
        stmt = stmt.where(Product.search_text.ilike(f"%{term}%") | (similarity > 0.2))
        order = [similarity.desc(), *order]

    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = await session.execute(
        stmt.options(selectinload(Product.tiers)).order_by(*order).limit(limit).offset(offset)
    )
    items = [_product_out(p, org) for p, org in rows.all()]
    return ProductPage(items=items, total=total or 0)


def _product_out(p: Product, org: Organization) -> ProductOut:
    return ProductOut(
        id=p.id,
        seller=SellerBrief(id=org.id, display_name=org.display_name),
        category_id=p.category_id,
        name=p.name,
        unit=p.unit,
        pack_size=p.pack_size,
        base_price_amd=p.base_price_amd,
        vat_included=p.vat_included,
        min_qty=p.min_qty,
        qty_step=p.qty_step,
        in_stock=p.in_stock,
        allow_offers=p.allow_offers,
        images=p.images,
        tiers=p.tiers,
    )
