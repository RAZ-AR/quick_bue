"""Price negotiation on an order (docs/02-mvp.md §6, docs/03-architecture.md §2.4).

Semantics:
- The buyer's first offer comes with checkout. The other side answers every open line (or the whole order):
  accept, decline or counter. Accept fixes the proposed price; decline keeps the pre-negotiation price.
- When no line is left open, the order becomes `placed` (the buyer may still cancel before confirmation).
- No answer in time: the order is cancelled (`offer_expired`); the buyer can reorder at the list price.
- The seller autopilot answers buyer offers when every open line has a rule that decides it.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.domain import negotiation as rules
from app.domain.orders import By, OrderAction
from app.models import (
    ClientLink,
    LineDecision,
    Negotiation,
    NegotiationScope,
    NegotiationStatus,
    Offer,
    OfferKind,
    OfferLine,
    OfferResponse,
    Order,
    OrderLine,
    OrderStatus,
    OrgKind,
    PriceSource,
    Product,
    SellerProfile,
    Side,
)
from app.platform.authz import Action, Actor
from app.platform.errors import Conflict, NotFound, ValidationFailed
from app.services import orders as order_svc
from app.services.prices import RuleBook, load_rule_book

AWAITING = {Side.buyer: NegotiationStatus.awaiting_buyer, Side.seller: NegotiationStatus.awaiting_seller}


def other(side: Side) -> Side:
    return Side.seller if side == Side.buyer else Side.buyer


@dataclass(frozen=True)
class LineAnswer:
    order_line_id: uuid.UUID
    decision: LineDecision
    price_amd: int | None = None


@dataclass(frozen=True)
class OrderAnswer:
    decision: LineDecision
    percent_bp: int | None = None


async def _response_hours(session: AsyncSession, seller_id: uuid.UUID) -> int:
    profile = await session.get(SellerProfile, seller_id)
    return profile.offer_response_hours if profile else get_settings().offer_response_hours


async def _client_orders(session: AsyncSession, order: Order) -> int:
    link = await session.scalar(
        select(ClientLink).where(
            ClientLink.seller_id == order.seller_id, ClientLink.buyer_id == order.buyer_id
        )
    )
    return link.orders_count if link else 0


async def load_for_order(
    session: AsyncSession, order_id: uuid.UUID, lock: bool = False
) -> Negotiation | None:
    stmt = (
        select(Negotiation)
        .where(Negotiation.order_id == order_id)
        .options(selectinload(Negotiation.offers).selectinload(Offer.lines))
    )
    if lock:
        stmt = stmt.with_for_update(of=Negotiation)
    return await session.scalar(stmt)


# --- opening ----------------------------------------------------------------------------------------------


async def open_negotiation(
    session: AsyncSession,
    order: Order,
    actor: Actor,
    now: datetime,
    line_offers: dict[uuid.UUID, int] | None = None,
    percent_bp: int | None = None,
) -> Negotiation:
    """Called by checkout after the order and its lines are flushed. Offers were validated by the cart."""
    scope = NegotiationScope.order if percent_bp is not None else NegotiationScope.lines
    nego = Negotiation(
        order_id=order.id,
        status=NegotiationStatus.awaiting_seller,
        scope=scope,
        round=1,
        expires_at=now + timedelta(hours=await _response_hours(session, order.seller_id)),
    )
    session.add(nego)
    offer = Offer(
        negotiation=nego,
        from_side=Side.buyer,
        author_user_id=actor.user.id,
        kind=OfferKind.percent if percent_bp is not None else OfferKind.price,
        percent_bp=percent_bp,
        lines=[OfferLine(order_line_id=k, proposed_price_amd=v) for k, v in (line_offers or {}).items()],
    )
    session.add(offer)
    await session.flush()
    order_svc.log(session, order, "offer_made", actor.user.id, round=1, percent_bp=percent_bp)
    await _autopilot(session, order, nego, now)
    return nego


# --- answering --------------------------------------------------------------------------------------------


def _open_offer(nego: Negotiation) -> Offer:
    pending = [o for o in nego.offers if o.response is None]
    if len(pending) != 1:
        raise Conflict("negotiation_state", "expected exactly one open offer")
    return pending[0]


def _history(nego: Negotiation, side: Side, order_line_id: uuid.UUID) -> int | None:
    """The last price this side proposed for the line, if any."""
    last = None
    for offer in nego.offers:
        if offer.from_side == side:
            for ol in offer.lines:
                if ol.order_line_id == order_line_id:
                    last = ol.proposed_price_amd
    return last


def _last_percent(nego: Negotiation, side: Side) -> int | None:
    return next((o.percent_bp for o in reversed(nego.offers) if o.from_side == side), None)


async def respond(
    session: AsyncSession,
    actor: Actor,
    order_id: uuid.UUID,
    now: datetime,
    lines: list[LineAnswer] | None = None,
    whole: OrderAnswer | None = None,
) -> Order:
    order = await order_svc.get_for_actor(session, actor, order_id, lock=True)
    side = Side.buyer if order_svc.side_of(actor, order) == By.buyer else Side.seller
    actor = actor.with_mode(OrgKind.buyer if side == Side.buyer else OrgKind.seller)
    actor.require(Action.order_buyer if side == Side.buyer else Action.order_seller)
    nego = await load_for_order(session, order.id, lock=True)
    if nego is None or order.status != OrderStatus.negotiating:
        raise Conflict("no_open_negotiation")
    if nego.status != AWAITING[side]:
        raise Conflict("not_your_turn", details={"status": nego.status})
    if nego.expires_at <= now:
        raise Conflict("negotiation_expired")
    counters = any(a.decision == LineDecision.countered for a in lines or []) or (
        whole is not None and whole.decision == LineDecision.countered
    )
    if side == Side.buyer and counters:
        actor.require(Action.offer_make)
    await _apply(session, order, nego, side, now, actor.user.id, is_auto=False, lines=lines, whole=whole)
    return order


async def _apply(
    session: AsyncSession,
    order: Order,
    nego: Negotiation,
    side: Side,
    now: datetime,
    user_id: uuid.UUID | None,
    is_auto: bool,
    lines: list[LineAnswer] | None = None,
    whole: OrderAnswer | None = None,
) -> None:
    offer = _open_offer(nego)
    if offer.from_side == side:
        raise Conflict("not_your_turn")
    my_offers = sum(1 for o in nego.offers if o.from_side == side)
    max_rounds = get_settings().offer_max_rounds
    problems: list[dict] = []

    if nego.scope == NegotiationScope.lines:
        by_line = {li.id: li for li in order.lines}
        open_lines = {
            ol.order_line_id: ol for ol in offer.lines if by_line[ol.order_line_id].final_price_amd is None
        }
        answers = {a.order_line_id: a for a in lines or []}
        if set(answers) != set(open_lines):
            raise ValidationFailed([{"code": "answer_every_open_line", "open": [str(k) for k in open_lines]}])
        new_lines: list[OfferLine] = []
        for line_id, ol in open_lines.items():
            line, ans = by_line[line_id], answers[line_id]
            ol.decision = ans.decision
            if ans.decision == LineDecision.accepted:
                line.final_price_amd = ol.proposed_price_amd
                line.price_source = PriceSource.negotiated
            elif ans.decision == LineDecision.declined:
                line.final_price_amd = line.list_price_amd  # the pre-negotiation price
            else:
                problem = _check_counter(nego, side, line, ol, ans.price_amd, my_offers, max_rounds)
                if problem:
                    problems.append({"order_line_id": str(line_id), "code": problem})
                else:
                    new_lines.append(OfferLine(order_line_id=line_id, proposed_price_amd=ans.price_amd))
        if problems:
            raise ValidationFailed(problems)
        decisions = {ol.decision for ol in open_lines.values()}
        if new_lines:
            offer.response = OfferResponse.countered
            session.add(
                Offer(
                    negotiation=nego,
                    from_side=side,
                    author_user_id=user_id,
                    is_auto=is_auto,
                    kind=OfferKind.price,
                    lines=new_lines,
                )
            )
        else:
            offer.response = (
                OfferResponse.accepted if LineDecision.accepted in decisions else OfferResponse.declined
            )
    else:
        if whole is None:
            raise ValidationFailed([{"code": "answer_the_order_offer"}])
        if whole.decision == LineDecision.countered:
            problem = _check_percent_counter(
                nego, side, order, offer, whole.percent_bp, my_offers, max_rounds
            )
            if problem:
                raise ValidationFailed([{"code": problem}])
            offer.response = OfferResponse.countered
            session.add(
                Offer(
                    negotiation=nego,
                    from_side=side,
                    author_user_id=user_id,
                    is_auto=is_auto,
                    kind=OfferKind.percent,
                    percent_bp=whole.percent_bp,
                )
            )
        else:
            offer.response = (
                OfferResponse.accepted if whole.decision == LineDecision.accepted else OfferResponse.declined
            )

    await session.flush()  # the new offer is already in nego.offers via back_populates
    if offer.response == OfferResponse.countered:
        nego.round += 1
        nego.status = AWAITING[other(side)]
        nego.expires_at = now + timedelta(hours=await _response_hours(session, order.seller_id))
        order_svc.log(session, order, "offer_countered", user_id, by=side, auto=is_auto, round=nego.round)
        if side == Side.buyer:
            await _autopilot(session, order, nego, now)
    else:
        await _finish(session, order, nego, now, user_id, by=side, auto=is_auto)


def _check_counter(
    nego: Negotiation,
    side: Side,
    line: OrderLine,
    ol: OfferLine,
    price: int | None,
    my_offers: int,
    max_rounds: int,
) -> str | None:
    if price is None:
        return "price_required"
    if my_offers >= max_rounds:
        return "no_rounds_left"
    if side == Side.seller:
        return rules.check_seller_price(
            price, line.list_price_amd, ol.proposed_price_amd, _history(nego, Side.seller, line.id)
        )
    return rules.check_buyer_price(
        price,
        line.list_price_amd,
        Decimal(line.qty_ordered),
        0,  # the line already qualified when the first offer was made
        previous_buyer=_history(nego, Side.buyer, line.id),
        seller_counter=ol.proposed_price_amd,
    )


def _check_percent_counter(
    nego: Negotiation,
    side: Side,
    order: Order,
    offer: Offer,
    percent: int | None,
    my_offers: int,
    max_rounds: int,
) -> str | None:
    if percent is None:
        return "percent_required"
    if my_offers >= max_rounds:
        return "no_rounds_left"
    if side == Side.seller:
        return rules.check_seller_percent(percent, offer.percent_bp or 0, _last_percent(nego, Side.seller))
    return rules.check_buyer_percent(
        percent, order.subtotal_amd, 0, _last_percent(nego, Side.buyer), seller_counter=offer.percent_bp
    )


async def _finish(
    session: AsyncSession, order: Order, nego: Negotiation, now: datetime, user_id, by: Side, auto: bool
) -> None:
    if nego.scope == NegotiationScope.lines:
        agreed = any(li.price_source == PriceSource.negotiated for li in order.lines)
    else:
        agreed = any(o.response == OfferResponse.accepted for o in nego.offers)
    nego.status = NegotiationStatus.agreed if agreed else NegotiationStatus.declined
    order_svc.apply(order, OrderAction.agree, By.system, now)
    await order_svc.recompute(session, order)
    order_svc.log(
        session, order, "negotiation_" + nego.status, user_id, by=by, auto=auto, total=order.total_amd
    )
    order_svc.log(session, order, "placed", None)


# --- autopilot and expiry -------------------------------------------------------------------------------


async def _autopilot(session: AsyncSession, order: Order, nego: Negotiation, now: datetime) -> None:
    """Answer the buyer's open offer for the seller when every open line has a deciding rule."""
    if nego.scope != NegotiationScope.lines or nego.status != NegotiationStatus.awaiting_seller:
        return
    offer = _open_offer(nego)
    book: RuleBook = await load_rule_book(session, order.seller_id)
    client_orders = await _client_orders(session, order)
    seller_offers = sum(1 for o in nego.offers if o.from_side == Side.seller)
    by_line = {li.id: li for li in order.lines}
    answers: list[LineAnswer] = []
    for ol in offer.lines:
        line = by_line[ol.order_line_id]
        if line.final_price_amd is not None:
            continue
        product = await session.get(Product, line.product_id) if line.product_id else None
        if product is None:
            return
        d = rules.decide(
            ol.proposed_price_amd,
            line.list_price_amd,
            Decimal(line.qty_ordered),
            book.auto_rule(product),
            client_orders,
        )
        if d.verdict == rules.Verdict.manual:
            return
        if d.verdict == rules.Verdict.counter:
            prev = _history(nego, Side.seller, line.id)
            if seller_offers >= get_settings().offer_max_rounds or (prev is not None and d.price_amd >= prev):
                return  # the autopilot cannot improve its last counter: a human decides
            answers.append(LineAnswer(line.id, LineDecision.countered, d.price_amd))
        elif d.verdict == rules.Verdict.accept:
            answers.append(LineAnswer(line.id, LineDecision.accepted))
        else:
            answers.append(LineAnswer(line.id, LineDecision.declined))
    if answers:
        await _apply(session, order, nego, Side.seller, now, None, is_auto=True, lines=answers)


async def expire_due(session: AsyncSession, now: datetime) -> int:
    """Scheduler job: offers nobody answered in time cancel the order (reason offer_expired)."""
    due = list(
        await session.scalars(
            select(Negotiation)
            .where(
                Negotiation.status.in_([NegotiationStatus.awaiting_buyer, NegotiationStatus.awaiting_seller]),
                Negotiation.expires_at <= now,
            )
            .with_for_update(skip_locked=True)
            .options(selectinload(Negotiation.offers))
        )
    )
    for nego in due:
        order = await order_svc.load(session, nego.order_id, lock=True)
        if order is None or order.status != OrderStatus.negotiating:
            continue
        for offer in nego.offers:
            if offer.response is None:
                offer.response = OfferResponse.expired
        nego.status = NegotiationStatus.expired
        order_svc.apply(order, OrderAction.expire, By.system, now)
        order.cancel_reason = "offer_expired"
        order_svc.log(session, order, "negotiation_expired", None)
    return len(due)


async def get_view(session: AsyncSession, actor: Actor, order_id: uuid.UUID) -> Negotiation:
    order = await order_svc.get_for_actor(session, actor, order_id)
    nego = await load_for_order(session, order.id)
    if nego is None:
        raise NotFound("no_negotiation")
    return nego
