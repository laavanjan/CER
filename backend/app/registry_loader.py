"""Registry loader — queries the controls table in PostgreSQL.

All public functions accept a SQLAlchemy ``Session`` as their first argument so
callers (API routes, pipeline tasks) can share the same database transaction.

The helper ``_to_dict`` converts an ORM row back to the plain dict that the rest
of the codebase (pipeline stages, schemas) already understands.
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.control import Control

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _to_dict(row: Control) -> dict[str, Any]:
    """Convert a Control ORM instance to the canonical control dict."""
    return {
        "id": row.control_id,
        "pillar": row.pillar,
        "tier": row.tier,
        "auto": row.auto,
        "plugins": row.plugins,
        "pass_criteria": row.pass_criteria,
        "partial_criteria": row.partial_criteria,
        "missing_criteria": row.missing_criteria,
        "cer_observability": row.cer_observability,
        "supplement_prompt": row.supplement_prompt,
        "artefact_type_expected": row.artefact_type_expected,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load(db: Session) -> list[dict[str, Any]]:
    """Return all controls from the database, ordered by control_id."""
    rows = db.query(Control).order_by(Control.control_id).all()
    return [_to_dict(r) for r in rows]


def get_control(control_id: str, db: Session) -> dict[str, Any] | None:
    """Return a single control dict by its business ID, or None if not found."""
    row = db.query(Control).filter(Control.control_id == control_id).first()
    return _to_dict(row) if row else None


def upsert_control(
    control_id: str,
    data: dict[str, Any],
    db: Session,
) -> dict[str, Any]:
    """Create or update a control by its business ID.

    Parameters
    ----------
    control_id: Business identifier, e.g. "GOV-01".
    data:       Fields to set (must not include ``"id"``).
    db:         Active SQLAlchemy session (caller is responsible for commit).

    Returns
    -------
    The updated or newly created control dict.
    """
    row = db.query(Control).filter(Control.control_id == control_id).first()
    if row is None:
        row = Control(id=uuid.uuid4(), control_id=control_id)

    row.pillar = data.get("pillar", "")
    row.tier = int(data.get("tier", 1))
    row.auto = bool(data.get("auto", False))
    row.plugins = data.get("plugins", [])
    row.pass_criteria = data.get("pass_criteria", "")
    row.partial_criteria = data.get("partial_criteria", "")
    row.missing_criteria = data.get("missing_criteria", "")
    row.cer_observability = data.get("cer_observability", "T1")
    row.supplement_prompt = data.get("supplement_prompt", "")
    row.artefact_type_expected = data.get("artefact_type_expected", "")

    db.flush()
    return _to_dict(row)


def delete_control(control_id: str, db: Session) -> bool:
    """Remove a control by its business ID.

    Returns
    -------
    True if the control was found and deleted, False if it did not exist.
    """
    row = db.query(Control).filter(Control.control_id == control_id).first()
    if row is None:
        return False
    db.delete(row)
    db.flush()
    return True
