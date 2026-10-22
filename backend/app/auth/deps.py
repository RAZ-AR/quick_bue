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
from app.models import Membership, User
from app.platform.authz import Actor

_bearer = HTTPBearer(auto_error=False)

Session = Annotated[AsyncSession, Depends(get_session)]


async def current_user(
    session: Session,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not authenticated")
    try:
        user_id = read_token(creds.credentials)
    except (jwt.PyJWTError, ValueError, KeyError) as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad token") from e
    user = await session.scalar(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.memberships).selectinload(Membership.organization))
    )
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unknown user")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def current_actor(
    user: CurrentUser,
    x_org_id: Annotated[uuid.UUID | None, Header()] = None,
) -> Actor:
    """The organization the user acts for: X-Org-Id, or the only one they belong to."""
    memberships = user.memberships
    if x_org_id is not None:
        membership = next((m for m in memberships if m.organization_id == x_org_id), None)
        if membership is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member of this organization")
    elif len(memberships) == 1:
        membership = memberships[0]
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "X-Org-Id header is required")
    return Actor(user=user, org=membership.organization, membership=membership)


CurrentActor = Annotated[Actor, Depends(current_actor)]
