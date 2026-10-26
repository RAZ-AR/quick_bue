"""Delivery addresses of the buyer's company (several, each with a receiver)."""

import uuid

from fastapi import APIRouter, Response

from app.auth.deps import CurrentActor, Session
from app.models import Address
from app.platform.clock import utcnow
from app.schemas import AddressIn, AddressOut
from app.services import addresses as svc

router = APIRouter(tags=["addresses"])


@router.get("/addresses", response_model=list[AddressOut])
async def list_addresses(session: Session, actor: CurrentActor) -> list[Address]:
    return await svc.list_for(session, actor)


@router.post("/addresses", response_model=AddressOut, status_code=201)
async def add_address(body: AddressIn, session: Session, actor: CurrentActor) -> Address:
    address = await svc.create(session, actor, svc.AddressIn(**body.model_dump()))
    await session.commit()
    return address


@router.put("/addresses/{address_id}", response_model=AddressOut)
async def edit_address(
    address_id: uuid.UUID, body: AddressIn, session: Session, actor: CurrentActor
) -> Address:
    address = await svc.update(session, actor, address_id, svc.AddressIn(**body.model_dump()))
    await session.commit()
    return address


@router.delete("/addresses/{address_id}", status_code=204)
async def remove_address(address_id: uuid.UUID, session: Session, actor: CurrentActor) -> Response:
    await svc.archive(session, actor, address_id, utcnow())
    await session.commit()
    return Response(status_code=204)
