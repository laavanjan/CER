"""Celery tasks — the main `run_scan` task orchestrates the full S1–S11 pipeline."""

import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def _log_stage(stage: str, summary: str, details: dict[str, Any] | None = None) -> None:
    logger.info("")
    logger.info("============================== %s ==============================", stage)
    logger.info("")
    logger.info("%s", summary)
    if details:
        for key, value in details.items():
            logger.info("- %s: %s", key, value)
    logger.info("")

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
from app.pipeline.models import ProjectProfile, SupplementEntry
from app.worker.celery_app import celery_app


@celery_app.task(bind=True, name="run_scan", max_retries=3)
def run_scan(self: Any, scan_id: str, project_data: dict[str, Any]) -> dict[str, Any]:
    """Orchestrate the full S1–S11 ethics review pipeline."""
    scan_uuid = uuid.UUID(scan_id)
    db = SessionLocal()

    try:
        scan = db.get(Scan, scan_uuid)
        if not scan:
            raise ValueError(f"Scan {scan_id} not found in database.")

        pipeline_start = time.perf_counter()
        scan.status = "S1_INTAKE"
        scan.started_at = datetime.now(UTC)
        db.commit()

        profile = ProjectProfile(
            project_id=project_data["project_id"],
            name=project_data["name"],
            github_url=project_data.get("github_url"),
            zip_path=project_data.get("zip_path"),
            assurance_level=project_data.get("assurance_level", "ug"),
            uses_genai=project_data.get("uses_genai", False),
            registry_version=project_data.get("registry_version", settings.registry_version),
            uses_rel_ai=project_data.get("uses_rel_ai", False),
            vulnerable_users=project_data.get("vulnerable_users", False),
            rights_affecting=project_data.get("rights_affecting", False),
            regulated_sector=project_data.get("regulated_sector", False),
            cross_border_transfer=project_data.get("cross_border_transfer", False),
            jurisdiction=project_data.get("jurisdiction"),
            user_facing=project_data.get("user_facing", True),
        )

        # S1 — Intake validation
        t = time.perf_counter()
        profile = s1_intake.run(profile, settings.registry_path)
        d = round(time.perf_counter() - t, 2)
        s11_audit.record(db, scan_uuid, "S1_INTAKE", "Intake validated",
                         payload={"profile": project_data, "duration_s": d})
        _log_stage("S1_INTAKE", "Intake validated", {"duration_s": d})

        # S2 — Repository ingestion (now returns commit_sha + workspace_hash)
        scan.status = "S2_MANIFEST"
        db.commit()
        t = time.perf_counter()
        repo_root, manifest, commit_sha, workspace_hash = s2_manifest.run(profile)
        d = round(time.perf_counter() - t, 2)
        scan.commit_sha = commit_sha
        scan.workspace_hash = workspace_hash
        db.commit()
        s11_audit.record(db, scan_uuid, "S2_MANIFEST",
                         f"Manifest built: {len(manifest)} files",
                         payload={"commit_sha": commit_sha, "workspace_hash": workspace_hash, "duration_s": d})
        _log_stage("S2_MANIFEST", f"Manifest built: {len(manifest)} files",
               {"commit_sha": commit_sha, "workspace_hash": workspace_hash, "duration_s": d})

        # S3 — AI detection
        scan.status = "S3_AI_DETECT"
        db.commit()
        t = time.perf_counter()
        profile = s3_ai_detect.run(profile, manifest, repo_root)
        d = round(time.perf_counter() - t, 2)
        s11_audit.record(db, scan_uuid, "S3_AI_DETECT", "AI signals detected",
                         payload={"gen_triggered": profile.gen_triggered,
                                  "rel_triggered": profile.rel_triggered, "duration_s": d})
        _log_stage("S3_AI_DETECT", "AI signals detected",
               {"gen_triggered": profile.gen_triggered, "rel_triggered": profile.rel_triggered, "duration_s": d})

        # S4 — Control activation & routing (now returns supplement_entries)
        scan.status = "S4_FILTER"
        db.commit()
        t = time.perf_counter()
        all_controls = registry_loader.load(db)
        active_controls, t3_queue, supplement_entries = s4_filter.run(profile, all_controls)
        d = round(time.perf_counter() - t, 2)

        # Persist T3 supplement entries to DB
        from app.models.metadata_supplement import MetadataSupplement
        for entry in supplement_entries:
            db.add(MetadataSupplement(
                scan_id=scan_uuid,
                control_id=entry.control_id,
                supplement_prompt=entry.supplement_prompt,
                artefact_type_expected=entry.artefact_type_expected,
            ))

        # Store cer_observability_summary on scan
        scan.cer_observability_summary = {
            "T1": len([c for c in active_controls if c.get("cer_observability") == "T1"]),
            "T2": len([c for c in active_controls if c.get("cer_observability") == "T2"]),
            "T3": len(t3_queue),
        }
        db.commit()
        s11_audit.record(db, scan_uuid, "S4_FILTER",
                         f"{len(active_controls)} active (T1/T2), {len(t3_queue)} T3 supplement queued",
                         payload={"duration_s": d})
        _log_stage("S4_FILTER",
               f"{len(active_controls)} active (T1/T2), {len(t3_queue)} T3 supplement queued",
               {"duration_s": d})

        # S5 — Plugin runner (30s timeouts per plugin)
        scan.status = "S5_RUNNER"
        db.commit()
        t = time.perf_counter()
        raw_findings = s5_runner.run(active_controls, manifest, str(repo_root))
        d = round(time.perf_counter() - t, 2)
        timed_out = sum(1 for f in raw_findings if f.timed_out)
        s11_audit.record(db, scan_uuid, "S5_RUNNER",
                         f"{len(raw_findings)} raw findings ({timed_out} timed out)",
                         payload={"duration_s": d})
        _log_stage("S5_RUNNER", f"{len(raw_findings)} raw findings ({timed_out} timed out)",
               {"duration_s": d})

        # S6 — GEN/REL signal routing
        scan.status = "S6_TAG"
        db.commit()
        t = time.perf_counter()
        tagged_findings = s6_tag.run(raw_findings)
        d = round(time.perf_counter() - t, 2)
        s11_audit.record(db, scan_uuid, "S6_TAG", "Overlay tags applied", payload={"duration_s": d})
        _log_stage("S6_TAG", "Overlay tags applied", {"duration_s": d})

        # S7 — Evidence mapping (full decision tree)
        scan.status = "S7_EVIDENCE"
        db.commit()
        t = time.perf_counter()
        evidence_results = s7_evidence.run(
            tagged_findings, active_controls, supplement_entries,
            profile_user_facing=profile.user_facing,
        )
        d = round(time.perf_counter() - t, 2)
        s11_audit.record(db, scan_uuid, "S7_EVIDENCE", "Evidence outcomes determined",
                         payload={r.control_id: r.outcome for r in evidence_results} | {"duration_s": d})
        _log_stage("S7_EVIDENCE", "Evidence outcomes determined",
               {"results": len(evidence_results), "duration_s": d})

        # S8 — Escalation check
        scan.status = "S8_HONESTY"
        db.commit()
        t = time.perf_counter()
        escalation_hints = s8_honesty.run(profile)
        d = round(time.perf_counter() - t, 2)
        scan.escalation_hints = [
            {"control_id": h.control_id, "hint": h.hint, "severity": h.severity}
            for h in escalation_hints
        ]
        db.commit()
        s11_audit.record(db, scan_uuid, "S8_HONESTY",
                         f"{len(escalation_hints)} escalation hints",
                         payload={"duration_s": d})
        _log_stage("S8_HONESTY", f"{len(escalation_hints)} escalation hints", {"duration_s": d})

        # S9 — LLM explanation (structured JSON, temperature=0)
        scan.status = "S9_LLM"
        db.commit()
        t = time.perf_counter()
        annotations = s9_llm.run(
            evidence_results,
            anthropic_api_key=settings.anthropic_api_key,
            assurance_level=profile.assurance_level,
            ollama_api_key=getattr(settings, "ollama_api_key", ""),
            gemini_api_key=getattr(settings, "gemini_api_key", ""),
        )
        d = round(time.perf_counter() - t, 2)
        s11_audit.record(db, scan_uuid, "S9_LLM", "LLM annotations generated",
                         payload={"count": len(annotations), "duration_s": d})
        _log_stage("S9_LLM", "LLM annotations generated",
               {"count": len(annotations), "duration_s": d})

        # S10 — Assemble all packages (P1–P10)
        scan.status = "S10_ASSEMBLE"
        db.commit()
        t = time.perf_counter()
        output_packages = s10_assemble.run(
            profile, evidence_results, escalation_hints, annotations,
            supplement_entries, workspace_hash=workspace_hash, commit_sha=commit_sha,
        )
        d = round(time.perf_counter() - t, 2)

        # Persist ControlResult rows
        import json as _json
        from app.models.control_result import ControlResult
        ann_map = {a.control_id: a for a in annotations}
        for result in evidence_results:
            a = ann_map.get(result.control_id)
            db.add(ControlResult(
                scan_id=scan_uuid,
                control_id=result.control_id,
                outcome=result.outcome,
                evidence={"paths": result.evidence_paths, "gaps": result.gaps},
                explanation=a.developer_explanation if a else None,
                remediation=_json.dumps(a.remediation_steps) if a else None,
                student_summary=a.student_summary if a else None,
                what_is_present=a.what_is_present if a else None,
                what_is_missing=a.what_is_missing if a else None,
                doc_classification=a.doc_classification if a else None,
            ))

        # Persist handoff exports
        from app.models.handoff_export import HandoffExport
        for target, pkg_key in [("reviewer", "p7"), ("certifier", "p8")]:
            db.add(HandoffExport(
                scan_id=scan_uuid,
                project_id=uuid.UUID(profile.project_id),
                target=target,
                registry_version=profile.registry_version,
                commit_sha=commit_sha,
                payload=output_packages[pkg_key],
            ))

        _log_stage("S10_ASSEMBLE", "Output packages assembled", {"duration_s": d})

        total = round(time.perf_counter() - pipeline_start, 2)
        scan.status = "COMPLETE"
        scan.completed_at = datetime.now(UTC)
        db.commit()

        s11_audit.record(db, scan_uuid, "S11_AUDIT", "Scan completed",
                         payload={"total_duration_s": total, "workspace_hash": workspace_hash})

        _log_stage("S11_AUDIT", "Scan completed",
               {"total_duration_s": total, "workspace_hash": workspace_hash})

        return output_packages

    except Exception as exc:
        scan = db.get(Scan, scan_uuid)
        if scan:
            scan.status = "FAILED"
            db.commit()
        raise self.retry(exc=exc, countdown=30) from exc
    finally:
        db.close()
