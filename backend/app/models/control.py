"""Control model — represents a single ethics control definition."""

import uuid

from sqlalchemy import Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Control(Base):
    """Persistent representation of an ethics control from the registry."""

    __tablename__ = "controls"
    __table_args__ = (UniqueConstraint("control_id", name="uq_controls_control_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Business identifier, e.g. "GOV-01"
    control_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    pillar: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    tier: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    auto: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # List of plugin IDs stored as a JSONB array, e.g. ["governance_scanner"]
    plugins: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    pass_criteria: Mapped[str] = mapped_column(Text, nullable=False, default="")
    partial_criteria: Mapped[str] = mapped_column(Text, nullable=False, default="")
    missing_criteria: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # CER observability tier: "T1" (code), "T2" (document), "T3" (design/supplement)
    cer_observability: Mapped[str] = mapped_column(String(10), nullable=False, default="T1")
    supplement_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    artefact_type_expected: Mapped[str] = mapped_column(String(100), nullable=False, default="")
