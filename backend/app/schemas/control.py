"""Pydantic schemas for Control registry items."""

from pydantic import BaseModel


class ControlRead(BaseModel):
    """A single control definition returned by the API."""

    id: str
    pillar: str
    tier: int
    auto: bool
    plugins: list[str]
    pass_criteria: str
    partial_criteria: str
    missing_criteria: str


class ControlWrite(BaseModel):
    """Payload for creating or updating a control."""

    pillar: str
    tier: int
    auto: bool
    plugins: list[str]
    pass_criteria: str
    partial_criteria: str
    missing_criteria: str
