"""S10 — Assemble: assemble 6 output packages from S7/S8/S9 data.

Responsibilities
----------------
1. Combine EvidenceResult, EscalationHint and LLMAnnotation data.
2. Produce 6 output packages:
   P1 – Executive Summary
   P2 – Full Findings (per-control detail)
   P3 – Remediation Plan
   P4 – Escalation Report (discrepancies and hints)
   P5 – Audit Trail Reference (summary pointing to AuditLog entries)
   P6 – Machine-Readable JSON (for downstream tooling)
"""

from typing import Any

from app.pipeline.models import (
    EscalationHint,
    EvidenceResult,
    LLMAnnotation,
    ProjectProfile,
)


def _build_annotation_map(annotations: list[LLMAnnotation]) -> dict[str, LLMAnnotation]:
    return {a.control_id: a for a in annotations}


def run(
    profile: ProjectProfile,
    evidence_results: list[EvidenceResult],
    escalation_hints: list[EscalationHint],
    annotations: list[LLMAnnotation],
) -> dict[str, Any]:
    """Assemble all output packages into a single structured dict.

    Parameters
    ----------
    profile:           Project profile.
    evidence_results:  Per-control outcomes from S7.
    escalation_hints:  Honesty-check hints from S8.
    annotations:       LLM annotations from S9.

    Returns
    -------
    Dict with keys p1 through p6, each containing the relevant package.
    """
    ann_map = _build_annotation_map(annotations)

    # -- P1: Executive Summary --------------------------------------------------
    total = len(evidence_results)
    pass_count = sum(1 for r in evidence_results if r.outcome == "PASS")
    partial_count = sum(1 for r in evidence_results if r.outcome == "PARTIAL")
    missing_count = sum(1 for r in evidence_results if r.outcome == "MISSING")
    p1 = {
        "project_name": profile.name,
        "registry_version": profile.registry_version,
        "assurance_level": profile.assurance_level,
        "total_controls": total,
        "pass": pass_count,
        "partial": partial_count,
        "missing": missing_count,
        "escalation_count": len(escalation_hints),
    }

    # -- P2: Full Findings ------------------------------------------------------
    p2 = []
    for r in evidence_results:
        ann = ann_map.get(r.control_id)
        p2.append(
            {
                "control_id": r.control_id,
                "outcome": r.outcome,
                "evidence_paths": r.evidence_paths,
                "explanation": ann.explanation if ann else None,
            }
        )

    # -- P3: Remediation Plan ---------------------------------------------------
    p3 = [
        {
            "control_id": r.control_id,
            "outcome": r.outcome,
            "remediation": ann_map[r.control_id].remediation
            if r.control_id in ann_map
            else None,
        }
        for r in evidence_results
        if r.outcome in ("PARTIAL", "MISSING")
    ]

    # -- P4: Escalation Report --------------------------------------------------
    p4 = [
        {
            "control_id": h.control_id,
            "hint": h.hint,
            "severity": h.severity,
        }
        for h in escalation_hints
    ]

    # -- P5: Audit Trail Reference ----------------------------------------------
    p5 = {
        "note": "Full audit trail is stored in the audit_logs table. "
                "Query by scan_id to retrieve all WORM entries.",
        "stages_executed": ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10"],
    }

    # -- P6: Machine-Readable JSON ----------------------------------------------
    p6 = {
        "schema_version": "1.0",
        "project": {
            "name": profile.name,
            "registry_version": profile.registry_version,
        },
        "findings": [
            {
                "control_id": r.control_id,
                "outcome": r.outcome,
                "doc_classification": ann_map.get(r.control_id, None) and
                    ann_map[r.control_id].doc_classification,
            }
            for r in evidence_results
        ],
        "escalations": p4,
    }

    return {"p1": p1, "p2": p2, "p3": p3, "p4": p4, "p5": p5, "p6": p6}
