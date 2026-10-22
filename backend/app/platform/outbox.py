"""Write side effects into the outbox in the caller's transaction (docs/03-architecture.md §3.6)."""

import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OutboxEvent


def jsonable(payload: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(payload, default=str))


def emit(session: AsyncSession, topic: str, **payload: Any) -> None:
    session.add(OutboxEvent(topic=topic, payload=jsonable(payload)))


def ids(*values: uuid.UUID) -> list[str]:
    return [str(v) for v in values]
