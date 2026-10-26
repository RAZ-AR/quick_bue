"""Cart suggestions (cross-sell) as pure rules: no database. services/suggestions.py feeds them.

Four kinds, from the most useful to the buyer to the least:
- fill_min / fill_free_delivery: the same seller's products to reach the minimum order or free delivery;
- tier: "2 more kg and the price per kg drops";
- usual: what this venue bought in the last 90 days and is not in the cart;
- complement: related categories from other sellers (cheese -> bread, packaging), and the sellers' services.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.domain.pricing import Tier

# Category slug -> categories that usually go with it in a HoReCa order
COMPLEMENTS: dict[str, tuple[str, ...]] = {
    "dairy": ("bakery", "produce", "disposables"),
    "meat": ("produce", "bakery", "cleaning"),
    "produce": ("dairy", "meat", "grocery"),
    "coffee": ("dairy", "disposables", "bakery"),
    "bakery": ("dairy", "coffee"),
    "grocery": ("produce", "cleaning"),
    "disposables": ("cleaning", "coffee"),
    "cleaning": ("disposables",),
}


def complement_categories(in_cart: set[str]) -> list[str]:
    """Related categories not yet in the cart, the most often named first."""
    votes: dict[str, int] = {}
    for slug in in_cart:
        for i, other in enumerate(COMPLEMENTS.get(slug, ())):
            if other not in in_cart:
                votes[other] = votes.get(other, 0) + 10 - i
    return sorted(votes, key=lambda s: -votes[s])


@dataclass(frozen=True)
class TierStep:
    min_qty: Decimal
    price_amd: int
    extra_qty: Decimal
    saving_amd: int  # on the whole line at the new quantity, against the current unit price


def next_tier(qty: Decimal, unit_price_amd: int, tiers: list[Tier]) -> TierStep | None:
    """The nearest volume price above the current quantity that is cheaper than what the line pays now."""
    for t in sorted(tiers, key=lambda t: t.min_qty):
        if t.min_qty > qty and t.price_amd < unit_price_amd:
            saving = int((unit_price_amd - t.price_amd) * t.min_qty)
            return TierStep(t.min_qty, t.price_amd, t.min_qty - qty, saving)
    return None


@dataclass(frozen=True)
class Candidate:
    product_id: object
    price_amd: int  # for the smallest quantity one can order
    bought_before: bool
    popularity: int  # order lines in the last 90 days, all buyers


def rank_fillers(candidates: list[Candidate], gap_amd: int, limit: int = 3) -> list[Candidate]:
    """To close a gap: what the venue already buys first, then items that cover the gap without overshooting
    much, then the popular ones."""

    def score(c: Candidate) -> tuple:
        covers = c.price_amd >= gap_amd
        overshoot = c.price_amd - gap_amd if covers else gap_amd - c.price_amd
        return (not c.bought_before, not covers, overshoot, -c.popularity)

    return sorted(candidates, key=score)[:limit]
