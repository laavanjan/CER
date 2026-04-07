"""Pydantic schemas for Project request/response objects."""

import uuid
from datetime import datetime

from pydantic import BaseModel, HttpUrl


class ProjectCreate(BaseModel):
    """Payload accepted when creating a new project at /intake."""

    name: str
    github_url: HttpUrl | None = None
    assurance_level: str = "standard"
    uses_genai: bool = False
    # Must match the version string embedded in controls_v1.json (validated by S1)
    registry_version: str


class ProjectRead(BaseModel):
    """Project returned from the API."""

    id: uuid.UUID
    name: str
    github_url: str | None
    assurance_level: str
    uses_genai: bool
    registry_version: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
