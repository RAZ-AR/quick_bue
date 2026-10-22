import asyncio
from typing import Protocol

from app.auth.identity import AuthError, ExternalIdentity, normalize_locale
from app.models import AuthProvider


class GoogleVerifier(Protocol):
    async def verify(self, token: str) -> ExternalIdentity: ...


class GoogleIdTokenVerifier:
    """Verifies a Google Identity Services ID token (signature, audience, expiry)."""

    def __init__(self, client_id: str) -> None:
        self.client_id = client_id

    async def verify(self, token: str) -> ExternalIdentity:
        if not self.client_id:
            raise AuthError("google: client id is not configured")
        from google.auth.transport import requests as g_requests
        from google.oauth2 import id_token

        try:
            # Fetches Google certs over HTTP (cached by the lib), so keep it off the event loop
            claims = await asyncio.to_thread(
                id_token.verify_oauth2_token, token, g_requests.Request(), self.client_id
            )
        except ValueError as e:
            raise AuthError(f"google: {e}") from e
        if not claims.get("email_verified", False):
            raise AuthError("google: email is not verified")
        return ExternalIdentity(
            provider=AuthProvider.google,
            external_id=claims["sub"],
            display_name=claims.get("name", ""),
            email=claims.get("email"),
            locale=normalize_locale(claims.get("locale")),
        )
