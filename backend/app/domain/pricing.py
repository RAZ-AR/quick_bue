"""Which unit price applies to a buyer: negotiated → contract → volume tier → list (docs/02-mvp.md §7.3).

Pure functions, no DB: callers load the product, its tiers and the buyer's active agreement.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.models.orders import PriceSource


@dataclass(frozen=True)
class Tier:
    min_qty: Decimal
    price_amd: int


@dataclass(frozen=True)
class UnitPrice:
    amount_amd: int
    source: PriceSource


def resolve_unit_price(
    list_price_amd: int,
    qty: Decimal,
    tiers: Sequence[Tier] = (),
    agreement_price_amd: int | None = None,
    negotiated_price_amd: int | None = None,
) -> UnitPrice:
    if negotiated_price_amd is not None:
        return UnitPrice(negotiated_price_amd, PriceSource.negotiated)
    candidates = [UnitPrice(list_price_amd, PriceSource.list)]
    reachable = [t for t in tiers if qty >= t.min_qty]
    if reachable:
        best = max(reachable, key=lambda t: t.min_qty)
        candidates.append(UnitPrice(best.price_amd, PriceSource.tier))
    if agreement_price_amd is not None:
        candidates.append(UnitPrice(agreement_price_amd, PriceSource.agreement))
    # The contract price wins over a tier only when it is actually lower: a buyer never pays more
    # for having negotiated. On a tie the more specific source (agreement) is kept.
    order = {PriceSource.agreement: 0, PriceSource.tier: 1, PriceSource.list: 2}
    return min(candidates, key=lambda p: (p.amount_amd, order[p.source]))


def line_total_amd(unit_price_amd: int, qty: Decimal) -> int:
    """Line total rounded half-up to whole drams."""
    return int((Decimal(unit_price_amd) * qty).quantize(Decimal(1), rounding="ROUND_HALF_UP"))
