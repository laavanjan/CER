"""Controls router — CRUD endpoints for the ethics control registry."""

from fastapi import APIRouter, HTTPException, status

from app import registry_loader
from app.schemas.control import ControlRead, ControlWrite

router = APIRouter()


def _to_read(raw: dict) -> ControlRead:
    return ControlRead(
        id=raw["id"],
        pillar=raw.get("pillar", ""),
        tier=int(raw.get("tier", 1)),
        auto=bool(raw.get("auto", False)),
        plugins=raw.get("plugins", []),
        pass_criteria=raw.get("pass_criteria", ""),
        partial_criteria=raw.get("partial_criteria", ""),
        missing_criteria=raw.get("missing_criteria", ""),
    )


@router.get("/", response_model=list[ControlRead])
def list_controls() -> list[ControlRead]:
    """Return all controls from the registry."""
    return [_to_read(c) for c in registry_loader.load()]


@router.get("/{control_id}", response_model=ControlRead)
def get_control(control_id: str) -> ControlRead:
    """Return a single control by its ID (e.g. GOV-01)."""
    control = registry_loader.get_control(control_id)
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    return _to_read(control)


@router.post("/{control_id}", response_model=ControlRead, status_code=status.HTTP_201_CREATED)
def create_control(control_id: str, payload: ControlWrite) -> ControlRead:
    """Create a new control entry in the registry.

    Returns 409 if the ID already exists.
    """
    if registry_loader.get_control(control_id):
        raise HTTPException(status_code=409, detail="Control ID already exists")
    raw = registry_loader.upsert_control(control_id, payload.model_dump())
    return _to_read(raw)


@router.put("/{control_id}", response_model=ControlRead)
def update_control(control_id: str, payload: ControlWrite) -> ControlRead:
    """Update an existing control.  Returns 404 if the ID does not exist."""
    if not registry_loader.get_control(control_id):
        raise HTTPException(status_code=404, detail="Control not found")
    raw = registry_loader.upsert_control(control_id, payload.model_dump())
    return _to_read(raw)


@router.delete("/{control_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_control(control_id: str) -> None:
    """Delete a control from the registry.  Returns 404 if not found."""
    removed = registry_loader.delete_control(control_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Control not found")
