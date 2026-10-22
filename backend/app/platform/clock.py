"""One place for "now", so tests can move time (expiry, auto-accept, delivery dates)."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

YEREVAN = ZoneInfo("Asia/Yerevan")


def utcnow() -> datetime:
    return datetime.now(UTC)


def local(dt: datetime) -> datetime:
    return dt.astimezone(YEREVAN)
