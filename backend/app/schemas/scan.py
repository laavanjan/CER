"""Pydantic schemas for Scan request/response objects."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class ScanCreate(BaseModel):
    """Payload to kick off a new scan for an existing project."""

    project_id: uuid.UUID


class ScanRead(BaseModel):
    """Scan status returned from the API — polled by the frontend stage progress page."""

    id: uuid.UUID
    project_id: uuid.UUID
    # Current pipeline stage, e.g. "S3_AI_DETECT", "COMPLETE", "FAILED"
    status: str
    celery_task_id: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
