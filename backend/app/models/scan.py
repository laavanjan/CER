"""Scan model — represents one pipeline execution against a Project."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.control_result import ControlResult
    from app.models.handoff_export import HandoffExport
    from app.models.metadata_supplement import MetadataSupplement
    from app.models.project import Project


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Audit reproducibility fields (§14.1)
    workspace_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    commit_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    plugin_versions_used: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    escalation_hints: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    cer_observability_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project: Mapped[Project] = relationship("Project", back_populates="scans")
    control_results: Mapped[list[ControlResult]] = relationship(
        "ControlResult", back_populates="scan"
    )
    audit_logs: Mapped[list[AuditLog]] = relationship("AuditLog", back_populates="scan")
    handoff_exports: Mapped[list[HandoffExport]] = relationship(
        "HandoffExport", back_populates="scan"
    )
    metadata_supplements: Mapped[list[MetadataSupplement]] = relationship(
        "MetadataSupplement", back_populates="scan"
    )
