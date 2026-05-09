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
    # Vulnerable user base — triggers ACC-05 + minimum capstone assurance level (S4)
    vulnerable_users: Mapped[bool] = mapped_column(default=False)
    # Rights-affecting decisions (loans, hiring, benefits, medical, legal) — capstone minimum (S4)
    rights_affecting: Mapped[bool] = mapped_column(default=False)
    # Regulated sector (healthcare, finance, insurance, legal) — industrial minimum (S4)
    regulated_sector: Mapped[bool] = mapped_column(default=False)
    # Personal data leaves the country — activates PRV-07 (S4); mismatch checked at S8
    cross_border_transfer: Mapped[bool] = mapped_column(default=False)
    # Operating jurisdiction(s) — affects regulation mapping and evidence bar
    jurisdiction: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Public-facing vs internal — affects ACC-02, ACC-04 (S4)
    user_facing: Mapped[bool] = mapped_column(default=True)
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
