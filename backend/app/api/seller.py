"""Seller cabinet API: products and delivery terms. Acts in seller mode whatever the app's current mode is."""

import uuid
from datetime import time
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel

from app.auth.deps import CurrentActor, Session
from app.models import OfferRule, Product, Unit
from app.platform.clock import utcnow
from app.schemas import ORM, TierOut
from app.services import seller_catalog as svc

router = APIRouter(prefix="/seller", tags=["seller"])


class TierIn(BaseModel):
    min_qty: Decimal
    price_amd: int


class AutopilotIO(BaseModel):
    enabled: bool = True
    floor_price_amd: int | None = None
    accept_price_amd: int | None = None
    auto_counter: bool = True
    min_line_amd: int | None = None


class ProductIn(BaseModel):
    name: dict[str, str]
    unit: Unit
    base_price_amd: int
    category_id: uuid.UUID | None = None
    sku: str | None = None
    description: dict[str, str] | None = None
    pack_size: str | None = None
    vat_included: bool = True
    min_qty: Decimal = Decimal(1)
    qty_step: Decimal = Decimal(1)
    in_stock: bool = True
    allow_offers: bool = False
    tiers: list[TierIn] = []
    autopilot: AutopilotIO | None = None


class SellerProductOut(ORM):
    id: uuid.UUID
    sku: str | None
    category_id: uuid.UUID | None
    name: dict[str, str]
    description: dict[str, str] | None
    unit: Unit
    pack_size: str | None
    base_price_amd: int
    vat_included: bool
    vat_rate_bp: int
    min_qty: Decimal
    qty_step: Decimal
    in_stock: bool
    allow_offers: bool
    archived: bool
    tiers: list[TierOut]
    autopilot: AutopilotIO | None


class ZoneIO(BaseModel):
    district: str
    weekdays: list[int]


class SettingsIO(BaseModel):
    min_order_amd: int = 0
    cutoff_time: time = time(16, 0)
    lead_days: int = 1
    delivery_fee_amd: int = 0
    free_delivery_from_amd: int | None = None
    offer_response_hours: int = 24
    zones: list[ZoneIO] = []


def _out(p: Product, rule: OfferRule | None) -> SellerProductOut:
    return SellerProductOut(
        id=p.id,
        sku=p.sku,
        category_id=p.category_id,
        name=p.name,
        description=p.description,
        unit=p.unit,
        pack_size=p.pack_size,
        base_price_amd=p.base_price_amd,
        vat_included=p.vat_included,
        vat_rate_bp=p.vat_rate_bp,
        min_qty=p.min_qty,
        qty_step=p.qty_step,
        in_stock=p.in_stock,
        allow_offers=p.allow_offers,
        archived=p.archived_at is not None,
        tiers=[
            TierOut(min_qty=t.min_qty, price_amd=t.price_amd)
            for t in sorted(p.tiers, key=lambda t: t.min_qty)
        ],
        autopilot=AutopilotIO(
            enabled=rule.enabled,
            floor_price_amd=rule.floor_price_amd,
            accept_price_amd=rule.auto_accept_price_amd,
            auto_counter=rule.auto_counter,
            min_line_amd=rule.min_line_amd,
        )
        if rule
        else None,
    )


def _data(body: ProductIn) -> svc.ProductIn:
    return svc.ProductIn(
        **body.model_dump(exclude={"tiers", "autopilot"}),
        tiers=[svc.TierIn(t.min_qty, t.price_amd) for t in body.tiers],
        autopilot=svc.AutopilotIn(**body.autopilot.model_dump()) if body.autopilot else None,
    )


async def _reload(session: Session, actor: CurrentActor, product_id: uuid.UUID) -> SellerProductOut:
    for p, rule in await svc.list_own(session, actor) + await svc.list_own(session, actor, archived=True):
        if p.id == product_id:
            await session.refresh(p, ["tiers"])
            return _out(p, rule)
    raise AssertionError("product vanished")


@router.get("/products", response_model=list[SellerProductOut])
async def list_products(session: Session, actor: CurrentActor, archived: bool = False):
    return [_out(p, r) for p, r in await svc.list_own(session, actor, archived)]


@router.post("/products", response_model=SellerProductOut, status_code=201)
async def create_product(body: ProductIn, session: Session, actor: CurrentActor):
    product = await svc.create(session, actor, _data(body))
    await session.commit()
    return await _reload(session, actor, product.id)


@router.put("/products/{product_id}", response_model=SellerProductOut)
async def update_product(product_id: uuid.UUID, body: ProductIn, session: Session, actor: CurrentActor):
    await svc.update(session, actor, product_id, _data(body))
    await session.commit()
    return await _reload(session, actor, product_id)


@router.post("/products/{product_id}/archive", response_model=SellerProductOut)
async def archive_product(product_id: uuid.UUID, session: Session, actor: CurrentActor):
    await svc.set_archived(session, actor, product_id, True, utcnow())
    await session.commit()
    return await _reload(session, actor, product_id)


@router.post("/products/{product_id}/restore", response_model=SellerProductOut)
async def restore_product(product_id: uuid.UUID, session: Session, actor: CurrentActor):
    await svc.set_archived(session, actor, product_id, False, utcnow())
    await session.commit()
    return await _reload(session, actor, product_id)


@router.get("/settings", response_model=SettingsIO)
async def get_settings(session: Session, actor: CurrentActor):
    profile, zones = await svc.get_settings_for(session, actor)
    await session.commit()
    return _settings_out(profile, zones)


@router.put("/settings", response_model=SettingsIO)
async def put_settings(body: SettingsIO, session: Session, actor: CurrentActor):
    data = svc.SettingsIn(
        **body.model_dump(exclude={"zones"}), zones=[svc.ZoneIn(z.district, z.weekdays) for z in body.zones]
    )
    profile, zones = await svc.save_settings(session, actor, data)
    await session.commit()
    return _settings_out(profile, zones)


def _settings_out(profile, zones) -> SettingsIO:
    return SettingsIO(
        min_order_amd=profile.min_order_amd,
        cutoff_time=profile.cutoff_time,
        lead_days=profile.lead_days,
        delivery_fee_amd=profile.delivery_fee_amd,
        free_delivery_from_amd=profile.free_delivery_from_amd,
        offer_response_hours=profile.offer_response_hours,
        zones=[ZoneIO(district=z.district, weekdays=z.weekdays) for z in zones],
    )
