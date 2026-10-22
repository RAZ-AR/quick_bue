"""Public catalog. Guests see products and prices but not who sells them (docs/05-cabinets-and-auth.md)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.auth.deps import OptionalUser, Session
from app.models import Category, Organization, OrgStatus, Product, VerificationStatus
from app.schemas import CategoryOut, ProductOut, ProductPage, SellerBrief

router = APIRouter(tags=["catalog"])


@router.get("/categories", response_model=list[CategoryOut])
async def categories(session: Session) -> list[Category]:
    rows = await session.scalars(select(Category).order_by(Category.sort, Category.slug))
    return list(rows)


@router.get("/products", response_model=ProductPage)
async def products(
    session: Session,
    user: OptionalUser,
    q: Annotated[str | None, Query(max_length=100)] = None,
    category_id: uuid.UUID | None = None,
    seller_id: uuid.UUID | None = None,
    ids: Annotated[list[uuid.UUID] | None, Query(max_length=200)] = None,
    offers_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProductPage:
    guest = user is None
    stmt = (
        select(Product, Organization)
        .join(Organization, Organization.id == Product.seller_id)
        .where(
            Organization.is_seller.is_(True),
            Organization.verification_status == VerificationStatus.verified,
            Organization.status != OrgStatus.blocked,
            Product.archived_at.is_(None),
        )
    )
    own = [m.organization_id for m in user.memberships] if user else []
    if own:  # a company that also sells does not buy from itself
        stmt = stmt.where(Product.seller_id.not_in(own))
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if seller_id and not guest:  # guests cannot browse a seller they cannot see
        stmt = stmt.where(Product.seller_id == seller_id)
    if ids:
        stmt = stmt.where(Product.id.in_(ids))
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
    items = [_product_out(p, None if guest else org) for p, org in rows.all()]
    return ProductPage(items=items, total=total or 0, guest=guest)


def _product_out(p: Product, org: Organization | None) -> ProductOut:
    return ProductOut(
        id=p.id,
        seller=SellerBrief(id=org.id, display_name=org.display_name) if org else None,
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
