"""Reports router — endpoints to retrieve scan findings and audit logs."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.control_result import ControlResult
from app.models.scan import Scan
from app.schemas.audit_log import AuditLogRead
from app.schemas.control_result import ControlResultRead

router = APIRouter()


@router.get("/{scan_id}/findings", response_model=list[ControlResultRead])
def get_findings(scan_id: uuid.UUID, db: Session = Depends(get_db)) -> list[ControlResultRead]:
    """Return all per-control findings for a completed scan."""
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    results = (
        db.query(ControlResult)
        .filter(ControlResult.scan_id == scan_id)
        .order_by(ControlResult.control_id)
        .all()
    )
    return [ControlResultRead.model_validate(r) for r in results]


@router.get("/{scan_id}/audit", response_model=list[AuditLogRead])
def get_audit_log(scan_id: uuid.UUID, db: Session = Depends(get_db)) -> list[AuditLogRead]:
    """Return the full append-only audit trail for a scan.

    NOTE: This endpoint is read-only.  No write or delete endpoints exist for
    the audit log — the WORM guarantee is enforced at the application layer.
    """
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    logs = (
        db.query(AuditLog)
        .filter(AuditLog.scan_id == scan_id)
        .order_by(AuditLog.recorded_at)
        .all()
    )
    return [AuditLogRead.model_validate(log) for log in logs]
