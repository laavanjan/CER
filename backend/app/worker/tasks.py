"""Celery tasks — the main `run_scan` task orchestrates the full pipeline.

Each task updates the Scan.status field as it progresses through stages S1–S11
so the frontend progress page can poll for live updates.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from app import registry_loader
from app.core.config import settings
from app.core.database import SessionLocal
import app.models  # noqa: F401 — registers all mappers before relationship resolution
from app.models.scan import Scan
from app.pipeline import (
    s1_intake,
    s2_manifest,
    s3_ai_detect,
    s4_filter,
    s5_runner,
    s6_tag,
    s7_evidence,
    s8_honesty,
    s9_llm,
    s10_assemble,
    s11_audit,
)
from app.pipeline.models import ProjectProfile
from app.worker.celery_app import celery_app


def _update_scan_status(scan_id: uuid.UUID, status: str) -> None:
    """Update the scan status in the database."""
    with SessionLocal() as db:
        scan = db.get(Scan, scan_id)
        if scan:
            scan.status = status
            db.commit()


@celery_app.task(bind=True, name="run_scan", max_retries=3)
def run_scan(self: Any, scan_id: str, project_data: dict[str, Any]) -> dict[str, Any]:
    """Orchestrate the full S1–S11 ethics review pipeline for a single scan.

    Parameters
    ----------
    scan_id:      UUID string of the Scan record.
    project_data: Serialised project profile dict from the API.

    Returns
    -------
    Dict containing the assembled output packages (P1–P6).
    """
    scan_uuid = uuid.UUID(scan_id)
    db = SessionLocal()

    try:
        scan = db.get(Scan, scan_uuid)
        if not scan:
            raise ValueError(f"Scan {scan_id} not found in database.")

        # Mark scan as started
        scan.status = "S1_INTAKE"
        scan.started_at = datetime.now(UTC)
        db.commit()

        # Build profile from serialised data
        profile = ProjectProfile(
            project_id=project_data["project_id"],
            name=project_data["name"],
            github_url=project_data.get("github_url"),
            zip_path=project_data.get("zip_path"),
            assurance_level=project_data.get("assurance_level", "standard"),
            uses_genai=project_data.get("uses_genai", False),
            registry_version=project_data.get("registry_version", settings.registry_version),
        )

        # S1 — Intake validation
        profile = s1_intake.run(profile, settings.registry_path)
        s11_audit.record(db, scan_uuid, "S1_INTAKE", "Intake validated", payload={"profile": project_data})

        # S2 — Manifest
        scan.status = "S2_MANIFEST"
        db.commit()
        repo_root, manifest = s2_manifest.run(profile)
        s11_audit.record(db, scan_uuid, "S2_MANIFEST", f"Manifest built: {len(manifest)} files")

        # S3 — AI detection
        scan.status = "S3_AI_DETECT"
        db.commit()
        profile = s3_ai_detect.run(profile, manifest, repo_root)
        s11_audit.record(
            db, scan_uuid, "S3_AI_DETECT",
            "AI signals detected",
            payload={
                "gen_triggered": getattr(profile, "gen_triggered", False),
                "rel_triggered": getattr(profile, "rel_triggered", False),
            },
        )

        # S4 — Filter controls
        scan.status = "S4_FILTER"
        db.commit()
        all_controls = registry_loader.load(db)
        active_controls, t3_queue = s4_filter.run(profile, all_controls)
        s11_audit.record(
            db, scan_uuid, "S4_FILTER",
            f"Filtered {len(active_controls)} active controls, {len(t3_queue)} T3 queued",
        )

        # S5 — Plugin runner
        scan.status = "S5_RUNNER"
        db.commit()
        raw_findings = s5_runner.run(active_controls, manifest, str(repo_root))
        s11_audit.record(
            db, scan_uuid, "S5_RUNNER",
            f"Plugin runner produced {len(raw_findings)} raw findings",
        )

        # S6 — Tag
        scan.status = "S6_TAG"
        db.commit()
        tagged_findings = s6_tag.run(raw_findings, all_controls)
        s11_audit.record(db, scan_uuid, "S6_TAG", "Overlay tags applied")

        # S7 — Evidence mapping (deterministic)
        scan.status = "S7_EVIDENCE"
        db.commit()
        evidence_results = s7_evidence.run(tagged_findings, active_controls)
        s11_audit.record(
            db, scan_uuid, "S7_EVIDENCE",
            "Evidence outcomes determined",
            payload={
                r.control_id: r.outcome for r in evidence_results
            },
        )

        # S8 — Honesty check
        scan.status = "S8_HONESTY"
        db.commit()
        escalation_hints = s8_honesty.run(profile)
        s11_audit.record(
            db, scan_uuid, "S8_HONESTY",
            f"{len(escalation_hints)} escalation hints produced",
        )

        # S9 — LLM annotation
        scan.status = "S9_LLM"
        db.commit()
        annotations = s9_llm.run(evidence_results, settings.anthropic_api_key, settings.gemini_api_key)
        s11_audit.record(db, scan_uuid, "S9_LLM", "LLM annotations generated")

        # S10 — Assemble packages
        scan.status = "S10_ASSEMBLE"
        db.commit()
        output_packages = s10_assemble.run(profile, evidence_results, escalation_hints, annotations)
        s11_audit.record(db, scan_uuid, "S10_ASSEMBLE", "Output packages assembled")

        # Persist ControlResult rows
        from app.models.control_result import ControlResult
        ann_map = {a.control_id: a for a in annotations}
        for result in evidence_results:
            ann = ann_map.get(result.control_id)
            cr = ControlResult(
                scan_id=scan_uuid,
                control_id=result.control_id,
                outcome=result.outcome,
                evidence={"paths": result.evidence_paths},
                explanation=ann.explanation if ann else None,
                remediation=ann.remediation if ann else None,
            )
            db.add(cr)

        scan.status = "COMPLETE"
        scan.completed_at = datetime.now(UTC)
        db.commit()

        s11_audit.record(db, scan_uuid, "S11_AUDIT", "Scan completed successfully")

        return output_packages

    except Exception as exc:
        scan = db.get(Scan, scan_uuid)
        if scan:
            scan.status = "FAILED"
            db.commit()
        raise self.retry(exc=exc, countdown=30) from exc
    finally:
        db.close()
