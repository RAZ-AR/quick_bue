"""Company data by Armenian TIN (ՀՎՀՀ) to prefill sign-up.

Armenia has no official public API for this (as of Oct 2026): the state register (e-register.moj.am)
and the SRC taxpayer search are web forms. Paid intermediaries exist (an Apify actor over the register's
open data, karg.am), but their terms and accuracy are not verified. So the registry is a port: services
call `get_registry()` and never know which provider answers. "demo" serves fictional companies.
"""

import re
from dataclasses import dataclass
from typing import Protocol

from app.config import get_settings
from app.models import TaxRegime

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


def get_registry() -> Registry:
    return DemoRegistry() if get_settings().registry_provider == "demo" else NoRegistry()
