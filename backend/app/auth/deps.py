import uuid
from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.tokens import read_token
from app.db import get_session
from app.models import FileKind, FileStatus, Membership, OrgFile, OrgKind, User, VerificationStatus
from app.platform.authz import Actor

_bearer = HTTPBearer(auto_error=False)

Session = Annotated[AsyncSession, Depends(get_session)]


async def _user_from_token(session: AsyncSession, token: str) -> User | None:
    try:
        user_id = read_token(token)
    except (jwt.PyJWTError, ValueError, KeyError):
        return None
    return await session.scalar(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.memberships).selectinload(Membership.organization))
    )


async def current_user(
    session: Session,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not authenticated")
    user = await _user_from_token(session, creds.credentials)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad token")
    return user


async def optional_user(
    session: Session,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User | None:
    """Guests browse the catalog without signing in; a bad token is treated as no token."""
    return await _user_from_token(session, creds.credentials) if creds else None


CurrentUser = Annotated[User, Depends(current_user)]
OptionalUser = Annotated[User | None, Depends(optional_user)]


async def current_actor(
    session: Session,
    user: CurrentUser,
    x_org_id: Annotated[uuid.UUID | None, Header()] = None,
    x_mode: Annotated[OrgKind | None, Header()] = None,
) -> Actor:
    """The organization the user acts for (X-Org-Id, or the only one) and the side they act on (X-Mode)."""
    memberships = user.memberships
    if x_org_id is not None:
        membership = next((m for m in memberships if m.organization_id == x_org_id), None)
        if membership is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member of this organization")
    elif len(memberships) == 1:
        membership = memberships[0]
    elif not memberships:
        raise HTTPException(status.HTTP_409_CONFLICT, "register_company_first")
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "X-Org-Id header is required")
    org = membership.organization
    mode = x_mode or (OrgKind.buyer if org.is_buyer else OrgKind.seller)
    ready = org.verification_status == VerificationStatus.verified or bool(
        await session.scalar(
            select(OrgFile.id)
            .where(
                OrgFile.organization_id == org.id,
                OrgFile.kind == FileKind.state_registration,
                OrgFile.status != FileStatus.rejected,
            )
            .limit(1)
        )
    )
    return Actor(user=user, org=org, membership=membership, mode=mode, buyer_ready=ready)


CurrentActor = Annotated[Actor, Depends(current_actor)]
