"""Verification: the company uploads documents, an operator approves them, the seller can start trading."""

import uuid
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import (
    AuditLog,
    FileKind,
    FileStatus,
    Organization,
    OrgFile,
    OrgKind,
    OrgStatus,
    User,
    VerificationStatus,
)
from app.platform import storage
from app.platform.authz import Action, Actor
from app.platform.errors import Conflict, NotAllowed, NotFound, ValidationFailed

# What an operator needs to see before a company is verified
REQUIRED: dict[OrgKind, list[FileKind]] = {
    OrgKind.seller: [FileKind.state_registration],
    OrgKind.buyer: [FileKind.state_registration],
}
# Shown as optional slots; for food sellers they are what buyers trust
RECOMMENDED: dict[OrgKind, list[FileKind]] = {
    OrgKind.seller: [
        FileKind.food_safety_registration,
        FileKind.conformity,
        FileKind.haccp,
        FileKind.veterinary,
        FileKind.phytosanitary,
        FileKind.alcohol_license,
    ],
    OrgKind.buyer: [],
}


async def files_of(session: AsyncSession, org_id: uuid.UUID) -> list[OrgFile]:
    rows = await session.scalars(
        select(OrgFile).where(OrgFile.organization_id == org_id).order_by(OrgFile.created_at)
    )
    return list(rows)


async def upload(
    session: AsyncSession,
    actor: Actor,
    kind: FileKind,
    file_name: str,
    content_type: str,
    data: bytes,
    expires_on: date | None = None,
) -> OrgFile:
    actor.require(Action.org_staff)
    if content_type not in storage.ALLOWED_TYPES:
        raise ValidationFailed([{"code": "file_type_not_allowed", "allowed": list(storage.ALLOWED_TYPES)}])
    if len(data) > get_settings().max_upload_mb * 1024 * 1024:
        raise ValidationFailed([{"code": "file_too_large", "max_mb": get_settings().max_upload_mb}])
    if not data:
        raise ValidationFailed([{"code": "file_empty"}])
    key = storage.save(data, f"org/{actor.org.id}", content_type)
    f = OrgFile(
        organization_id=actor.org.id,
        kind=kind,
        file_name=file_name[:255] or "file",
        content_type=content_type,
        size_bytes=len(data),
        storage_key=key,
        uploaded_by=actor.user.id,
        expires_on=expires_on,
    )
    session.add(f)
    await session.flush()
    return f


async def remove(session: AsyncSession, actor: Actor, file_id: uuid.UUID) -> None:
    actor.require(Action.org_staff)
    f = await session.get(OrgFile, file_id)
    if f is None or f.organization_id != actor.org.id:
        raise NotFound("file_not_found")
    if f.status == FileStatus.approved:
        raise Conflict("file_approved", "approved files stay as evidence")
    storage.delete(f.storage_key)
    await session.delete(f)


async def submit(session: AsyncSession, actor: Actor) -> Organization:
    """Ask an operator to check the company. Every required kind needs a file that was not rejected."""
    actor.require(Action.org_staff)
    files = await files_of(session, actor.org.id)
    missing = [
        k
        for k in REQUIRED[actor.org.kind]
        if not any(f.kind == k and f.status != FileStatus.rejected for f in files)
    ]
    if missing:
        raise ValidationFailed([{"code": "file_required", "kind": k} for k in missing])
    if actor.org.verification_status == VerificationStatus.verified:
        return actor.org
    actor.org.verification_status = VerificationStatus.pending
    actor.org.review_note = None
    return actor.org


# --- operator side ---------------------------------------------------------------------------------------


def require_admin(user: User) -> None:
    if not user.is_platform_admin:
        raise NotAllowed("operators_only")


@dataclass
class QueueItem:
    org: Organization
    files: list[OrgFile]


async def queue(session: AsyncSession, admin: User, statuses: list[VerificationStatus]) -> list[QueueItem]:
    require_admin(admin)
    orgs = await session.scalars(
        select(Organization)
        .where(Organization.verification_status.in_(statuses))
        .order_by(Organization.updated_at)
    )
    return [QueueItem(o, await files_of(session, o.id)) for o in orgs]


async def review_file(
    session: AsyncSession, admin: User, file_id: uuid.UUID, approve: bool, note: str | None, now: datetime
) -> OrgFile:
    require_admin(admin)
    f = await session.get(OrgFile, file_id)
    if f is None:
        raise NotFound("file_not_found")
    f.status = FileStatus.approved if approve else FileStatus.rejected
    f.review_note = note
    f.reviewed_by = admin.id
    f.reviewed_at = now
    session.add(
        AuditLog(actor_user_id=admin.id, action=f"file.{f.status}", entity="org_file", entity_id=f.id,
                 payload={"note": note, "kind": f.kind})
    )  # fmt: skip
    return f


async def review_org(
    session: AsyncSession, admin: User, org_id: uuid.UUID, approve: bool, note: str | None, now: datetime
) -> Organization:
    require_admin(admin)
    org = await session.get(Organization, org_id)
    if org is None:
        raise NotFound("organization_not_found")
    if approve:
        files = await files_of(session, org.id)
        missing = [
            k
            for k in REQUIRED[org.kind]
            if not any(f.kind == k and f.status == FileStatus.approved for f in files)
        ]
        if missing:
            raise ValidationFailed([{"code": "approve_required_files_first", "kind": k} for k in missing])
        org.verification_status = VerificationStatus.verified
        org.verified_at = now
        if org.kind == OrgKind.seller and org.status == OrgStatus.pending:
            org.status = OrgStatus.active  # the seller can trade now
    else:
        org.verification_status = VerificationStatus.rejected
    org.review_note = note
    session.add(
        AuditLog(actor_user_id=admin.id, action=f"org.{org.verification_status}", entity="organization",
                 entity_id=org.id, payload={"note": note})
    )  # fmt: skip
    return org


async def file_for_viewer(session: AsyncSession, user: User, file_id: uuid.UUID) -> OrgFile:
    """The company's own members and operators may open a file; nobody else."""
    f = await session.get(OrgFile, file_id)
    if f is None:
        raise NotFound("file_not_found")
    if not user.is_platform_admin and not any(
        m.organization_id == f.organization_id for m in user.memberships
    ):
        raise NotFound("file_not_found")
    return f
