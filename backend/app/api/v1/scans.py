"""Scans router — endpoints to start and poll ethics review scans."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.limiter import limiter
from app.models.project import Project
from app.models.scan import Scan
from app.schemas.scan import ScanCreate, ScanRead

router = APIRouter()


@router.post("/", response_model=ScanRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
def create_scan(request: Request, payload: ScanCreate, db: Session = Depends(get_db)) -> ScanRead:
    """Start a new pipeline scan for a project.

    Enqueues the `run_scan` Celery task and returns immediately with the scan ID
    so the frontend can start polling.
    """
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    scan = Scan(project_id=payload.project_id)
    db.add(scan)
    db.commit()
    db.refresh(scan)

    # Import here to avoid circular imports at module level
    from app.worker.tasks import run_scan

    task = run_scan.delay(
        str(scan.id),
        {
            "project_id": str(project.id),
            "name": project.name,
            "github_url": project.github_url,
            "zip_path": None,
            "assurance_level": project.assurance_level,
            "uses_genai": project.uses_genai,
            "registry_version": project.registry_version,
        },
    )
    scan.celery_task_id = task.id
    db.commit()
    db.refresh(scan)

    return ScanRead.model_validate(scan)


@router.get("/{scan_id}", response_model=ScanRead)
def get_scan(scan_id: uuid.UUID, db: Session = Depends(get_db)) -> ScanRead:
    """Get the current status of a scan — polled by the frontend stage progress page."""
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanRead.model_validate(scan)


@router.get("/", response_model=list[ScanRead])
def list_scans(
    project_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
) -> list[ScanRead]:
    """List all scans, optionally filtered by project."""
    query = db.query(Scan)
    if project_id:
        query = query.filter(Scan.project_id == project_id)
    scans = query.order_by(Scan.created_at.desc()).all()
    return [ScanRead.model_validate(s) for s in scans]
