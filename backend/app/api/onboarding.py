import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.auth.deps import CurrentActor, CurrentUser, Session
from app.auth.tokens import issue_token
from app.config import get_settings
from app.models import FileKind, Organization, User, VerificationStatus
from app.platform import storage
from app.platform.clock import utcnow
from app.schemas import (
    AddRoleIn,
    CompanyOut,
    DevRegisterIn,
    LookupOut,
    NewOrgIn,
    OrgDetailOut,
    OrgFileOut,
    RequisitesIn,
    ReviewIn,
    TokenOut,
    VerificationOut,
)
from app.services import onboarding, verification

router = APIRouter(tags=["onboarding"])


@router.post("/auth/dev-register", response_model=TokenOut, status_code=201)
async def dev_register(body: DevRegisterIn, session: Session) -> TokenOut:
    """Create a user without Telegram, for local testing of the sign-up flow. Only with DEV_LOGIN=true."""
    if not get_settings().dev_login:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    email = body.email.lower().strip()
    if not email or not body.name.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "name and email are required")
    if await session.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "email_taken")
    user = User(name=body.name.strip(), email=email)
    session.add(user)
    await session.commit()
    return TokenOut(access_token=issue_token(user.id))


@router.get("/registry/lookup", response_model=LookupOut)
async def registry_lookup(
    session: Session, _: CurrentUser, tin: Annotated[str, Query(max_length=20)]
) -> LookupOut:
    r = await onboarding.lookup(session, tin)
    c = r.company
    return LookupOut(
        tin=r.tin,
        found=c is not None,
        already_registered=r.already_registered,
        provider=r.provider,
        unavailable=r.unavailable,
        company=CompanyOut(
            tin=c.tin,
            legal_name=c.legal_name,
            registration_number=c.registration_number,
            legal_address=c.legal_address,
            director_name=c.director_name,
            tax_regime=c.tax_regime,
            active=c.active,
        )
        if c
        else None,
    )


@router.post("/organizations", response_model=OrgDetailOut, status_code=201)
async def create_organization(body: NewOrgIn, session: Session, user: CurrentUser) -> Organization:
    org = await onboarding.create_organization(session, user, onboarding.NewOrganization(**body.model_dump()))
    await session.commit()
    return org


@router.post("/organizations/me/roles", response_model=OrgDetailOut)
async def add_role(body: AddRoleIn, session: Session, actor: CurrentActor) -> Organization:
    org = await onboarding.add_role(session, actor, body.role, body.delivery_address, body.district)
    await session.commit()
    return org


@router.get("/organizations/me", response_model=OrgDetailOut)
async def my_organization(actor: CurrentActor) -> Organization:
    return actor.org


@router.patch("/organizations/me", response_model=OrgDetailOut)
async def update_my_organization(body: RequisitesIn, session: Session, actor: CurrentActor) -> Organization:
    org = await onboarding.update_requisites(session, actor, body.model_dump(exclude_unset=True))
    await session.commit()
    return org


# --- verification -------------------------------------------------------------------------------------


async def _verification_out(session: Session, org: Organization) -> VerificationOut:
    return VerificationOut(
        organization=OrgDetailOut.model_validate(org),
        required=verification.required(org),
        recommended=verification.recommended(org),
        files=[OrgFileOut.model_validate(f) for f in await verification.files_of(session, org.id)],
    )


@router.get("/verification", response_model=VerificationOut)
async def my_verification(session: Session, actor: CurrentActor) -> VerificationOut:
    return await _verification_out(session, actor.org)


@router.post("/verification/files", response_model=OrgFileOut, status_code=201)
async def upload_file(
    session: Session,
    actor: CurrentActor,
    file: UploadFile,
    kind: Annotated[FileKind, Form()],
    expires_on: Annotated[date | None, Form()] = None,
):
    data = await file.read(get_settings().max_upload_mb * 1024 * 1024 + 1)
    f = await verification.upload(
        session, actor, kind, file.filename or "file", file.content_type or "", data, expires_on
    )
    await session.commit()
    return f


@router.delete("/verification/files/{file_id}", status_code=204)
async def delete_file(file_id: uuid.UUID, session: Session, actor: CurrentActor) -> None:
    await verification.remove(session, actor, file_id)
    await session.commit()


@router.post("/verification/submit", response_model=VerificationOut)
async def submit(session: Session, actor: CurrentActor) -> VerificationOut:
    await verification.submit(session, actor)
    await session.commit()
    return await _verification_out(session, actor.org)


@router.get("/files/{file_id}")
async def open_file(file_id: uuid.UUID, session: Session, user: CurrentUser) -> FileResponse:
    f = await verification.file_for_viewer(session, user, file_id)
    return FileResponse(storage.path_of(f.storage_key), media_type=f.content_type, filename=f.file_name)


# --- operator --------------------------------------------------------------------------------------------


@router.get("/admin/verification", response_model=list[VerificationOut])
async def admin_queue(
    session: Session,
    user: CurrentUser,
    status_: Annotated[list[VerificationStatus] | None, Query(alias="status")] = None,
) -> list[VerificationOut]:
    items = await verification.queue(session, user, status_ or [VerificationStatus.pending])
    return [await _verification_out(session, i.org) for i in items]


@router.post("/admin/files/{file_id}/review", response_model=OrgFileOut)
async def admin_review_file(file_id: uuid.UUID, body: ReviewIn, session: Session, user: CurrentUser):
    f = await verification.review_file(session, user, file_id, body.approve, body.note, utcnow())
    await session.commit()
    return f


@router.post("/admin/organizations/{org_id}/review", response_model=OrgDetailOut)
async def admin_review_org(org_id: uuid.UUID, body: ReviewIn, session: Session, user: CurrentUser):
    org = await verification.review_org(session, user, org_id, body.approve, body.note, utcnow())
    await session.commit()
    return org
