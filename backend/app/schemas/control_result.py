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
    outcome: str  # PASS | PARTIAL | MISSING
    evidence: dict[str, Any] | None
    explanation: str | None
    remediation: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
