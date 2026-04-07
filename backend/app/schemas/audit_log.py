"""Pydantic schemas for AuditLog response objects (read-only — no write schema)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    """Single audit-log entry returned from the API."""

    id: uuid.UUID
    scan_id: uuid.UUID
    stage: str
    event: str
    payload: dict[str, Any] | None
    recorded_at: datetime

    model_config = {"from_attributes": True}
