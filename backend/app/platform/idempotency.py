"""Idempotency-Key support: a retried request gets the stored response instead of running twice."""

import uuid
from datetime import datetime, timedelta

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import IdempotencyKey

TTL = timedelta(hours=24)


async def replay(
    session: AsyncSession, org_id: uuid.UUID, key: str | None, endpoint: str, now: datetime
) -> IdempotencyKey | None:
    if not key:
        return None
    row = await session.scalar(
        select(IdempotencyKey).where(IdempotencyKey.organization_id == org_id, IdempotencyKey.key == key)
    )
    if row is None or row.created_at < now - TTL or row.endpoint != endpoint:
        return None
    return row


def store(
    session: AsyncSession, org_id: uuid.UUID, key: str | None, endpoint: str, status_code: int, body: object
) -> None:
    if key:
        session.add(
            IdempotencyKey(
                key=key,
                organization_id=org_id,
                endpoint=endpoint,
                status_code=status_code,
                response=jsonable_encoder(body),
            )
        )
