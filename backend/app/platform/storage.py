"""File storage for uploads: a local directory (Docker volume) for now; the keys work for S3/R2 later."""

import uuid
from pathlib import Path

from app.config import get_settings

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
}


def root() -> Path:
    return Path(get_settings().media_dir).resolve()


def save(data: bytes, folder: str, content_type: str) -> str:
    """Store bytes and return the storage key (relative path). Names are random: users never pick paths."""
    key = f"{folder}/{uuid.uuid4().hex}{ALLOWED_TYPES[content_type]}"
    path = root() / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return key


def save_as(key: str, data: bytes) -> str:
    """Store bytes under a key the caller built (still random names, no user input)."""
    path = root() / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return key


def path_of(key: str) -> Path:
    path = (root() / key).resolve()
    if root() not in path.parents:  # never serve anything outside the media root
        raise ValueError("bad storage key")
    return path


def delete(key: str) -> None:
    path_of(key).unlink(missing_ok=True)
