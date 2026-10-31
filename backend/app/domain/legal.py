"""Legal documents a user accepts: the public offer and the personal data policy.

Bump a version when its text changes in a way users must accept again; the app then asks everyone once more.
"""

from app.models import LegalDoc

CURRENT_VERSIONS: dict[LegalDoc, str] = {
    LegalDoc.terms: "2026-10-30",
    LegalDoc.privacy: "2026-10-30",
}


def missing(accepted: set[tuple[LegalDoc, str]]) -> list[LegalDoc]:
    """Documents whose current version the user has not accepted yet."""
    return [doc for doc, version in CURRENT_VERSIONS.items() if (doc, version) not in accepted]
