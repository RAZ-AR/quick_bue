"""What a seller knows about a buyer when answering an offer: history with this seller only."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ClientLink,
    ClientSource,
    Negotiation,
    NegotiationStatus,
    Order,
    OrderLine,
    OrderStatus,
    PriceSource,
)

# Orders that went through: placed and not cancelled or rejected
_LIVE = (
    OrderStatus.placed,
    OrderStatus.confirmed,
    OrderStatus.delivering,
    OrderStatus.delivered,
    OrderStatus.disputed,
    OrderStatus.accepted,
)


@dataclass(frozen=True)
class ClientProfile:
    source: ClientSource | None  # who brought the client; None before the first order
    orders: int  # earlier orders that went through
    accepted_orders: int  # of them received and accepted
    avg_order_amd: int
    first_order_at: datetime | None
    last_order_at: datetime | None
    negotiated_orders: int  # earlier orders that had an offer
    agreed_orders: int  # of them ended with a deal
    avg_discount_bp: int  # average won discount on negotiated lines, weighted by money


async def profile(
    session: AsyncSession, seller_id: uuid.UUID, buyer_id: uuid.UUID, exclude_order_id: uuid.UUID
) -> ClientProfile:
    pair = (Order.seller_id == seller_id, Order.buyer_id == buyer_id, Order.id != exclude_order_id)
    link = await session.scalar(
        select(ClientLink).where(ClientLink.seller_id == seller_id, ClientLink.buyer_id == buyer_id)
    )
    count, avg_total, first_at, last_at = (
        await session.execute(
            select(
                func.count(Order.id),
                func.coalesce(func.avg(Order.total_amd), 0),
                func.min(Order.created_at),
                func.max(Order.created_at),
            ).where(*pair, Order.status.in_(_LIVE))
        )
    ).one()
    accepted = await session.scalar(
        select(func.count(Order.id)).where(*pair, Order.status == OrderStatus.accepted)
    )
    negotiated, agreed = (
        await session.execute(
            select(
                func.count(Negotiation.id),
                func.count(Negotiation.id).filter(Negotiation.status == NegotiationStatus.agreed),
            )
            .join(Order, Order.id == Negotiation.order_id)
            .where(*pair)
        )
    ).one()
    qty = func.coalesce(OrderLine.qty_confirmed, OrderLine.qty_ordered)
    list_sum, won_sum = (
        await session.execute(
            select(
                func.coalesce(func.sum(OrderLine.list_price_amd * qty), 0),
                func.coalesce(func.sum((OrderLine.list_price_amd - OrderLine.final_price_amd) * qty), 0),
            )
            .join(Order, Order.id == OrderLine.order_id)
            .where(
                *pair,
                Order.status.in_(_LIVE),
                OrderLine.price_source == PriceSource.negotiated,
                OrderLine.final_price_amd.is_not(None),
            )
        )
    ).one()
    return ClientProfile(
        source=link.source if link else None,
        orders=count,
        accepted_orders=accepted or 0,
        avg_order_amd=round(avg_total),
        first_order_at=first_at,
        last_order_at=last_at,
        negotiated_orders=negotiated,
        agreed_orders=agreed,
        avg_discount_bp=int(won_sum * 10_000 // list_sum) if list_sum else 0,
    )
