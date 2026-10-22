"""Files an organization uploads to prove who it is and that its food is safe (operator reviews them)."""

import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPk, str_enum


class FileKind(StrEnum):
    state_registration = "state_registration"  # extract from the state register of legal entities
    food_safety_registration = "food_safety_registration"  # Food Safety Inspection Body registration
    conformity = "conformity"  # EAEU certificate / declaration of conformity
    veterinary = "veterinary"  # veterinary-sanitary certificate (meat, dairy, fish)
    phytosanitary = "phytosanitary"  # plant products
    haccp = "haccp"
    alcohol_license = "alcohol_license"
    other = "other"


class FileStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class OrgFile(UUIDPk, Timestamped, Base):
    __tablename__ = "org_files"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[FileKind] = mapped_column(str_enum(FileKind))
    file_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    storage_key: Mapped[str] = mapped_column(String(500))  # path inside MEDIA_DIR (S3 key later)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    status: Mapped[FileStatus] = mapped_column(str_enum(FileStatus), default=FileStatus.pending)
    expires_on: Mapped[date | None] = mapped_column(Date)
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
