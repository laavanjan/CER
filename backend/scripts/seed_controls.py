"""Seed controls — read registry/controls_v2.json and insert into the controls table.

Usage (from the backend directory):
    python -m scripts.seed_controls

The script is idempotent: records that already exist (matched by control_id) are
skipped so it is safe to run multiple times.
"""

import json
import os
import sys
import uuid
from pathlib import Path

# Allow running as a standalone script from the backend directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.control import Control  # noqa: E402


def seed(registry_path: str | None = None) -> None:
    """Load controls from JSON and upsert into the database.

    Existing records are updated (not skipped) so that changes to cer_observability,
    supplement_prompt, artefact_type_expected and other fields are reflected after re-run.
    """
    path = registry_path or settings.registry_path

    if not os.path.exists(path):
        print(f"Registry file not found: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path, encoding="utf-8") as fh:
        records: list[dict] = json.load(fh)

    db = SessionLocal()
    try:
        inserted = 0
        updated = 0
        for rec in records:
            cid = rec.get("id", "")
            if not cid:
                print(f"Skipping record with missing id: {rec}", file=sys.stderr)
                continue

            control = db.query(Control).filter(Control.control_id == cid).first()
            if control is None:
                control = Control(id=uuid.uuid4(), control_id=cid)
                db.add(control)
                inserted += 1
            else:
                updated += 1

            control.pillar = rec.get("pillar", "")
            control.tier = int(rec.get("tier", 1))
            control.auto = bool(rec.get("auto", False))
            control.plugins = rec.get("plugins", [])
            control.pass_criteria = rec.get("pass_criteria", "")
            control.partial_criteria = rec.get("partial_criteria", "")
            control.missing_criteria = rec.get("missing_criteria", "")
            control.cer_observability = rec.get("cer_observability", "T1")
            control.supplement_prompt = rec.get("supplement_prompt", "")
            control.artefact_type_expected = rec.get("artefact_type_expected", "")

        db.commit()
        print(f"Seed complete: {inserted} inserted, {updated} updated.")
    except Exception as exc:
        db.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
