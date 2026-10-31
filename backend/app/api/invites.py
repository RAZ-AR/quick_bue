"""Supplier links: the public page /s/<code>, its QR, joining as a client, and the seller's side of it.

The page names the seller even to guests: the seller shared the link to be found
(the catalog itself still hides sellers from guests, docs/05-cabinets-and-auth.md).
"""

import io
import uuid
from datetime import datetime, time

import segno
from fastapi import APIRouter, Response
from pydantic import BaseModel
from sqlalchemy import func, select

from app.auth.deps import CurrentActor, OptionalUser, Session
from app.config import get_settings
from app.models import (
    ClientSource,
    DeliveryZone,
    OrgKind,
    Product,
    SellerProfile,
    VerificationStatus,
)
from app.platform.authz import Action
from app.platform.errors import NotFound
from app.services import invites

router = APIRouter(tags=["invites"])


class SupplierPageOut(BaseModel):
    code: str
    seller_id: uuid.UUID
    display_name: str
    description: dict[str, str] | None
    verified: bool  # not yet: the page opens, but nothing can be ordered
    products: int
    category_ids: list[uuid.UUID]
    min_order_amd: int
    delivery_fee_amd: int
    free_delivery_from_amd: int | None
    lead_days: int
    cutoff_time: time
    districts: list[str]
    client: bool | None  # None for guests


class JoinOut(BaseModel):
    status: invites.JoinResult
    seller_id: uuid.UUID
    display_name: str


class InviteOut(BaseModel):
    code: str
    url: str
    invited_clients: int


class ClientOut(BaseModel):
    buyer_id: uuid.UUID
    display_name: str
    source: ClientSource
    since: datetime
    orders: int
    last_order_at: datetime | None


def _url(code: str) -> str:
    return f"{get_settings().web_app_url.rstrip('/')}/s/{code}"


async def _resolve(session, code: str):
    found = await invites.resolve(session, code)
    if found is None:
        raise NotFound("invite_not_found")
    return found


@router.get("/s/{code}", response_model=SupplierPageOut)
async def supplier_page(code: str, session: Session, user: OptionalUser) -> SupplierPageOut:
    invite, seller = await _resolve(session, code)
    profile = await session.get(SellerProfile, seller.id)
    live = (
        Product.seller_id == seller.id,
        Product.archived_at.is_(None),
        Product.is_service.is_(False),
    )
    count = await session.scalar(select(func.count(Product.id)).where(*live)) or 0
    categories = await session.scalars(
        select(Product.category_id).where(*live, Product.category_id.is_not(None)).distinct()
    )
    zones = await session.scalars(
        select(DeliveryZone.district)
        .where(DeliveryZone.seller_id == seller.id)
        .order_by(DeliveryZone.district)
    )
    client = None
    if user is not None:
        client = await invites.client_of(session, seller.id, [m.organization_id for m in user.memberships])
    verified = seller.verification_status == VerificationStatus.verified
    return SupplierPageOut(
        code=invite.code,
        seller_id=seller.id,
        display_name=seller.display_name,
        description=profile.description if profile else None,
        verified=verified,
        products=count if verified else 0,
        category_ids=list(categories) if verified else [],
        min_order_amd=profile.min_order_amd if profile else 0,
        delivery_fee_amd=profile.delivery_fee_amd if profile else 0,
        free_delivery_from_amd=profile.free_delivery_from_amd if profile else None,
        lead_days=profile.lead_days if profile else 1,
        cutoff_time=profile.cutoff_time if profile else time(16, 0),
        districts=list(zones),
        client=client,
    )


@router.get("/s/{code}/qr.svg")
async def supplier_qr(code: str, session: Session) -> Response:
    invite, _ = await _resolve(session, code)
    buf = io.BytesIO()
    qr = segno.make(_url(invite.code), error="m")
    qr.save(buf, kind="svg", scale=8, border=2, dark="#111", xmldecl=False)
    return Response(
        buf.getvalue(),
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.post("/s/{code}/join", response_model=JoinOut)
async def join(code: str, session: Session, actor: CurrentActor) -> JoinOut:
    # Joining is not buying yet: no registry extract needed, only a buyer company that is not blocked
    actor.with_mode(OrgKind.buyer).require(Action.cart_edit)
    _, seller = await _resolve(session, code)
    status = await invites.join(session, actor.org, code)
    await session.commit()
    return JoinOut(status=status, seller_id=seller.id, display_name=seller.display_name)


@router.get("/seller/invite", response_model=InviteOut)
async def my_invite(session: Session, actor: CurrentActor) -> InviteOut:
    invite = await invites.current(session, actor)
    count = await invites.invited_count(session, invite.seller_id)
    await session.commit()
    return InviteOut(code=invite.code, url=_url(invite.code), invited_clients=count)


@router.post("/seller/invite/rotate", response_model=InviteOut)
async def rotate_invite(session: Session, actor: CurrentActor) -> InviteOut:
    invite = await invites.rotate(session, actor)
    count = await invites.invited_count(session, invite.seller_id)
    await session.commit()
    return InviteOut(code=invite.code, url=_url(invite.code), invited_clients=count)


@router.get("/seller/clients", response_model=list[ClientOut])
async def my_clients(session: Session, actor: CurrentActor) -> list[ClientOut]:
    rows = await invites.clients(session, actor)
    return [ClientOut(**r.__dict__) for r in rows]
