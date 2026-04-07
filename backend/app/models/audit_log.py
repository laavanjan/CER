"""AuditLog model — append-only WORM log of every pipeline decision (S11)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False
    )
    # Pipeline stage that generated this entry, e.g. "S7_EVIDENCE"
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    # Short human-readable description of the decision
    event: Mapped[str] = mapped_column(Text, nullable=False)
    # Arbitrary structured payload (control_id, outcome, confidence, etc.)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    scan: Mapped["Scan"] = relationship("Scan", back_populates="audit_logs")  # noqa: F821

    # NOTE: This table is insert-only.  No UPDATE or DELETE routes exist for AuditLog.
