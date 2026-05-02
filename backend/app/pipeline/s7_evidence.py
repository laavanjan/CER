"""S7 — Evidence: map RawFindings to PASS/PARTIAL/MISSING/ISSUE outcomes (deterministic, no AI).

Responsibilities
----------------
1. Group RawFindings by control_id.
2. Apply deterministic scoring rules from the registry pass/partial/missing criteria.
3. Aggregate evidence_locations and issue_locations from all findings.
4. Return a list of EvidenceResult objects — one per control.

IMPORTANT: This stage is fully deterministic — no randomness, no LLM calls.
The outcome depends only on evidence_found / missing counts and confidence scores.

Outcomes
--------
PASS    : At least one finding has evidence AND confidence >= PASS threshold.
PARTIAL : At least one finding has some evidence OR confidence >= PARTIAL threshold.
ISSUE   : Active problems were detected (issue_locations populated), regardless of evidence.
MISSING : No evidence found across all findings.
"""

from typing import Any

from app.pipeline.models import EvidenceLocation, EvidenceResult, RawFinding

# Threshold above which a single finding is considered "passing"
_PASS_CONFIDENCE_THRESHOLD = 0.75
# Threshold above which a finding is considered "partial"
_PARTIAL_CONFIDENCE_THRESHOLD = 0.40


def _score(findings: list[RawFinding]) -> str:
    """Return PASS / PARTIAL / ISSUE / MISSING for a group of findings for one control.

    Rules (deterministic, evaluated in priority order):
    - PASS   : At least one finding has evidence AND confidence >= PASS threshold.
    - ISSUE  : Any finding has issue_locations populated (active problems detected).
               An ISSUE can co-exist with evidence — it means something was found but
               there are also active problems that need remediation.
    - PARTIAL: At least one finding has some evidence OR confidence >= PARTIAL threshold.
    - MISSING: No evidence found across all findings.
    """
    if not findings:
        return "MISSING"

    has_pass = any(
        f.evidence_found and f.confidence >= _PASS_CONFIDENCE_THRESHOLD
        for f in findings
    )
    has_issues = any(f.issue_locations for f in findings)

    if has_pass and not has_issues:
        return "PASS"

    if has_issues:
        return "ISSUE"

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
        tier = int(control.get("tier", 1))
        group = grouped.get(cid, [])
        outcome = _score(group)
        evidence_paths = [p for f in group for p in f.evidence_found]

        # Aggregate line-level locations from all findings for this control
        ev_locs: list[EvidenceLocation] = [
            loc for f in group for loc in f.evidence_locations
        ]
        issue_locs: list[EvidenceLocation] = [
            loc for f in group for loc in f.issue_locations
        ]

        results.append(
            EvidenceResult(
                control_id=cid,
                outcome=outcome,
                tier=tier,
                raw_findings=group,
                evidence_paths=evidence_paths,
                evidence_locations=ev_locs,
                issue_locations=issue_locs,
            )
        )

    return results
