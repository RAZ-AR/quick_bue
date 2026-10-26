"""TIN lookup through the public search of e-register.moj.am, on pages saved from the register (Oct 2026)."""

from pathlib import Path

import httpx
import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app.integrations import eregister as er
from app.integrations import registry as reg
from app.integrations.registry import CachedRegistry, CompanyInfo, RegistryUnavailable

PAGES = Path(__file__).parent / "fixtures" / "eregister"
UCOM = "00024873"  # an active company
LIQUIDATING = "00093347"  # "in the process of liquidation"


def page(name: str) -> str:
    return (PAGES / name).read_text(encoding="utf-8")


# --- parsing -----------------------------------------------------------------------------------------------


def test_parse_search_results():
    assert er.parse_search(page("search_found.html")) == ["/hy/companies/37191802"]
    assert er.parse_search(page("search_empty.html")) == []


def test_parse_active_company_card():
    hy, en = er.parse_company(page("company_hy.html")), er.parse_company(page("company_en.html"))
    assert hy.name == "«ՅՈՒՔՈՄ» ՓԲԸ" and en.name == '"UCOM" CJSC'
    c = er.to_company(UCOM, hy, en)
    assert c is not None
    assert (c.legal_name, c.registration_number, c.active, c.source) == (
        '«ՅՈՒՔՈՄ» ՓԲԸ / "UCOM" CJSC',
        "286.120.1110041",
        True,
        "eregister",
    )
    assert c.legal_address == "ՄԱՆԱՆԴՅԱՆ Փ., 33/8, ՇԵՆՔ, ԵՐԵՎԱՆ, 0046, ԵՐԵՎԱՆ"
    assert (c.director_name, c.tax_regime) == (None, None)  # not on the free card
    # Menu headings and declaration links are not card fields
    assert set(hy.fields) >= {"Գրանցման համար", "ՀՎՀՀ", "Գտնվելու վայր", "Կարգավիճակ"}
    assert not any(v.startswith("20") and ":" in v for v in hy.fields.values())


def test_liquidating_company_is_inactive():
    c = er.to_company(LIQUIDATING, er.parse_company(page("company_liquidating_hy.html")), None)
    assert c is not None and c.active is False


def test_another_companys_card_or_unknown_layout():
    hy = er.parse_company(page("company_hy.html"))
    assert er.to_company("11111111", hy, None) is None
    with pytest.raises(RegistryUnavailable):
        er.to_company(UCOM, er.parse_company("<html><h4>Something else</h4></html>"), None)


# --- the adapter, with the register replaced by saved pages -------------------------------------------------


def registry(routes: dict[str, httpx.Response]) -> er.EregisterRegistry:
    def answer(request: httpx.Request) -> httpx.Response:
        key = request.url.path + (
            f"?query={request.url.params['query']}" if "query" in request.url.params else ""
        )
        return routes.get(key, httpx.Response(404))

    client = httpx.AsyncClient(transport=httpx.MockTransport(answer))
    return er.EregisterRegistry("https://e-register.test", client=client)


FOUND = {
    f"/hy/search/companies?query={UCOM}": httpx.Response(200, text=page("search_found.html")),
    "/hy/companies/37191802": httpx.Response(200, text=page("company_hy.html")),
    "/en/companies/37191802": httpx.Response(200, text=page("company_en.html")),
}


async def test_lookup_finds_company_by_tin():
    c = await registry(FOUND).lookup(UCOM)
    assert c is not None and c.legal_name.startswith("«ՅՈՒՔՈՄ» ՓԲԸ") and c.active


async def test_lookup_not_found():
    routes = {"/hy/search/companies?query=99999990": httpx.Response(200, text=page("search_empty.html"))}
    assert await registry(routes).lookup("99999990") is None


async def test_lookup_without_latin_name_keeps_armenian():
    routes = {**FOUND, "/en/companies/37191802": httpx.Response(503)}
    c = await registry(routes).lookup(UCOM)
    assert c is not None and c.legal_name == "«ՅՈՒՔՈՄ» ՓԲԸ"


@pytest.mark.parametrize(
    "search",
    [
        httpx.Response(500),
        httpx.Response(200, text="<html>Maintenance</html>"),  # the page changed: not "not found"
    ],
)
async def test_lookup_unavailable(search):
    with pytest.raises(RegistryUnavailable):
        await registry({f"/hy/search/companies?query={UCOM}": search}).lookup(UCOM)


async def test_lookup_network_error():
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("slow", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(boom))
    with pytest.raises(RegistryUnavailable):
        await er.EregisterRegistry("https://e-register.test", client=client).lookup(UCOM)


# --- cache ---------------------------------------------------------------------------------------------------


class FakeRedis:
    def __init__(self, down: bool = False):
        self.data: dict[str, str] = {}
        self.ttl: dict[str, int] = {}
        self.down = down

    async def get(self, key):
        if self.down:
            raise RedisConnectionError("down")
        return self.data.get(key)

    async def set(self, key, value, ex=None):
        if self.down:
            raise RedisConnectionError("down")
        self.data[key], self.ttl[key] = value, ex


class Counting:
    name = "eregister"

    def __init__(self, answer: CompanyInfo | None | Exception):
        self.answer, self.calls = answer, 0

    async def lookup(self, tin):
        self.calls += 1
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


COMPANY = CompanyInfo(UCOM, "«ՅՈՒՔՈՄ» ՓԲԸ", "286.120.1110041", "Yerevan", None, None, True, "eregister")


async def test_cache_remembers_answers():
    redis, inner = FakeRedis(), Counting(COMPANY)
    cached = CachedRegistry(inner, redis)
    assert await cached.lookup(UCOM) == COMPANY
    assert await cached.lookup(UCOM) == COMPANY
    assert inner.calls == 1 and redis.ttl[f"registry:eregister:{UCOM}"] == CachedRegistry.FOUND_S

    missing = CachedRegistry(Counting(None), redis)
    assert await missing.lookup("99999990") is None
    assert await missing.lookup("99999990") is None
    assert missing.inner.calls == 1 and redis.ttl["registry:eregister:99999990"] == CachedRegistry.NOT_FOUND_S


async def test_cache_skips_errors_and_works_without_redis():
    redis, inner = FakeRedis(), Counting(RegistryUnavailable("down"))
    with pytest.raises(RegistryUnavailable):
        await CachedRegistry(inner, redis).lookup(UCOM)
    assert redis.data == {}

    inner = Counting(COMPANY)
    no_redis = CachedRegistry(inner, FakeRedis(down=True))
    assert await no_redis.lookup(UCOM) == COMPANY and await no_redis.lookup(UCOM) == COMPANY
    assert inner.calls == 2


# --- sign-up falls back to manual entry -----------------------------------------------------------------------


@pytest.mark.usefixtures("seeded")
async def test_signup_when_register_is_down(client, monkeypatch):
    from app.services import onboarding

    monkeypatch.setattr(onboarding, "get_registry", lambda: Counting(RegistryUnavailable("down")))
    r = await client.post("/auth/dev-register", json={"name": "Ani", "email": "ani@example.am"})
    me = {"Authorization": f"Bearer {r.json()['access_token']}"}

    body = (await client.get("/registry/lookup", headers=me, params={"tin": UCOM})).json()
    assert (body["found"], body["unavailable"], body["provider"]) == (False, True, "eregister")

    r = await client.post(
        "/organizations",
        headers=me,
        json={"roles": ["seller"], "tin": UCOM, "legal_name": "UCOM CJSC", "display_name": "UCOM"},
    )
    assert r.status_code == 201, r.text


def test_provider_switch(monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "registry_provider", "eregister")
    r = reg.get_registry()
    assert isinstance(r, CachedRegistry) and isinstance(r.inner, er.EregisterRegistry)
    assert r.inner.base_url == "https://e-register.moj.am"
