"""Address check: a typed address -> the house and its district (integrations/geocoder.py)."""

from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.auth.deps import CurrentUser
from app.config import get_settings
from app.integrations.geocoder import GeocoderUnavailable, NominatimGeocoder
from app.integrations.registry import shared_redis
from app.platform import ratelimit
from app.platform.errors import TooManyRequests

router = APIRouter(tags=["geo"])


class PlaceOut(BaseModel):
    found: bool
    unavailable: bool = False  # the map service did not answer: keep the address as typed
    text: str | None = None
    street: str | None = None
    house: str | None = None
    district: str | None = None
    lat: float | None = None
    lng: float | None = None


@router.get("/geo/resolve", response_model=PlaceOut)
async def resolve(
    user: CurrentUser,
    q: Annotated[str, Query(min_length=3, max_length=200)],
    lang: Literal["hy", "ru", "en"] = "hy",
) -> PlaceOut:
    if not get_settings().geocoder_url:
        return PlaceOut(found=False, unavailable=True)
    if not await ratelimit.hit(f"geo:{user.id}", limit=30, window_s=60):
        raise TooManyRequests("too_many_requests", "too many address checks, wait a minute")
    try:
        place = await NominatimGeocoder(get_settings().geocoder_url, shared_redis()).resolve(q, lang)
    except GeocoderUnavailable:
        return PlaceOut(found=False, unavailable=True)
    if place is None:
        return PlaceOut(found=False)
    return PlaceOut(found=True, **place.__dict__)
