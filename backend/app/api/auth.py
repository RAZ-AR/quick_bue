from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.auth.deps import CurrentUser, Session
from app.auth.tokens import issue_token
from app.config import get_settings
from app.models import User
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
async def me(user: CurrentUser) -> User:
    return user
