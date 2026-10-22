from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.auth import service
from app.auth.deps import CurrentUser, Session
from app.auth.google import GoogleIdTokenVerifier
from app.auth.identity import AuthError
from app.auth.telegram import verify_login_widget
from app.auth.tokens import issue_token
from app.config import get_settings
from app.models import FileKind, FileStatus, OrgFile, User, VerificationStatus
from app.platform.clock import utcnow
from app.schemas import DevLoginIn, MeOut, TokenOut

router = APIRouter(tags=["auth"])


@router.post("/auth/dev-login", response_model=TokenOut)
async def dev_login(body: DevLoginIn, session: Session) -> TokenOut:
    """Sign in as an existing (seeded) user by email. Only with DEV_LOGIN=true, never in prod."""
    if not get_settings().dev_login:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    user = await session.scalar(select(User).where(User.email == body.email.lower().strip()))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such user")
    return TokenOut(access_token=issue_token(user.id))


@router.get("/me", response_model=MeOut)
async def me(user: CurrentUser, session: Session) -> MeOut:
    out = MeOut.model_validate(user)
    for m in out.memberships:
        m.buyer_ready = m.organization.verification_status == VerificationStatus.verified or bool(
            await session.scalar(
                select(OrgFile.id)
                .where(
                    OrgFile.organization_id == m.organization.id,
                    OrgFile.kind == FileKind.state_registration,
                    OrgFile.status != FileStatus.rejected,
                )
                .limit(1)
            )
        )
    return out


# --- real sign-in: e-mail code, Google, Telegram --------------------------------------------------------


class EmailStartIn(BaseModel):
    email: str
    lang: str = "hy"


class EmailVerifyIn(BaseModel):
    email: str
    code: str


class GoogleIn(BaseModel):
    credential: str  # ID token from Google Identity Services


@router.post("/auth/email/start")
async def email_start(body: EmailStartIn, session: Session) -> dict:
    code = await service.start_email_login(session, body.email, body.lang, utcnow())
    await session.commit()
    s = get_settings()
    # Without a real mailer in development the code is shown on screen; never in production
    show = s.dev_login and s.mail_provider == "console"
    return {"sent": True, "dev_code": code if show else None}


@router.post("/auth/email/verify", response_model=TokenOut)
async def email_verify(body: EmailVerifyIn, session: Session) -> TokenOut:
    user = await service.finish_email_login(session, body.email, body.code, utcnow())
    await session.commit()
    return TokenOut(access_token=issue_token(user.id))


@router.post("/auth/google", response_model=TokenOut)
async def google(body: GoogleIn, session: Session) -> TokenOut:
    try:
        ident = await GoogleIdTokenVerifier(get_settings().google_client_id).verify(body.credential)
    except AuthError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e
    user = await service.login_or_register(session, ident)
    await session.commit()
    return TokenOut(access_token=issue_token(user.id))


@router.post("/auth/telegram", response_model=TokenOut)
async def telegram(body: dict, session: Session) -> TokenOut:
    """Telegram Login Widget payload (id, first_name, ..., auth_date, hash)."""
    s = get_settings()
    try:
        ident = verify_login_widget(body, s.telegram_bot_token, s.telegram_auth_max_age_s)
    except AuthError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e
    user = await service.login_or_register(session, ident)
    await session.commit()
    return TokenOut(access_token=issue_token(user.id))
