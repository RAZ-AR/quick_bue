import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.config import get_settings

ALGORITHM = "HS256"


def issue_token(user_id: uuid.UUID) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(days=s.jwt_ttl_days)}
    return jwt.encode(payload, s.jwt_secret, algorithm=ALGORITHM)


def read_token(token: str) -> uuid.UUID:
    """Raises jwt.PyJWTError or ValueError on a bad token."""
    payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
    return uuid.UUID(payload["sub"])
