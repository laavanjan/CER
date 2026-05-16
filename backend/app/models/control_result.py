"""ControlResult model — stores per-control PASS/PARTIAL/MISSING outcome for a scan."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.scan import Scan


class ControlResult(Base):
    __tablename__ = "control_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False
    )
    # Control identifier from the registry, e.g. "GOV-01"
    control_id: Mapped[str] = mapped_column(String(50), nullable=False)
    # Deterministic outcome produced by S7
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)  # PASS/PARTIAL/MISSING
    # Serialised list of evidence file paths / snippets
    evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # LLM-generated fields from S9
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)       # developer_explanation
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)       # remediation_steps (JSON)
    student_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    what_is_present: Mapped[str | None] = mapped_column(Text, nullable=True)
    what_is_missing: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_classification: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Deterministic scanner-based explanation (T1 controls only, no LLM)
    deterministic_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    scan: Mapped[Scan] = relationship("Scan", back_populates="control_results")
