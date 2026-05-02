"""Projects router — CRUD endpoints for AI system projects."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectRead

router = APIRouter()


@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
def create_project(request: Request, payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectRead:
    """Create a new project record.

    Registry version is stored as-is; S1 will validate it when a scan is started.
    """
    project = Project(
        name=payload.name,
        github_url=str(payload.github_url) if payload.github_url else None,
        assurance_level=payload.assurance_level,
        uses_genai=payload.uses_genai,
        uses_rel_ai=payload.uses_rel_ai,
        registry_version=settings.registry_version,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return ProjectRead.model_validate(project)


@router.get("/", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)) -> list[ProjectRead]:
    """List all projects."""
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return [ProjectRead.model_validate(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: uuid.UUID, db: Session = Depends(get_db)) -> ProjectRead:
    """Get a single project by ID."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectRead.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    """Delete a project (and cascade-delete its scans)."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
