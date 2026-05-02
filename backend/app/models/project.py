"""Project model — represents a submitted AI system repository for review."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    github_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    assurance_level: Mapped[str] = mapped_column(
        String(50), nullable=False, default="standard"
    )
    # Whether the project declares generative AI usage
    uses_genai: Mapped[bool] = mapped_column(default=False)
    # Whether the project declares reliability/classical AI usage (TF, PyTorch, sklearn, …)
    uses_rel_ai: Mapped[bool] = mapped_column(default=False)
    # Registry version pinned at intake (validated by S1)
    registry_version: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # One project may have many scans over time
    scans: Mapped[list["Scan"]] = relationship(  # noqa: F821
        "Scan", back_populates="project"
    )
