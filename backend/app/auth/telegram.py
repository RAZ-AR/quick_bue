"""Verification of Telegram Login Widget payloads and Mini App initData.

Docs: https://core.telegram.org/widgets/login#checking-authorization
      https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import hashlib
import hmac
import json
import time
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qsl

from app.auth.identity import AuthError, ExternalIdentity, normalize_locale
from app.models import AuthProvider


def _data_check_string(fields: Mapping[str, Any]) -> str:
    return "\n".join(f"{k}={fields[k]}" for k in sorted(fields) if k != "hash")


def _check_age(auth_date: Any, max_age_s: int, now: float | None) -> None:
    try:
        ts = int(auth_date)
    except (TypeError, ValueError) as e:
        raise AuthError("telegram: bad auth_date") from e
    if (now or time.time()) - ts > max_age_s:
        raise AuthError("telegram: auth data expired")


def _identity(user: Mapping[str, Any]) -> ExternalIdentity:
    name = " ".join(p for p in (user.get("first_name"), user.get("last_name")) if p)
    return ExternalIdentity(
        provider=AuthProvider.telegram,
        external_id=str(user["id"]),
        display_name=name,
        username=user.get("username"),
        locale=normalize_locale(user.get("language_code")),
    )


def verify_login_widget(
    data: Mapping[str, Any], bot_token: str, max_age_s: int = 86400, now: float | None = None
) -> ExternalIdentity:
    if not bot_token:
        raise AuthError("telegram: bot token is not configured")
    received = str(data.get("hash", ""))
    fields = {k: v for k, v in data.items() if v is not None}
    secret = hashlib.sha256(bot_token.encode()).digest()
    expected = hmac.new(secret, _data_check_string(fields).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        raise AuthError("telegram: bad signature")
    _check_age(data.get("auth_date"), max_age_s, now)
    return _identity(data)


def verify_init_data(
    init_data: str, bot_token: str, max_age_s: int = 86400, now: float | None = None
) -> ExternalIdentity:
    if not bot_token:
        raise AuthError("telegram: bot token is not configured")
    fields = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
    received = fields.get("hash", "")
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, _data_check_string(fields).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        raise AuthError("telegram: bad signature")
    _check_age(fields.get("auth_date"), max_age_s, now)
    try:
        user = json.loads(fields["user"])
    except (KeyError, json.JSONDecodeError) as e:
        raise AuthError("telegram: initData has no user") from e
    return _identity(user)
