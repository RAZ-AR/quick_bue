"""Public catalog. Guests see products and prices but not who sells them (docs/05-cabinets-and-auth.md)."""

import re
import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.auth.deps import CurrentUser, OptionalUser, Session
from app.domain import product_specs
from app.models import (
    Category,
    Organization,
    OrgStatus,
    Product,
    ProductDocument,
    SellerProfile,
    VerificationStatus,
)
from app.platform import storage
from app.platform.errors import NotFound
from app.schemas import (
    CategoryOut,
    ImageOut,
    ProductDetailOut,
    ProductDocOut,
    ProductOut,
    ProductPage,
    SellerBrief,
)
from app.services.product_media import image_urls

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
    # Services are offered in the cart, not listed in the catalog (asking by id still finds them)
    stmt = stmt.where(Product.id.in_(ids)) if ids else stmt.where(Product.is_service.is_(False))
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
        stmt.options(selectinload(Product.tiers), selectinload(Product.documents))
        .order_by(*order)
        .limit(limit)
        .offset(offset)
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
        images=[ImageOut(**i) for i in image_urls(p)],
        tiers=p.tiers,
        has_documents=bool(p.documents),
    )


def _visible():
    """What anyone may open: live products of verified, not blocked sellers."""
    return (
        select(Product, Organization)
        .join(Organization, Organization.id == Product.seller_id)
        .where(
            Organization.is_seller.is_(True),
            Organization.verification_status == VerificationStatus.verified,
            Organization.status != OrgStatus.blocked,
            Product.archived_at.is_(None),
        )
        .options(selectinload(Product.tiers), selectinload(Product.documents))
    )


@router.get("/products/{product_id}", response_model=ProductDetailOut)
async def product_card(product_id: uuid.UUID, session: Session, user: OptionalUser) -> ProductDetailOut:
    row = (await session.execute(_visible().where(Product.id == product_id))).first()
    if row is None:
        raise NotFound("product_not_found")
    p, org = row
    guest = user is None
    category = await session.get(Category, p.category_id) if p.category_id else None
    profile = None if guest else await session.get(SellerProfile, org.id)
    base = _product_out(p, None if guest else org)
    return ProductDetailOut(
        **base.model_dump(),
        description=p.description,
        category=category.slug if category else None,
        specs=p.specs or {},
        documents=[
            ProductDocOut(id=d.id, kind=d.kind, number=d.number, valid_until=d.valid_until)
            for d in p.documents
        ],
        is_service=p.is_service,
        vat_rate_bp=p.vat_rate_bp,
        seller_min_order_amd=profile.min_order_amd if profile else None,
        seller_lead_days=profile.lead_days if profile else None,
    )


@router.get("/products/{product_id}/documents/{doc_id}")
async def product_document(product_id: uuid.UUID, doc_id: uuid.UUID, session: Session, _: CurrentUser):
    """Certificates open for signed-in users only; guests see that they exist."""
    if (await session.execute(_visible().where(Product.id == product_id))).first() is None:
        raise NotFound("product_not_found")
    doc = await session.get(ProductDocument, doc_id)
    if doc is None or doc.product_id != product_id:
        raise NotFound("document_not_found")
    return FileResponse(
        storage.path_of(doc.storage_key), media_type=doc.content_type, filename=doc.original_name
    )


_IMAGE = re.compile(r"^[0-9a-f]{32}(-s)?\.webp$")


@router.get("/media/products/{product_id}/{name}")
async def product_image(product_id: uuid.UUID, name: str):
    """Product photos are public (names are random and never reused, so they cache for a year)."""
    if not _IMAGE.match(name):
        raise NotFound("image_not_found")
    path = storage.path_of(f"products/{product_id}/{name}")
    if not path.exists():
        raise NotFound("image_not_found")
    return FileResponse(
        path, media_type="image/webp", headers={"Cache-Control": "public, max-age=31536000, immutable"}
    )


@router.get("/product-specs")
async def spec_definitions() -> dict:
    """Characteristics by category and document kinds, labels in three languages (for forms and cards)."""
    return {
        "groups": product_specs.GROUPS,
        "specs": [
            {
                "code": s.code,
                "kind": s.kind,
                "label": s.label,
                "group": s.group,
                "unit": s.unit,
                "options": s.options,
                "categories": list(s.categories),
            }
            for s in product_specs.SPECS
        ],
        "doc_kinds": product_specs.DOC_LABELS,
    }
