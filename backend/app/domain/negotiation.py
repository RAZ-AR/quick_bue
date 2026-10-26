"""Negotiation rules and the seller autopilot (docs/02-mvp.md §6, docs/03-architecture.md §2.4).

Line offers carry unit prices. Prices must converge: each new buyer offer is higher than the previous one,
each seller counter is lower than the previous one, and they never cross.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from app.domain.pricing import line_total_amd

MIN_OFFER_RATIO = Decimal("0.5")  # an offer below 50% of the price is noise
MAX_DISCOUNT_BP = 5_000  # order-level discount up to 50%


# --- validation: returns a problem code or None ----------------------------------------------------------


def check_buyer_price(
    proposed: int,
    reference: int,
    qty: Decimal,
    min_line_amd: int,
    previous_buyer: int | None = None,
    seller_counter: int | None = None,
) -> str | None:
    if proposed <= 0:
        return "bad_price"
    if proposed >= reference:
        return "offer_not_below_price"
    if proposed < reference * MIN_OFFER_RATIO:
        return "offer_too_low"
    if line_total_amd(reference, qty) < min_line_amd:
        return "line_too_small_for_offer"
    if previous_buyer is not None and proposed <= previous_buyer:
        return "offer_must_increase"
    if seller_counter is not None and proposed >= seller_counter:
        return "offer_not_below_counter"  # equal or higher: just accept the counter
    return None


def check_seller_price(
    counter: int, reference: int, buyer_offer: int, previous_seller: int | None = None
) -> str | None:
    if counter >= reference:
        return "counter_not_below_price"  # no discount = decline
    if counter <= buyer_offer:
        return "counter_not_above_offer"  # equal or lower: just accept the offer
    if previous_seller is not None and counter >= previous_seller:
        return "counter_must_decrease"
    return None


def check_buyer_percent(
    percent_bp: int,
    subtotal_amd: int,
    min_order_amd: int,
    previous_buyer: int | None = None,
    seller_counter: int | None = None,
) -> str | None:
    if not 0 < percent_bp <= MAX_DISCOUNT_BP:
        return "bad_discount"
    if subtotal_amd < min_order_amd:
        return "order_too_small_for_offer"
    if previous_buyer is not None and percent_bp >= previous_buyer:
        return "offer_must_increase"  # asking for a smaller discount = a higher price
    if seller_counter is not None and percent_bp <= seller_counter:
        return "offer_not_below_counter"
    return None


def check_seller_percent(counter_bp: int, buyer_bp: int, previous_seller: int | None = None) -> str | None:
    if counter_bp <= 0:
        return "counter_not_below_price"
    if counter_bp >= buyer_bp:
        return "counter_not_above_offer"
    if previous_seller is not None and counter_bp <= previous_seller:
        return "counter_must_decrease"
    return None


# --- autopilot ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class AutoRule:
    """A seller rule resolved for one line. Absolute prices win over percentages of the reference price."""

    floor_price_amd: int | None = None
    floor_pct_bp: int | None = None
    accept_price_amd: int | None = None
    accept_pct_bp: int | None = None
    auto_counter: bool = True
    only_regulars: bool = False
    min_qty: Decimal | None = None
    min_line_amd: int | None = None


class Verdict(StrEnum):
    accept = "accept"
    counter = "counter"
    decline = "decline"
    manual = "manual"


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    price_amd: int | None = None
    reason: str | None = None


def discount_bp(price: int, reference: int) -> int:
    """How far below the reference a price is, in basis points (rounded down: never promise more)."""
    if reference <= 0 or price >= reference:
        return 0
    return (reference - price) * 10_000 // reference


def accept_discount_bp(rule: AutoRule, reference: int) -> int | None:
    """The discount the autopilot accepts at once for this reference price."""
    if rule.accept_price_amd is not None:
        return discount_bp(rule.accept_price_amd, reference)
    if rule.accept_pct_bp is not None:
        return 10_000 - rule.accept_pct_bp
    return None


def _pct(reference: int, bp: int) -> int:
    # Nearest dram: a rule saved as "-5.71%" keeps the 3 300 it was set from on a 3 500 price
    return int((Decimal(reference) * bp / 10_000).to_integral_value(rounding=ROUND_HALF_UP))


def _round10(value: Decimal) -> int:
    return int((value / 10).quantize(Decimal(1), rounding="ROUND_HALF_UP")) * 10


def decide(
    proposed: int, reference: int, qty: Decimal, rule: AutoRule | None, client_orders: int
) -> Decision:
    if rule is None:
        return Decision(Verdict.manual)
    if rule.only_regulars and client_orders < 3:
        return Decision(Verdict.manual)
    if rule.min_qty is not None and qty < rule.min_qty:
        return Decision(Verdict.manual)
    if rule.min_line_amd is not None and line_total_amd(reference, qty) < rule.min_line_amd:
        return Decision(Verdict.decline, reason="line_too_small_for_offer")

    accept = rule.accept_price_amd or (_pct(reference, rule.accept_pct_bp) if rule.accept_pct_bp else None)
    floor = rule.floor_price_amd or (_pct(reference, rule.floor_pct_bp) if rule.floor_pct_bp else 0)
    if accept is None:
        return Decision(Verdict.manual)
    if proposed >= accept:
        return Decision(Verdict.accept, proposed)
    if proposed < floor:
        return Decision(Verdict.decline, reason="below_floor")
    if not rule.auto_counter:
        return Decision(Verdict.manual)
    counter = max(accept, _round10((Decimal(proposed) + reference) / 2))
    if counter >= reference:
        return Decision(Verdict.decline, reason="no_discount_possible")
    return Decision(Verdict.counter, counter)
