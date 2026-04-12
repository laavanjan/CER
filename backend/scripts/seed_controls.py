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
    """Load controls from JSON and insert any that are not yet in the database."""
    path = registry_path or settings.registry_path

    if not os.path.exists(path):
        print(f"Registry file not found: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path, encoding="utf-8") as fh:
        records: list[dict] = json.load(fh)

    db = SessionLocal()
    try:
        inserted = 0
        skipped = 0
        for rec in records:
            cid = rec.get("id", "")
            if not cid:
                print(f"Skipping record with missing id: {rec}", file=sys.stderr)
                continue

            exists = db.query(Control).filter(Control.control_id == cid).first()
            if exists:
                skipped += 1
                continue

            control = Control(
                id=uuid.uuid4(),
                control_id=cid,
                pillar=rec.get("pillar", ""),
                tier=int(rec.get("tier", 1)),
                auto=bool(rec.get("auto", False)),
                plugins=rec.get("plugins", []),
                pass_criteria=rec.get("pass_criteria", ""),
                partial_criteria=rec.get("partial_criteria", ""),
                missing_criteria=rec.get("missing_criteria", ""),
            )
            db.add(control)
            inserted += 1

        db.commit()
        print(f"Seed complete: {inserted} inserted, {skipped} skipped.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
