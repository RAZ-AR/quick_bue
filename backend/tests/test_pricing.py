from decimal import Decimal as D

from app.core.pricing import Tier, line_total_amd, resolve_unit_price
from app.core.search import build_search_text, transliterate
from app.models import PriceSource

TIERS = [Tier(D(10), 3400), Tier(D(20), 3350)]


def test_list_price_below_first_tier():
    p = resolve_unit_price(3500, D(5), TIERS)
    assert (p.amount_amd, p.source) == (3500, PriceSource.list)


def test_highest_reached_tier_wins():
    assert resolve_unit_price(3500, D(10), TIERS).amount_amd == 3400
    p = resolve_unit_price(3500, D(25), TIERS)
    assert (p.amount_amd, p.source) == (3350, PriceSource.tier)


def test_agreement_beats_tier_only_when_cheaper():
    assert resolve_unit_price(3500, D(5), TIERS, agreement_price_amd=3300).source == PriceSource.agreement
    # A buyer with a contract never pays more than an anonymous buyer for the same volume
    p = resolve_unit_price(3500, D(25), TIERS, agreement_price_amd=3380)
    assert (p.amount_amd, p.source) == (3350, PriceSource.tier)
    # Tie: the contract is reported as the source
    assert resolve_unit_price(3500, D(25), TIERS, agreement_price_amd=3350).source == PriceSource.agreement


def test_negotiated_price_is_final():
    p = resolve_unit_price(3500, D(25), TIERS, agreement_price_amd=3000, negotiated_price_amd=3300)
    assert (p.amount_amd, p.source) == (3300, PriceSource.negotiated)


def test_line_total_rounds_half_up():
    assert line_total_amd(2000, D("0.5")) == 1000
    assert line_total_amd(999, D("1.5")) == 1499  # 1498.5 -> 1499
    assert line_total_amd(3500, D(12)) == 42_000


def test_transliteration():
    assert transliterate("Լոռի պանիր") == "lori panir"
    assert transliterate("Սուրճ") == "surch"
    assert transliterate("Сыр чанах") == "syr chanakh"


def test_search_text_dedupes_and_keeps_all_languages():
    text = build_search_text({"hy": "Պանիր", "ru": "Сыр", "en": "Cheese"})
    assert text == "պանիր panir сыр syr cheese"
