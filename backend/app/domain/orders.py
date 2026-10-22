"""Order lifecycle and money: allowed transitions, totals, delivery date. Pure functions.

Domain modules may import enums from app.models (plain StrEnums), never sessions or queries.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum

from app.domain.pricing import line_total_amd
from app.models import OrderStatus as St


class By(StrEnum):
    buyer = "buyer"
    seller = "seller"
    system = "system"


class OrderAction(StrEnum):
    agree = "agree"  # negotiation finished
    expire = "expire"  # negotiation timed out
    cancel = "cancel"
    confirm = "confirm"
    reject = "reject"
    ship = "ship"
    deliver = "deliver"
    accept = "accept"


# (status, action, who) -> new status. Anything else is forbidden (docs/03-architecture.md §2.5).
TRANSITIONS: dict[tuple[St, OrderAction, By], St] = {
    (St.negotiating, OrderAction.agree, By.system): St.placed,
    (St.negotiating, OrderAction.expire, By.system): St.cancelled,
    (St.negotiating, OrderAction.cancel, By.buyer): St.cancelled,
    (St.placed, OrderAction.confirm, By.seller): St.confirmed,
    (St.placed, OrderAction.reject, By.seller): St.rejected,
    (St.placed, OrderAction.cancel, By.buyer): St.cancelled,
    (St.confirmed, OrderAction.ship, By.seller): St.delivering,
    (St.confirmed, OrderAction.deliver, By.seller): St.delivered,
    (St.delivering, OrderAction.deliver, By.seller): St.delivered,
    (St.delivered, OrderAction.accept, By.buyer): St.accepted,
    (St.delivered, OrderAction.accept, By.system): St.accepted,
}

FINAL = frozenset({St.accepted, St.cancelled, St.rejected})


class InvalidTransition(ValueError):
    def __init__(self, status: St, action: OrderAction, by: By):
        super().__init__(f"{by} cannot {action} an order in status {status}")
        self.status, self.action, self.by = status, action, by


def transition(status: St, action: OrderAction, by: By) -> St:
    try:
        return TRANSITIONS[(status, action, by)]
    except KeyError:
        raise InvalidTransition(status, action, by) from None


def allowed_actions(status: St, by: By) -> list[OrderAction]:
    return [a for (s, a, b) in TRANSITIONS if s == status and b == by]


@dataclass(frozen=True)
class LineAmount:
    qty: Decimal
    unit_price_amd: int


@dataclass(frozen=True)
class Totals:
    subtotal_amd: int
    discount_amd: int
    delivery_fee_amd: int
    total_amd: int


def compute_totals(
    lines: Iterable[LineAmount],
    discount_bp: int = 0,
    delivery_fee_amd: int = 0,
    free_delivery_from_amd: int | None = None,
) -> Totals:
    """Order-level discount (basis points) applies to goods only; delivery is free above the threshold."""
    subtotal = sum(line_total_amd(li.unit_price_amd, li.qty) for li in lines)
    discount = int((Decimal(subtotal) * discount_bp / 10_000).quantize(Decimal(1), rounding="ROUND_HALF_UP"))
    goods = subtotal - discount
    free = free_delivery_from_amd is not None and goods >= free_delivery_from_amd
    fee = 0 if free or subtotal == 0 else delivery_fee_amd
    return Totals(subtotal, discount, fee, goods + fee)


def delivery_date(
    now_local: datetime, cutoff: time, lead_days: int, weekdays: set[int] | None = None
) -> date:
    """First delivery day: after lead_days (+1 if ordered after the cutoff), on a day the seller delivers."""
    start = now_local.date() + timedelta(days=lead_days + (1 if now_local.time() >= cutoff else 0))
    for i in range(14):
        day = start + timedelta(days=i)
        if not weekdays or day.isoweekday() in weekdays:
            return day
    raise ValueError("seller has no delivery days")


def is_valid_qty(qty: Decimal, min_qty: Decimal, step: Decimal) -> bool:
    return qty >= min_qty and qty % step == 0
