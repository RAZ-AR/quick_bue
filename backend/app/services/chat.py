"""Chat inside an order: the buyer and the seller agree on substitutions, delivery time, defects.

Every message also becomes a notification for the other side (topic "order.message").
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OrderMessage
from app.platform.authz import Actor
from app.platform.errors import NotAllowed, ValidationFailed
from app.platform.outbox import emit
from app.services import notifications
from app.services import orders as order_svc

MAX_LENGTH = 2000


async def list_messages(session: AsyncSession, actor: Actor, order_id: uuid.UUID, now: datetime) -> list:
    order = await order_svc.get_for_actor(session, actor, order_id)
    rows = await session.scalars(
        select(OrderMessage).where(OrderMessage.order_id == order.id).order_by(OrderMessage.at)
    )
    # Reading the chat clears its bell entries
    await notifications.mark_read(session, actor.user, now, order_id=order.id, kind="message")
    return list(rows)


async def post_message(
    session: AsyncSession, actor: Actor, order_id: uuid.UUID, text: str, now: datetime
) -> OrderMessage:
    order = await order_svc.get_for_actor(session, actor, order_id)
    if actor.org.status == "blocked":
        raise NotAllowed("company_blocked")
    text = (text or "").strip()
    if not text:
        raise ValidationFailed([{"field": "text", "code": "required"}])
    if len(text) > MAX_LENGTH:
        raise ValidationFailed([{"field": "text", "code": "too_long"}])
    side = order_svc.side_of(actor, order)
    msg = OrderMessage(order_id=order.id, user_id=actor.user.id, side=str(side), text=text, at=now)
    session.add(msg)
    emit(
        session,
        "order.message",
        order_id=order.id,
        number=order.number,
        buyer_id=order.buyer_id,
        seller_id=order.seller_id,
        by=str(side),
        by_user=actor.user.id,
        text=text[:300],
    )
    await session.flush()
    return msg
