"""Pydantic schemas for ControlResult request/response objects."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ControlResultRead(BaseModel):
    """Per-control outcome returned as part of a report."""

    id: uuid.UUID
    scan_id: uuid.UUID
    control_id: str
    outcome: str  # evidence_found | partial | missing | not_triggered | not_evaluable
    evidence: dict[str, Any] | None
    explanation: str | None
    remediation: str | None
    student_summary: str | None = None
    what_is_present: str | None = None
    what_is_missing: str | None = None
    deterministic_explanation: str | None = None
    llm_outcome: str | None = None
    llm_confidence: float | None = None
    llm_evidence: dict[str, Any] | None = None
    llm_reasoning: str | None = None

    created_at: datetime

    model_config = {"from_attributes": True}
