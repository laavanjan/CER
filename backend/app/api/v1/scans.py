"""Scans router — endpoints to start and poll ethics review scans (§14.3, §14.4)."""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.limiter import limiter
from app.models.handoff_export import HandoffExport
from app.models.metadata_supplement import MetadataSupplement
from app.models.project import Project
from app.models.scan import Scan
from app.schemas.scan import ScanCreate, ScanRead, ScanSummary, SupplementPatch, SupplementRead

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_scan_or_404(scan_id: uuid.UUID, db: Session) -> Scan:
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


def _get_control_results(scan_id: uuid.UUID, db: Session) -> list:
    from app.models.control_result import ControlResult
    return db.query(ControlResult).filter(ControlResult.scan_id == scan_id).all()


def _get_latest_scan_or_404(db: Session) -> Scan:
    scan = db.query(Scan).order_by(Scan.created_at.desc()).first()
    if not scan:
        raise HTTPException(status_code=404, detail="No scans found")
    return scan


# ---------------------------------------------------------------------------
# Core scan endpoints
# ---------------------------------------------------------------------------

@router.post("/", response_model=ScanRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
def create_scan(request: Request, payload: ScanCreate, db: Session = Depends(get_db)) -> ScanRead:
    """Start a new pipeline scan for a project."""
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    scan = Scan(project_id=payload.project_id)
    db.add(scan)
    db.commit()
    db.refresh(scan)

    from kombu.exceptions import OperationalError as KombuError
    from app.worker.tasks import run_scan
    from app.worker.celery_app import get_fallback_app

    task_args = (
        str(scan.id),
        {
            "project_id": str(project.id),
            "name": project.name,
            "github_url": project.github_url,
            "zip_path": None,
            "assurance_level": project.assurance_level,
            "uses_genai": project.uses_genai,
            "uses_rel_ai": project.uses_rel_ai,
            "registry_version": project.registry_version,
            "vulnerable_users": project.vulnerable_users,
            "rights_affecting": project.rights_affecting,
            "regulated_sector": project.regulated_sector,
            "cross_border_transfer": project.cross_border_transfer,
            "jurisdiction": project.jurisdiction,
            "user_facing": project.user_facing,
        },
    )

    try:
        task = run_scan.delay(*task_args)
    except (KombuError, Exception) as primary_exc:
        fallback = get_fallback_app()
        if fallback is None:
            raise HTTPException(status_code=503, detail="Redis broker unavailable and no fallback configured.") from primary_exc
        try:
            task = fallback.send_task("run_scan", args=task_args)
        except Exception as fallback_exc:
            raise HTTPException(status_code=503, detail="Both primary and fallback Redis brokers are unavailable.") from fallback_exc

    scan.celery_task_id = task.id
    db.commit()
    db.refresh(scan)
    return ScanRead.model_validate(scan)


@router.get("/summaries", response_model=list[ScanSummary])
def list_scan_summaries(db: Session = Depends(get_db)) -> list[ScanSummary]:
    rows = (
        db.query(Scan, Project)
        .join(Project, Project.id == Scan.project_id)
        .order_by(Scan.created_at.desc())
        .all()
    )
    return [
        ScanSummary(scan_id=scan.id, github_url=project.github_url, name=project.name)
        for scan, project in rows
    ]


@router.get("/latest/handoff/certifier")
def get_latest_certifier_handoff(db: Session = Depends(get_db)) -> Any:
    scan = _get_latest_scan_or_404(db)
    handoff = (
        db.query(HandoffExport)
        .filter(HandoffExport.scan_id == scan.id, HandoffExport.target == "certifier")
        .first()
    )
    if not handoff:
        raise HTTPException(status_code=404, detail="Certifier handoff not yet assembled")
    return handoff.payload


@router.get("/{scan_id}", response_model=ScanRead)
def get_scan(scan_id: uuid.UUID, db: Session = Depends(get_db)) -> ScanRead:
    """Get scan status — polled by the frontend progress page."""
    return ScanRead.model_validate(_get_scan_or_404(scan_id, db))


@router.get("/", response_model=list[ScanRead])
def list_scans(project_id: uuid.UUID | None = None, db: Session = Depends(get_db)) -> list[ScanRead]:
    query = db.query(Scan)
    if project_id:
        query = query.filter(Scan.project_id == project_id)
    return [ScanRead.model_validate(s) for s in query.order_by(Scan.created_at.desc()).all()]


# ---------------------------------------------------------------------------
# Results and findings
# ---------------------------------------------------------------------------

@router.get("/{scan_id}/results")
def get_results(scan_id: uuid.UUID, db: Session = Depends(get_db)) -> Any:
    """Full control results with LLM explanations."""
    _get_scan_or_404(scan_id, db)
    results = _get_control_results(scan_id, db)
    return [
        {
            "control_id": r.control_id,
            "outcome": r.outcome,
            "evidence": r.evidence,
            "explanation": r.explanation,
            "remediation": r.remediation,
            "student_summary": r.student_summary,
            "what_is_present": r.what_is_present,
            "what_is_missing": r.what_is_missing,
            "deterministic_explanation": r.deterministic_explanation,
        }
        for r in results
    ]


@router.get("/{scan_id}/findings")
def get_findings(scan_id: uuid.UUID, db: Session = Depends(get_db)) -> Any:
    """Raw plugin findings (audit/debugging). Returns audit log entries for S5."""
    _get_scan_or_404(scan_id, db)
    from app.models.audit_log import AuditLog
    entries = (
        db.query(AuditLog)
        .filter(AuditLog.scan_id == scan_id, AuditLog.stage == "S5_RUNNER")
        .all()
    )
    return [{"stage": e.stage, "event": e.event, "payload": e.payload, "recorded_at": e.recorded_at} for e in entries]


@router.get("/{scan_id}/report")
def get_report(scan_id: uuid.UUID, audience: str = "developer", db: Session = Depends(get_db)) -> Any:
    """Audience-targeted report (developer | student)."""
    _get_scan_or_404(scan_id, db)
    results = _get_control_results(scan_id, db)

    if audience == "student":
        # Student report uses shorter summaries
        from app.models.audit_log import AuditLog
        llm_log = (
            db.query(AuditLog)
            .filter(AuditLog.scan_id == scan_id, AuditLog.stage == "S9_LLM")
            .first()
        )
        return {
            "audience": "student",
            "findings": [
                {
                    "control_id": r.control_id,
                    "outcome": r.outcome,
                    "explanation": r.explanation,
                }
                for r in results
            ],
        }

    return {
        "audience": "developer",
        "findings": [
            {
                "control_id": r.control_id,
                "outcome": r.outcome,
                "evidence": r.evidence,
                "explanation": r.explanation,
                "remediation": r.remediation,
            }
            for r in results
        ],
    }


@router.get("/{scan_id}/sarif")
def get_sarif(scan_id: uuid.UUID, db: Session = Depends(get_db)) -> Any:
    """SARIF 2.1.0 export for GitHub code scanning integration."""
    _get_scan_or_404(scan_id, db)
    handoff = (
        db.query(HandoffExport)
        .filter(HandoffExport.scan_id == scan_id, HandoffExport.target == "reviewer")
        .first()
    )
    if not handoff:
        raise HTTPException(status_code=404, detail="Scan results not yet assembled")

    # Retrieve P9 (SARIF) from the audit log payload or rebuild from control results
    from app.models.audit_log import AuditLog
    assemble_log = (
        db.query(AuditLog)
        .filter(AuditLog.scan_id == scan_id, AuditLog.stage == "S10_ASSEMBLE")
        .first()
    )
    results = _get_control_results(scan_id, db)
    sarif = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "AIGAP Code Ethics Reviewer",
                        "version": "1.0.0",
                        "rules": [{"id": r.control_id, "name": r.control_id} for r in results],
                    }
                },
                "results": [
                    {
                        "ruleId": r.control_id,
                        "level": "warning" if r.outcome in ("partial", "missing") else "note",
                        "message": {"text": r.explanation or r.outcome},
                        "locations": [{"physicalLocation": {"artifactLocation": {"uri": "repository"}}}],
                    }
                    for r in results
                    if r.outcome in ("partial", "missing", "not_evaluable")
                ],
            }
        ],
    }
    return JSONResponse(content=sarif, media_type="application/sarif+json")


@router.get("/{scan_id}/escalation-hints")
def get_escalation_hints(scan_id: uuid.UUID, db: Session = Depends(get_db)) -> Any:
    """Escalation hints detected by S8."""
    scan = _get_scan_or_404(scan_id, db)
    return scan.escalation_hints or []


# ---------------------------------------------------------------------------
# Metadata Supplement endpoints (T3 controls, §6, §14.3)
# ---------------------------------------------------------------------------

@router.get("/{scan_id}/supplement", response_model=list[SupplementRead])
def get_supplement(scan_id: uuid.UUID, db: Session = Depends(get_db)) -> list[SupplementRead]:
    """Get all T3 Metadata Supplement entries for a scan."""
    _get_scan_or_404(scan_id, db)
    entries = db.query(MetadataSupplement).filter(MetadataSupplement.scan_id == scan_id).all()
    return [SupplementRead.model_validate(e) for e in entries]


@router.patch("/{scan_id}/supplement/{control_id}", response_model=SupplementRead)
def patch_supplement(
    scan_id: uuid.UUID,
    control_id: str,
    payload: SupplementPatch,
    db: Session = Depends(get_db),
) -> SupplementRead:
    """Submit a developer-declared file path for a T3 supplement entry.

    Triggers a file-existence check and upgrades status from not_evaluable
    to partial (found) or missing (not found).
    """
    _get_scan_or_404(scan_id, db)
    entry = (
        db.query(MetadataSupplement)
        .filter(
            MetadataSupplement.scan_id == scan_id,
            MetadataSupplement.control_id == control_id,
        )
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Supplement entry not found")

    # Attestation model: temp workspace is gone after scan, so we trust the declaration.
    # Non-empty path = developer attests artefact exists → partial.
    # Empty / None = developer has no artefact → missing.
    declared = (payload.declared_path or "").strip()
    if declared:
        entry.declared_path = declared
        entry.existence_check_result = "declared"
        entry.status_after_supplement = "partial"
    else:
        entry.declared_path = None
        entry.existence_check_result = "not_declared"
        entry.status_after_supplement = "missing"

    entry.completed_at = datetime.now(UTC)
    db.commit()
    db.refresh(entry)
    return SupplementRead.model_validate(entry)


# ---------------------------------------------------------------------------
# Handoff package endpoints (§14.4)
# ---------------------------------------------------------------------------

@router.get("/{scan_id}/handoff/reviewer")
def get_reviewer_handoff(scan_id: uuid.UUID, db: Session = Depends(get_db)) -> Any:
    """Reviewer handoff package including metadata_supplement entries."""
    _get_scan_or_404(scan_id, db)
    handoff = (
        db.query(HandoffExport)
        .filter(HandoffExport.scan_id == scan_id, HandoffExport.target == "reviewer")
        .first()
    )
    if not handoff:
        raise HTTPException(status_code=404, detail="Reviewer handoff not yet assembled")

    # Inject current supplement status (may have been updated by developer)
    supplements = db.query(MetadataSupplement).filter(MetadataSupplement.scan_id == scan_id).all()
    payload = dict(handoff.payload)
    payload["metadata_supplement"] = [
        {
            "control_id": s.control_id,
            "supplement_prompt": s.supplement_prompt,
            "artefact_type_expected": s.artefact_type_expected,
            "declared_path": s.declared_path,
            "existence_check_result": s.existence_check_result,
            "status_after_supplement": s.status_after_supplement,
        }
        for s in supplements
    ]
    return payload


@router.get("/{scan_id}/handoff/certifier")
def get_certifier_handoff(scan_id: uuid.UUID, db: Session = Depends(get_db)) -> Any:
    """Certifier pre-registration package."""
    _get_scan_or_404(scan_id, db)
    handoff = (
        db.query(HandoffExport)
        .filter(HandoffExport.scan_id == scan_id, HandoffExport.target == "certifier")
        .first()
    )
    if not handoff:
        raise HTTPException(status_code=404, detail="Certifier handoff not yet assembled")
    return handoff.payload
