"""Controls router — CRUD endpoints for the ethics control registry."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import registry_loader
from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.schemas.control import ControlRead, ControlWrite

router = APIRouter()


@router.get("/info")
def registry_info() -> dict:
    """Return metadata about the active registry version.

    Reads the registry_version setting and returns it alongside compatible
    filename and path fields so the frontend requires no changes.

    Example response:
        { "file": "controls_v2.json", "version": "v2", "path": "../registry/controls_v2.json" }
    """
    version = settings.registry_version
    return {
        "file": f"controls_{version}.json",
        "version": version,
        "path": settings.registry_path,
    }


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
def list_controls(db: Session = Depends(get_db)) -> list[ControlRead]:
    """Return all controls from the registry."""
    return [_to_read(c) for c in registry_loader.load(db)]


@router.get("/{control_id}", response_model=ControlRead)
def get_control(control_id: str, db: Session = Depends(get_db)) -> ControlRead:
    """Return a single control by its ID (e.g. GOV-01)."""
    control = registry_loader.get_control(control_id, db)
    if not control:
        raise HTTPException(status_code=404, detail="Control not found")
    return _to_read(control)


@router.post("/{control_id}", response_model=ControlRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
def create_control(
    request: Request, control_id: str, payload: ControlWrite, db: Session = Depends(get_db)
) -> ControlRead:
    """Create a new control entry in the registry.

    Returns 409 if the ID already exists.
    """
    if registry_loader.get_control(control_id, db):
        raise HTTPException(status_code=409, detail="Control ID already exists")
    raw = registry_loader.upsert_control(control_id, payload.model_dump(), db)
    db.commit()
    return _to_read(raw)


@router.put("/{control_id}", response_model=ControlRead)
def update_control(
    control_id: str, payload: ControlWrite, db: Session = Depends(get_db)
) -> ControlRead:
    """Update an existing control.  Returns 404 if the ID does not exist."""
    if not registry_loader.get_control(control_id, db):
        raise HTTPException(status_code=404, detail="Control not found")
    raw = registry_loader.upsert_control(control_id, payload.model_dump(), db)
    db.commit()
    return _to_read(raw)


@router.delete("/{control_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_control(control_id: str, db: Session = Depends(get_db)) -> None:
    """Delete a control from the registry.  Returns 404 if not found."""
    removed = registry_loader.delete_control(control_id, db)
    if not removed:
        raise HTTPException(status_code=404, detail="Control not found")
    db.commit()

