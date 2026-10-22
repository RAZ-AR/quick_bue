"""Who may do what (docs/03-architecture.md §2.11, docs/05-cabinets-and-auth.md).

Every request runs as an Actor: a user acting for one organization (X-Org-Id)
in one mode (X-Mode: buyer|seller).
A company may play both sides; each side has its own gate:
- buying is open once the company is registered and its registry extract is uploaded (or it is verified);
- selling is open only after an operator verified the company. Preparing the catalog is allowed before that.
"""

import dataclasses
from dataclasses import dataclass
from enum import StrEnum

from app.models import Membership, Organization, OrgKind, OrgStatus, Role, User, VerificationStatus
from app.platform.errors import NotAllowed


class Action(StrEnum):
    cart_edit = "cart.edit"
    order_place = "order.place"
    offer_make = "offer.make"
    order_buyer = "order.buyer"  # cancel, accept delivery, reorder, answer seller counters
    order_seller = "order.seller"  # confirm, reject, ship, deliver, mark paid, answer offers
    agreement_create = "agreement.create"
    catalog_edit = "catalog.edit"  # products, prices, delivery terms, autopilot
    org_staff = "org.staff"  # requisites, verification, roles, team


B, S = OrgKind.buyer, OrgKind.seller

# (mode, role) -> allowed actions
PERMISSIONS: dict[tuple[OrgKind, Role], frozenset[Action]] = {
    (B, Role.owner): frozenset({Action.cart_edit, Action.order_place, Action.offer_make, Action.order_buyer}),
    # Staff may also make offers when can_negotiate is set (checked in Actor.can)
    (B, Role.buyer_staff): frozenset({Action.cart_edit, Action.order_place, Action.order_buyer}),
    (S, Role.owner): frozenset({Action.order_seller, Action.agreement_create, Action.catalog_edit}),
    (S, Role.manager): frozenset({Action.order_seller, Action.agreement_create, Action.catalog_edit}),
}

# Selling actions that need a verified company; catalog editing does not
NEEDS_VERIFIED = frozenset({Action.order_seller, Action.agreement_create})
BUYING = frozenset({Action.cart_edit, Action.order_place, Action.offer_make, Action.order_buyer})


def can_sell(org: Organization) -> bool:
    return (
        org.is_seller
        and org.status != OrgStatus.blocked
        and org.verification_status == VerificationStatus.verified
    )


@dataclass(frozen=True)
class Actor:
    user: User
    org: Organization
    membership: Membership
    mode: OrgKind = OrgKind.buyer
    # Registry extract uploaded (or company verified): computed by the auth dependency
    buyer_ready: bool = False

    @property
    def role(self) -> Role:
        return self.membership.role

    @property
    def is_buyer(self) -> bool:
        """Acting on the buying side right now."""
        return self.mode == OrgKind.buyer

    @property
    def is_seller(self) -> bool:
        return self.mode == OrgKind.seller

    def with_mode(self, mode: OrgKind) -> "Actor":
        """Order pages decide the side themselves: the same user may be the buyer of one order and the seller
        of another, whatever mode the app is in."""
        return self if mode == self.mode else dataclasses.replace(self, mode=mode)

    def why_not(self, action: Action) -> str | None:
        org = self.org
        if org.status == OrgStatus.blocked:
            return "company_blocked"
        if action == Action.org_staff:
            return None if self.role == Role.owner else "owners_only"
        if self.mode == OrgKind.buyer and not org.is_buyer:
            return "not_a_buyer"
        if self.mode == OrgKind.seller and not org.is_seller:
            return "not_a_seller"
        if action in BUYING and action != Action.cart_edit and not self.buyer_ready:
            return "upload_registry_extract"
        if action in NEEDS_VERIFIED and not can_sell(org):
            return "seller_not_verified"
        if action == Action.offer_make and self.role == Role.buyer_staff:
            return None if self.membership.can_negotiate else "not_allowed_to_negotiate"
        allowed = PERMISSIONS.get((self.mode, self.role), frozenset())
        return None if action in allowed else "not_allowed"

    def can(self, action: Action) -> bool:
        return self.why_not(action) is None

    def require(self, action: Action) -> None:
        reason = self.why_not(action)
        if reason is not None:
            raise NotAllowed(reason, f"{self.role} in {self.mode} mode cannot {action}")
