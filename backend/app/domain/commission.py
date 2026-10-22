"""Platform commission on an accepted order (docs/03-architecture.md §2.7). Pure functions."""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Commission:
    amount_amd: int
    rate_bp: int  # effective (weighted) rate, for display and reports


def compute(lines: Iterable[tuple[int, int]], first_order_bonus_bp: int = 0) -> Commission:
    """lines: (goods amount after discount, rate bp). The bonus applies on top of every line's rate."""
    base = 0
    exact = Decimal(0)
    for amount, rate in lines:
        base += amount
        exact += Decimal(amount) * (rate + first_order_bonus_bp) / 10_000
    amount = int(exact.quantize(Decimal(1), rounding="ROUND_HALF_UP"))
    rate = int((exact * 10_000 / base).quantize(Decimal(1), rounding="ROUND_HALF_UP")) if base else 0
    return Commission(amount, rate)
