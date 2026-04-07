"""S11 — Audit: write every pipeline decision to append-only WORM audit log.

Responsibilities
----------------
1. Receive the audit entry data (stage, event, payload).
2. INSERT a new row into the audit_logs table.
3. NEVER update or delete rows — this table is insert-only.

This stage is called after every pipeline stage decision to ensure full
traceability.  The WORM guarantee is enforced at the application layer
(no UPDATE/DELETE routes exist) and should be reinforced by DB policy.
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record(
    db: Session,
    scan_id: uuid.UUID,
    stage: str,
    event: str,
    payload: dict[str, Any] | None = None,
) -> AuditLog:
    """Insert a single audit-log entry (WORM — never update or delete).

    Parameters
    ----------
    db:       Open SQLAlchemy session.
    scan_id:  UUID of the scan this entry belongs to.
    stage:    Pipeline stage label, e.g. "S7_EVIDENCE".
    event:    Human-readable description of the decision.
    payload:  Optional structured data to store alongside the event.

    Returns
    -------
    The newly created AuditLog ORM instance.
    """
    entry = AuditLog(
        scan_id=scan_id,
        stage=stage,
        event=event,
        payload=payload,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def record_bulk(
    db: Session,
    scan_id: uuid.UUID,
    entries: list[dict[str, Any]],
) -> list[AuditLog]:
    """Insert multiple audit-log entries in a single transaction.

    Parameters
    ----------
    db:       Open SQLAlchemy session.
    scan_id:  UUID of the scan.
    entries:  List of dicts with keys: stage, event, payload (optional).

    Returns
    -------
    List of newly created AuditLog ORM instances.
    """
    logs = [
        AuditLog(
            scan_id=scan_id,
            stage=e["stage"],
            event=e["event"],
            payload=e.get("payload"),
        )
        for e in entries
    ]
    db.add_all(logs)
    db.commit()
    return logs
