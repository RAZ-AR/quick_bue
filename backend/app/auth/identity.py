from dataclasses import dataclass

from app.models import AuthProvider

SUPPORTED_LOCALES = ("hy", "ru", "en")


def normalize_locale(code: str | None) -> str | None:
    if not code:
        return None
    base = code.split("-")[0].lower()
    return base if base in SUPPORTED_LOCALES else None


@dataclass(frozen=True)
class ExternalIdentity:
    """A verified identity coming from an external provider."""

    provider: AuthProvider
    external_id: str
    display_name: str = ""
    username: str | None = None
    email: str | None = None
    locale: str | None = None


class AuthError(Exception):
    pass
