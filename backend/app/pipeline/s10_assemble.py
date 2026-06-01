"""S10 — Report Assembly: assemble all output packages (§11).

Output packages:
  P1  — Executive Summary
  P2  — Full Findings (per-control, developer-facing)
  P3  — Remediation Plan (non-pass controls only)
  P4  — Escalation Report
  P5  — Audit Trail Reference
  P6  — Machine-Readable JSON
  P7  — Reviewer Handoff Package (§11.1)
  P8  — Certifier Pre-Registration Package (§11.2)
  P9  — SARIF 2.1.0 Export
  P10 — Metadata Supplement entries (T3 controls)

Governing invariants respected:
  I-05: CER produces observations only — no Reviewer/Certifier statuses in any package.
  I-13: Coverage stats reported per tier separately.
  I-14: Every non-evidence_found finding carries recommended_next_artifact.
"""

import json
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.pipeline.models import (
    EscalationHint,
    EvidenceResult,
    LLMAnnotation,
    ProjectProfile,
    SupplementEntry,
)


def build_deterministic_explanation(r: EvidenceResult) -> str:
    """Build a deterministic explanation for T1 controls from raw scanner output.

    No LLM involved — purely derived from S5/S7 evidence data.
    Only meaningful for T1 (code-observable) controls.
    """
    if r.cer_observability != "T1":
        return ""

    parts: list[str] = []

    # Outcome summary
    if r.outcome == "evidence_found":
        parts.append(f"Scanner found evidence for {r.control_id} in {len(r.evidence_paths)} file(s).")
    elif r.outcome == "partial":
        parts.append(f"Scanner found partial evidence for {r.control_id} in {len(r.evidence_paths)} file(s).")
    elif r.outcome == "missing":
        parts.append(f"Scanner found no evidence for {r.control_id} after checking all code files.")
    else:
        parts.append(f"Control {r.control_id} was not evaluated (outcome: {r.outcome}).")

    # Files with evidence
    if r.evidence_paths:
        file_list = ", ".join(f"`{p}`" for p in r.evidence_paths[:5])
        suffix = f" and {len(r.evidence_paths) - 5} more" if len(r.evidence_paths) > 5 else ""
        parts.append(f"Evidence files: {file_list}{suffix}.")

    # Line-level matches
    if r.evidence_locations:
        sample = r.evidence_locations[:3]
        loc_strs = [f"`{loc.file}:{loc.line}` — {loc.reason}" for loc in sample]
        parts.append(f"Matched locations: {'; '.join(loc_strs)}.")

    # Gaps
    if r.gaps:
        gap_list = "; ".join(r.gaps[:3])
        parts.append(f"What was not found: {gap_list}.")

    # Confidence
    if r.raw_findings:
        max_conf = max((f.confidence for f in r.raw_findings), default=0.0)
        parts.append(f"Scanner confidence: {round(max_conf * 100)}%.")

    # Severity
    if r.severity not in ("none", "info"):
        parts.append(f"Risk level: {r.severity}.")

    return " ".join(parts)

_SARIF_LEVEL = {
    "critical": "error",
    "major": "error",
    "minor": "warning",
    "action_required": "note",
    "info": "note",
    "none": "none",
}


def _annotation_map(annotations: list[LLMAnnotation]) -> dict[str, LLMAnnotation]:
    return {a.control_id: a for a in annotations}


_ETYPE_CACHE: dict[str, dict[str, list[str]]] | None = None


def _load_etype_map() -> dict[str, dict[str, list[str]]]:
    global _ETYPE_CACHE
    if _ETYPE_CACHE is not None:
        return _ETYPE_CACHE

    path = Path(settings.etype_map_path)
    if not path.exists():
        _ETYPE_CACHE = {}
        return _ETYPE_CACHE

    try:
        _ETYPE_CACHE = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        _ETYPE_CACHE = {}
    return _ETYPE_CACHE


def _e_type_candidates(control_id: str, fallback: list[str]) -> list[str]:
    entry = _load_etype_map().get(control_id) or {}
    for key in ("available", "partial", "required_union"):
        values = entry.get(key) or []
        if values:
            return values
    return fallback


def run(
    profile: ProjectProfile,
    evidence_results: list[EvidenceResult],
    escalation_hints: list[EscalationHint],
    annotations: list[LLMAnnotation],
    supplement_entries: list[SupplementEntry],
    artefact_type_by_control: dict[str, str] | None = None,
    workspace_hash: str = "",
    commit_sha: str = "",
) -> dict[str, Any]:
    ann = _annotation_map(annotations)

    # Coverage summary per tier (I-13 — never aggregate across tiers)
    t1 = [r for r in evidence_results if r.cer_observability == "T1"]
    t2 = [r for r in evidence_results if r.cer_observability == "T2"]
    t3 = [r for r in evidence_results if r.cer_observability == "T3"]

    def _counts(results: list[EvidenceResult]) -> dict:
        return {
            "total": len(results),
            "evidence_found": sum(1 for r in results if r.outcome == "evidence_found"),
            "partial": sum(1 for r in results if r.outcome == "partial"),
            "missing": sum(1 for r in results if r.outcome == "missing"),
            "not_evaluable": sum(1 for r in results if r.outcome == "not_evaluable"),
            "not_triggered": sum(1 for r in results if r.outcome == "not_triggered"),
        }

    # -- P1: Executive Summary --------------------------------------------------
    p1 = {
        "project_name": profile.name,
        "registry_version": profile.registry_version,
        "assurance_level": profile.assurance_level,
        "commit_sha": commit_sha,
        "workspace_hash": workspace_hash,
        "escalation_count": len(escalation_hints),
        "gen_signals_detected": profile.gen_triggered,
        "rel_signals_detected": profile.rel_triggered,
        "coverage": {
            "T1_code_observable": _counts(t1),
            "T2_document_observable": _counts(t2),
            "T3_design_only": _counts(t3),
        },
    }

    # -- P2: Full Findings (developer report) ------------------------------------
    p2 = []
    for r in evidence_results:
        a = ann.get(r.control_id)
        finding: dict[str, Any] = {
            "control_id": r.control_id,
            "cer_observability": r.cer_observability,
            "outcome": r.outcome,
            "severity": r.severity,
            "overlay_relevance": r.overlay_relevance,
            "evidence_paths": r.evidence_paths,
            "gaps": r.gaps,
            "recommended_next_artifact": r.recommended_next_artifact,
            "deterministic_explanation": build_deterministic_explanation(r),
        }
        if a:
            finding["developer_explanation"] = a.developer_explanation
            finding["student_summary"] = a.student_summary
            finding["what_is_present"] = a.what_is_present
            finding["what_is_missing"] = a.what_is_missing
            finding["doc_classification"] = a.doc_classification
        p2.append(finding)

    # -- P3: Remediation Plan (non-evidence_found controls) ----------------------
    p3 = []
    for r in evidence_results:
        if r.outcome not in ("partial", "missing"):
            continue
        a = ann.get(r.control_id)
        p3.append({
            "control_id": r.control_id,
            "outcome": r.outcome,
            "severity": r.severity,
            "remediation_steps": a.remediation_steps if a else [],
            "recommended_next_artifact": r.recommended_next_artifact,
        })

    # -- P4: Escalation Report --------------------------------------------------
    p4 = [
        {"control_id": h.control_id, "hint": h.hint, "severity": h.severity}
        for h in escalation_hints
    ]

    # -- P5: Audit Trail Reference ----------------------------------------------
    p5 = {
        "note": "Full audit trail stored in audit_logs table. Query by scan_id.",
        "workspace_hash": workspace_hash,
        "commit_sha": commit_sha,
        "stages_executed": ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10"],
    }

    # -- P6: Machine-Readable JSON ----------------------------------------------
    p6 = {
        "schema_version": "2.0",
        "project": {"name": profile.name, "registry_version": profile.registry_version},
        "findings": [
            {
                "control_id": r.control_id,
                "cer_observability": r.cer_observability,
                "outcome": r.outcome,
                "severity": r.severity,
                "overlay_relevance": r.overlay_relevance,
                "doc_classification": ann[r.control_id].doc_classification if r.control_id in ann else None,
                "recommended_next_artifact": r.recommended_next_artifact,
            }
            for r in evidence_results
        ],
        "escalations": p4,
    }

    # -- P7: Reviewer Handoff Package (§11.1) -----------------------------------
    p7: dict[str, Any] = {
        "scan_id": profile.project_id,  # scan_id injected by caller
        "project_id": profile.project_id,
        "registry_version": profile.registry_version,
        "commit_sha": commit_sha,
        "assurance_level": profile.assurance_level,
        "escalation_hints": p4,
        "gen_signals_detected": profile.gen_triggered,
        "rel_signals_detected": profile.rel_triggered,
        "metadata_supplement": [
            {
                "control_id": s.control_id,
                "supplement_prompt": s.supplement_prompt,
                "artefact_type_expected": s.artefact_type_expected,
                "declared_path": s.declared_path,
                "existence_check_result": s.existence_check_result,
                "status_after_supplement": s.status_after_supplement,
            }
            for s in supplement_entries
        ],
        "controls": [
            {
                "control_id": r.control_id,
                "cer_observability": r.cer_observability,
                "code_status": r.outcome,
                "severity": r.severity,
                "confidence": "high" if r.outcome == "evidence_found" else ("medium" if r.outcome == "partial" else "low"),
                "evidence_found": r.evidence_paths,
                "gaps": r.gaps,
                "recommended_next_artifact": r.recommended_next_artifact,
                "overlay_relevance": r.overlay_relevance,
            }
            for r in evidence_results
        ],
    }

    # -- P8: Certifier Pre-Registration Package (§11.2) -------------------------
    def _artifact_type(path: str) -> str:
        lower = path.lower()
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if "test" in lower:
            return "test_file"
        if ext in ("yaml", "yml", "toml", "json", "env", "cfg", "ini", "txt", "lock"):
            return "config_file"
        if ext in ("md", "rst", "pdf", "docx", "html"):
            return "doc_file"
        if ext == "ipynb":
            return "notebook"
        return "source_file"

    p8_artefacts = []
    for r in evidence_results:
        expected_type = (artefact_type_by_control or {}).get(r.control_id)
        fallback_candidates = [expected_type] if expected_type else r.recommended_next_artifact
        e_type_candidates = _e_type_candidates(r.control_id, fallback_candidates)
        for path in r.evidence_paths:
            p8_artefacts.append({
                "control_id": r.control_id,
                "file_path": path,
                "sha256": "",  # populated from manifest by caller if needed
                "artifact_type": _artifact_type(path),
                "e_type_candidates": e_type_candidates,
            })

    severity_counts: dict[str, int] = {"critical": 0, "major": 0, "minor": 0, "action_required": 0}
    for r in evidence_results:
        if r.severity in severity_counts:
            severity_counts[r.severity] += 1

    p8 = {
        "schema_version": "2.0",
        "project_id": profile.project_id,
        "registry_version": profile.registry_version,
        "commit_sha": commit_sha,
        "review_status": "COMPLETE",
        "assurance_level": profile.assurance_level,
        "risk_indicators": {
            "severity_counts": severity_counts,
            "escalation_hints": p4,
        },
        "findings": [
            {
                "control_id": r.control_id,
                "cer_observability": r.cer_observability,
                "outcome": r.outcome,
                "severity": r.severity,
                "gaps": r.gaps,
                "issue_summary": ann[r.control_id].what_is_missing if r.control_id in ann else "",
            }
            for r in evidence_results
        ],
        "evidence_artefacts": p8_artefacts,
    }

    # -- P9: SARIF 2.1.0 Export -------------------------------------------------
    sarif_results = []
    for r in evidence_results:
        if r.severity in ("none", "info") or r.outcome in ("evidence_found", "not_triggered"):
            continue
        a = ann.get(r.control_id)
        sarif_results.append({
            "ruleId": r.control_id,
            "level": _SARIF_LEVEL.get(r.severity, "note"),
            "message": {"text": a.developer_explanation if a else r.outcome},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": path},
                    }
                }
                for path in r.evidence_paths[:3]
            ] or [{"physicalLocation": {"artifactLocation": {"uri": "repository"}}}],
        })

    p9 = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "AIGAP Code Ethics Reviewer",
                        "version": "1.0.0",
                        "rules": [
                            {"id": r.control_id, "name": r.control_id}
                            for r in evidence_results
                        ],
                    }
                },
                "results": sarif_results,
            }
        ],
    }

    # -- P10: Metadata Supplement entries (T3) ----------------------------------
    p10 = [
        {
            "control_id": s.control_id,
            "supplement_prompt": s.supplement_prompt,
            "artefact_type_expected": s.artefact_type_expected,
            "status": s.status_after_supplement,
        }
        for s in supplement_entries
    ]

    return {
        "p1": p1, "p2": p2, "p3": p3, "p4": p4,
        "p5": p5, "p6": p6, "p7": p7, "p8": p8,
        "p9": p9, "p10": p10,
    }
