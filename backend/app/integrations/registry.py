"""Company data by Armenian TIN (ՀՎՀՀ) to prefill sign-up.

Armenia has no official public API for this (as of Oct 2026): the state register (e-register.moj.am)
and the SRC taxpayer search are web forms. Paid intermediaries exist (an Apify actor over the register's
open data, karg.am), but their terms and accuracy are not verified. So the registry is a port: services
call `get_registry()` and never know which provider answers. "demo" serves fictional companies,
"eregister" reads the register's public company search (integrations/eregister.py), "none" finds nothing.
"""

import dataclasses
import json
import logging
import re
from dataclasses import dataclass
from typing import Protocol

from redis import asyncio as aioredis
from redis.exceptions import RedisError

from app.config import get_settings
from app.models import TaxRegime

log = logging.getLogger(__name__)


class RegistryUnavailable(Exception):
    """The registry did not answer or sent what we cannot read: sign-up falls back to manual entry."""


TIN_RE = re.compile(r"^\d{8}$")


def normalize_tin(raw: str) -> str | None:
    tin = re.sub(r"\D", "", raw or "")
    return tin if TIN_RE.match(tin) else None


@dataclass(frozen=True)
class CompanyInfo:
    tin: str
    legal_name: str
    registration_number: str | None
    legal_address: str | None
    director_name: str | None
    tax_regime: TaxRegime | None
    active: bool = True
    source: str = "demo"


class Registry(Protocol):
    name: str

    async def lookup(self, tin: str) -> CompanyInfo | None: ...


class DemoRegistry:
    """Fictional companies. Never shown as real data: the UI labels the source."""

    name = "demo"
    COMPANIES = {
        c.tin: c
        for c in [
            CompanyInfo("02634517", "«Արարատ Ֆուդս» ՍՊԸ / Ararat Foods LLC", "286.110.112233",
                        "Yerevan, Arshakunyats Ave 12", "Armen Petrosyan", TaxRegime.vat),
            CompanyInfo("02710842", "«Գառնի Կաթ» ՍՊԸ / Garni Dairy LLC", "286.120.445566",
                        "Kotayk, Garni village, 3rd St 7", "Anna Hakobyan", TaxRegime.turnover),
            CompanyInfo("02598301", "«Կասկադ Կաֆե» ՍՊԸ / Cascade Cafe LLC", "290.110.778899",
                        "Yerevan, Tamanyan St 3", "Davit Grigoryan", TaxRegime.turnover),
            CompanyInfo("02744119", "«Սևան Ֆիշ» ՍՊԸ / Sevan Fish LLC", "290.130.990011",
                        "Gegharkunik, Sevan, Nairyan St 21", "Tigran Sargsyan", TaxRegime.vat),
            CompanyInfo("35012345", "Ա/Ձ Մարիամ Ավետիսյան / IE Mariam Avetisyan", "35.123.45678",
                        "Yerevan, Komitas Ave 40", "Mariam Avetisyan", TaxRegime.micro),
            CompanyInfo("02611111", "«Հին Ընկերություն» ՍՊԸ / Old Company LLC", "286.110.000001",
                        "Yerevan, Abovyan St 1", "Closed", None, active=False),
        ]
    }  # fmt: skip

    async def lookup(self, tin: str) -> CompanyInfo | None:
        return self.COMPANIES.get(tin)


class NoRegistry:
    name = "none"

    async def lookup(self, tin: str) -> CompanyInfo | None:
        return None


class CachedRegistry:
    """Remembers answers in Redis: the register is asked once per TIN a day (lookup and sign-up both ask).

    "Not found" is kept shorter: a company registered today should show up soon. Errors are not cached.
    Works without Redis: then every lookup goes to the register.
    """

    FOUND_S = 24 * 3600
    NOT_FOUND_S = 3 * 3600

    def __init__(self, inner: Registry, redis: aioredis.Redis):
        self.inner = inner
        self.name = inner.name
        self._redis = redis

    def _key(self, tin: str) -> str:
        return f"registry:{self.name}:{tin}"

    async def lookup(self, tin: str) -> CompanyInfo | None:
        try:
            raw = await self._redis.get(self._key(tin))
        except (RedisError, OSError) as e:
            log.warning("registry cache unavailable: %s", e)
            raw = None
        if raw is not None:
            data = json.loads(raw)
            if data is None:
                return None
            data["tax_regime"] = TaxRegime(data["tax_regime"]) if data.get("tax_regime") else None
            return CompanyInfo(**data)

        company = await self.inner.lookup(tin)  # RegistryUnavailable passes through, uncached
        value = json.dumps(dataclasses.asdict(company) if company else None, ensure_ascii=False)
        try:
            await self._redis.set(self._key(tin), value, ex=self.FOUND_S if company else self.NOT_FOUND_S)
        except (RedisError, OSError) as e:
            log.warning("registry cache unavailable: %s", e)
        return company


_redis_client: aioredis.Redis | None = None


def _redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            get_settings().redis_url, socket_timeout=1, socket_connect_timeout=1
        )
    return _redis_client


def get_registry() -> Registry:
    settings = get_settings()
    if settings.registry_provider == "demo":
        return DemoRegistry()
    if settings.registry_provider == "eregister":
        from app.integrations.eregister import EregisterRegistry

        return CachedRegistry(EregisterRegistry(settings.eregister_url), _redis())
    return NoRegistry()
