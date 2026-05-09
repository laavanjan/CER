"""Pydantic schemas for Project request/response objects."""

import uuid
from datetime import datetime

from pydantic import BaseModel, HttpUrl


class ProjectCreate(BaseModel):
    """Payload accepted when creating a new project at /intake."""

    name: str
    github_url: HttpUrl | None = None
    assurance_level: str = "ug"
    uses_genai: bool = False
    uses_rel_ai: bool = False
    vulnerable_users: bool = False
    rights_affecting: bool = False
    regulated_sector: bool = False
    cross_border_transfer: bool = False
    jurisdiction: str | None = None
    user_facing: bool = True


class ProjectRead(BaseModel):
    """Project returned from the API."""

    id: uuid.UUID
    name: str
    github_url: str | None
    assurance_level: str
    uses_genai: bool
    uses_rel_ai: bool
    vulnerable_users: bool
    rights_affecting: bool
    regulated_sector: bool
    cross_border_transfer: bool
    jurisdiction: str | None
    user_facing: bool
    registry_version: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
