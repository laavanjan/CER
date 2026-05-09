"""Pydantic schemas for Scan request/response objects."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class ScanCreate(BaseModel):
    project_id: uuid.UUID


class ScanRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    celery_task_id: str | None
    commit_sha: str | None = None
    workspace_hash: str | None = None
    cer_observability_summary: dict | None = None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SupplementRead(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    control_id: str
    supplement_prompt: str
    artefact_type_expected: str
    declared_path: str | None
    existence_check_result: str
    status_after_supplement: str
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SupplementPatch(BaseModel):
    declared_path: str
