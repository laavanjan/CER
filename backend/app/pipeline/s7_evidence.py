"""S7 — Evidence Mapping: apply the full scoring decision tree per control (§10).

Decision tree (first matching rule wins):
  Step 1  not_triggered — control applicability rule not satisfied (filtered by S4)
  Step 2  not_evaluable — T3 control ONLY (no plugins run, supplement pending)
  Step 3  missing       — T1/T2: plugins ran but found no files in scope
  Step 4  partial       — T1/T2: all plugins timed out (inconclusive)
  Step 5  missing       — files in scope, no expected evidence artefacts found
  Step 6  partial       — some expected evidence exists but not all required
  Step 7  pass          — all expected evidence present with sufficient confidence

`not_evaluable` is EXCLUSIVELY for T3 controls. T1/T2 controls with no
files in scope → missing. Timed-out T1/T2 → partial (inconclusive).

LLM is NEVER involved in status assignment (I-07).
Severity is calibrated to assurance level and control tier (§10.1).
"""

from typing import Any

from app.pipeline.models import (
    EvidenceLocation,
    EvidenceResult,
    RawFinding,
    SupplementEntry,
)

_PASS_CONFIDENCE = 0.75
_PARTIAL_CONFIDENCE = 0.40

# Artefact types to recommend when evidence is missing (advisory, not authoritative)
_RECOMMENDED_ARTIFACTS: dict[str, list[str]] = {
    "T1": ["source_file", "test_file", "config_file"],
    "T2": ["doc_file", "notebook", "report"],
    "T3": [],  # Handled by supplement
}


def _score_findings(findings: list[RawFinding]) -> str:
    """Steps 3–7 of the decision tree applied to a group of T1/T2 plugin findings.

    not_evaluable is NEVER returned here — it is exclusively for T3 controls.
    """
    if not findings:
        # Step 3: plugins ran but found no files in scope → treat as missing
        return "missing"

    has_timed_out_only = all(f.timed_out for f in findings)
    if has_timed_out_only:
        # Step 4: all plugins timed out — inconclusive, report as partial
        return "partial"

    has_pass = any(
        f.evidence_found and f.confidence >= _PASS_CONFIDENCE
        for f in findings
        if not f.timed_out
    )
    has_partial = any(
        f.evidence_found or f.confidence >= _PARTIAL_CONFIDENCE
        for f in findings
        if not f.timed_out
    )

    if has_pass:
        return "pass"
    if has_partial:
        return "partial"
    return "missing"


def _compute_severity(
    outcome: str,
    cer_obs: str,
    assurance_tier: int,
    user_facing: bool,
    has_overlay: bool,
) -> str:
    """Severity calibration per §10.1."""
    if outcome == "not_triggered":
        return "none"
    if outcome == "not_evaluable":
        # Only T3 controls reach here — supplement pending
        return "action_required"
    if outcome == "pass":
        return "none"
    # missing or partial
    is_high_tier = assurance_tier >= 2
    if outcome == "missing" and is_high_tier and user_facing:
        return "critical"
    if outcome == "missing" and is_high_tier:
        return "major"
    if outcome == "partial" and has_overlay:
        return "major"
    if outcome == "missing":
        return "minor"
    if outcome == "partial":
        return "minor"
    return "info"


def run(
    findings: list[RawFinding],
    active_controls: list[dict[str, Any]],
    supplement_entries: list[SupplementEntry],
    profile_user_facing: bool = True,
) -> list[EvidenceResult]:
    """Map findings to per-control outcomes.

    Parameters
    ----------
    findings:          Tagged RawFindings from S6.
    active_controls:   T1/T2 active controls from S4.
    supplement_entries: T3 supplement entries from S4.
    profile_user_facing: Whether project is public-facing (for severity).

    Returns
    -------
    List of EvidenceResult — one per active T1/T2 control + one per T3 supplement.
    """
    grouped: dict[str, list[RawFinding]] = {}
    for finding in findings:
        grouped.setdefault(finding.control_id, []).append(finding)

    results: list[EvidenceResult] = []

    # T1/T2 controls
    for control in active_controls:
        cid = control.get("id", control.get("control_id", ""))
        cer_obs: str = control.get("cer_observability", "T2")
        assurance_tier = int(control.get("tier", 1))

        group = grouped.get(cid, [])
        outcome = _score_findings(group)

        ev_paths = [p for f in group for p in f.evidence_found]
        ev_locs: list[EvidenceLocation] = [loc for f in group for loc in f.evidence_locations]
        issue_locs: list[EvidenceLocation] = [loc for f in group for loc in f.issue_locations]
        overlay_relevance = list({tag for f in group for tag in f.overlay_relevance})
        gaps = [m for f in group for m in f.missing]

        severity = _compute_severity(
            outcome, cer_obs, assurance_tier, profile_user_facing, bool(overlay_relevance)
        )

        recommended = _RECOMMENDED_ARTIFACTS.get(cer_obs, []) if outcome != "pass" else []

        results.append(
            EvidenceResult(
                control_id=cid,
                outcome=outcome,
                cer_observability=cer_obs,
                assurance_tier=assurance_tier,
                severity=severity,
                raw_findings=group,
                evidence_paths=ev_paths,
                evidence_locations=ev_locs,
                issue_locations=issue_locs,
                overlay_relevance=overlay_relevance,
                recommended_next_artifact=recommended,
                gaps=gaps,
            )
        )

    # T3 controls — always not_evaluable until supplement completed (I-03)
    for entry in supplement_entries:
        results.append(
            EvidenceResult(
                control_id=entry.control_id,
                outcome="not_evaluable",
                cer_observability="T3",
                assurance_tier=1,
                severity="action_required",
                recommended_next_artifact=[entry.artefact_type_expected],
                gaps=[f"Supplement required: {entry.supplement_prompt}"],
            )
        )

    return results
