"""Who accepted which version of the offer and the privacy policy."""

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import legal
from app.models import Consent, LegalDoc
from app.models.base import new_id


async def missing(session: AsyncSession, user_id: uuid.UUID) -> list[LegalDoc]:
    rows = await session.execute(select(Consent.document, Consent.version).where(Consent.user_id == user_id))
    return legal.missing({(LegalDoc(d), v) for d, v in rows})


async def accept_current(
    session: AsyncSession,
    user_id: uuid.UUID,
    organization_id: uuid.UUID | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Record acceptance of the current versions; accepting twice keeps the first record."""
    rows = [
        {
            "id": new_id(),
            "user_id": user_id,
            "organization_id": organization_id,
            "document": doc.value,
            "version": version,
            "ip": (ip or "")[:64] or None,
            "user_agent": (user_agent or "")[:300] or None,
        }
        for doc, version in legal.CURRENT_VERSIONS.items()
    ]
    await session.execute(insert(Consent).values(rows).on_conflict_do_nothing())
