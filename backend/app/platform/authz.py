"""Who may do what (docs/03-architecture.md §2.11). One table, one check function.

Every request runs as an Actor: a user acting for one organization (X-Org-Id header).
"""

from dataclasses import dataclass
from enum import StrEnum

from app.models import Membership, Organization, OrgKind, OrgStatus, Role, User
from app.platform.errors import NotAllowed


class Action(StrEnum):
    cart_edit = "cart.edit"
    order_place = "order.place"
    offer_make = "offer.make"
    order_buyer = "order.buyer"  # cancel, accept delivery, reorder, answer seller counters
    order_seller = "order.seller"  # confirm, reject, ship, deliver, mark paid, answer offers
    agreement_create = "agreement.create"
    org_staff = "org.staff"


B, S = OrgKind.buyer, OrgKind.seller

# (organization kind, role) -> allowed actions
PERMISSIONS: dict[tuple[OrgKind, Role], frozenset[Action]] = {
    (B, Role.owner): frozenset(
        {Action.cart_edit, Action.order_place, Action.offer_make, Action.order_buyer, Action.org_staff}
    ),
    # Staff may also make offers when can_negotiate is set (checked in Actor.can)
    (B, Role.buyer_staff): frozenset({Action.cart_edit, Action.order_place, Action.order_buyer}),
    (S, Role.owner): frozenset({Action.order_seller, Action.agreement_create, Action.org_staff}),
    (S, Role.manager): frozenset({Action.order_seller, Action.agreement_create}),
}


@dataclass(frozen=True)
class Actor:
    user: User
    org: Organization
    membership: Membership

    @property
    def role(self) -> Role:
        return self.membership.role

    @property
    def is_buyer(self) -> bool:
        return self.org.kind == OrgKind.buyer

    @property
    def is_seller(self) -> bool:
        return self.org.kind == OrgKind.seller

    def can(self, action: Action) -> bool:
        if self.org.status == OrgStatus.blocked:
            return False
        if (
            self.org.kind == OrgKind.seller
            and self.org.status != OrgStatus.active
            and action != Action.org_staff
        ):
            return False  # pending sellers cannot trade yet
        allowed = PERMISSIONS.get((self.org.kind, self.role), frozenset())
        if action == Action.offer_make and self.role == Role.buyer_staff:
            return self.membership.can_negotiate
        return action in allowed

    def require(self, action: Action) -> None:
        if not self.can(action):
            raise NotAllowed("not_allowed", f"{self.role} of a {self.org.kind} cannot {action}")
