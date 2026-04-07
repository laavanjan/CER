"""S7 — Evidence: map RawFindings to PASS/PARTIAL/MISSING outcomes (deterministic, no AI).

Responsibilities
----------------
1. Group RawFindings by control_id.
2. Apply deterministic scoring rules from the registry pass/partial/missing criteria.
3. Return a list of EvidenceResult objects — one per control.

IMPORTANT: This stage is fully deterministic — no randomness, no LLM calls.
The outcome depends only on evidence_found / missing counts and confidence scores.
"""

from typing import Any

from app.pipeline.models import EvidenceResult, RawFinding

# Threshold above which a single finding is considered "passing"
_PASS_CONFIDENCE_THRESHOLD = 0.75
# Threshold above which a finding is considered "partial"
_PARTIAL_CONFIDENCE_THRESHOLD = 0.40


def _score(findings: list[RawFinding]) -> str:
    """Return PASS / PARTIAL / MISSING for a group of findings for one control.

    Rules (deterministic):
    - PASS   : At least one finding has evidence AND confidence >= PASS threshold.
    - PARTIAL: At least one finding has some evidence OR confidence >= PARTIAL threshold.
    - MISSING: No evidence found across all findings.
    """
    if not findings:
        return "MISSING"

    for f in findings:
        if f.evidence_found and f.confidence >= _PASS_CONFIDENCE_THRESHOLD:
            return "PASS"

    for f in findings:
        if f.evidence_found or f.confidence >= _PARTIAL_CONFIDENCE_THRESHOLD:
            return "PARTIAL"

    return "MISSING"


def run(
    findings: list[RawFinding],
    active_controls: list[dict[str, Any]],
) -> list[EvidenceResult]:
    """Map findings to per-control outcomes.

    Parameters
    ----------
    findings:        Tagged RawFindings from S6.
    active_controls: Active controls list from S4 (used to ensure every control
                     has an outcome even if no plugin produced a finding).

    Returns
    -------
    List of EvidenceResult, one per active control.
    """
    # Group findings by control_id
    grouped: dict[str, list[RawFinding]] = {}
    for finding in findings:
        grouped.setdefault(finding.control_id, []).append(finding)

    results: list[EvidenceResult] = []
    for control in active_controls:
        cid = control["id"]
        group = grouped.get(cid, [])
        outcome = _score(group)
        evidence_paths = [p for f in group for p in f.evidence_found]
        results.append(
            EvidenceResult(
                control_id=cid,
                outcome=outcome,
                raw_findings=group,
                evidence_paths=evidence_paths,
            )
        )

    return results
