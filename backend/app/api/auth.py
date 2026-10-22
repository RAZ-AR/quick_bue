from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select

from app.auth import service
from app.auth.deps import CurrentUser, Session, is_buyer_ready
from app.auth.google import GoogleIdTokenVerifier
from app.auth.identity import AuthError
from app.auth.telegram import verify_login_widget
from app.auth.tokens import issue_token
from app.config import get_settings
from app.models import User
from app.platform import ratelimit
from app.platform.clock import utcnow
from app.platform.errors import ValidationFailed
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
    for m, membership in zip(out.memberships, user.memberships, strict=True):
        m.buyer_ready = await is_buyer_ready(session, membership.organization)
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


# Per client and for the whole site: every code is an e-mail sent from our account
CODES_PER_IP_HOUR = 20
CODES_PER_SITE_HOUR = 300


def _client_ip(request: Request) -> str:
    # Caddy and nginx append to X-Forwarded-For; the first entry is the browser
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "?")


@router.post("/auth/email/start")
async def email_start(body: EmailStartIn, session: Session, request: Request) -> dict:
    if not (
        await ratelimit.hit(f"login-ip:{_client_ip(request)}", CODES_PER_IP_HOUR, 3600)
        and await ratelimit.hit("login-site", CODES_PER_SITE_HOUR, 3600)
    ):
        raise service.TooManyRequests("too_many_codes", "try again later")
    code = await service.start_email_login(session, body.email, body.lang, utcnow())
    await session.commit()
    s = get_settings()
    # Without a real mailer in development the code is shown on screen; never in production
    show = s.dev_login and s.mail_provider == "console"
    return {"sent": True, "dev_code": code if show else None}


@router.post("/auth/email/verify", response_model=TokenOut)
async def email_verify(body: EmailVerifyIn, session: Session) -> TokenOut:
    try:
        user = await service.finish_email_login(session, body.email, body.code, utcnow())
    except ValidationFailed:
        await session.commit()  # keep the counted attempt / the burnt code
        raise
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
