"""MetadataSupplement model — T3 design-only control supplement entries (§6)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.scan import Scan


class MetadataSupplement(Base):
    __tablename__ = "metadata_supplements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False
    )
    control_id: Mapped[str] = mapped_column(String(50), nullable=False)
    supplement_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    artefact_type_expected: Mapped[str] = mapped_column(String(10), nullable=False)

    # Developer-provided fields (null until submitted via PATCH)
    declared_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # found | not_found | not_declared | pending
    existence_check_result: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    # partial | missing | not_evaluable
    status_after_supplement: Mapped[str] = mapped_column(
        String(20), nullable=False, default="not_evaluable"
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    scan: Mapped[Scan] = relationship("Scan", back_populates="metadata_supplements")
