"""S6 — GEN/REL Signal Routing: tag PRIMARY control findings with overlay relevance.

AIGAP Architectural constraint
-------------------------------
GEN and REL are *derived* overlays — they never receive direct status assignments
from the CER.  Their status is derived by the Reviewer/Certifier from the outcomes
of anchoring PRIMARY controls.

What this stage does
--------------------
1. Build a reverse anchor map: PRIMARY control → list of GEN/REL overlays it informs.
   (Forward map defined in architecture section 8.2 / 8.3 — GEN/REL → PRIMARY controls.)
2. For every RawFinding produced by S5 (all of which belong to PRIMARY controls),
   look up which GEN/REL overlays that PRIMARY control informs and stamp
   finding.overlay_relevance accordingly.
3. Return the annotated findings unchanged in structure — control_id is never altered.

Anchor map (architecture §8.2 / §8.3)
--------------------------------------
GEN-01  Prompt Safety            → SAFE-01, SAFE-04
GEN-02  AI Disclosure            → TRAN-01, TRAN-06
GEN-03  Hallucination/Grounding  → TRAN-02, SAFE-06, TRAN-04
GEN-04  Content Moderation       → TRAN-01, SAFE-02
REL-01  Supply Chain Security    → SEC-01,  SEC-03
REL-02  Third-Party Data Prov.   → PRIV-06, DOC-01
REL-03  Model Supply Chain       → SEC-06
"""

from app.pipeline.models import RawFinding

# Forward map: GEN/REL overlay → anchoring PRIMARY controls (source of truth)
_FORWARD_ANCHOR: dict[str, list[str]] = {
    "GEN-01": ["SAFE-01", "SAFE-04"],
    "GEN-02": ["TRAN-01", "TRAN-06"],
    "GEN-03": ["TRAN-02", "SAFE-06", "TRAN-04"],
    "GEN-04": ["TRAN-01", "SAFE-02"],
    "REL-01": ["SEC-01",  "SEC-03"],
    "REL-02": ["PRIV-06", "DOC-01"],
    "REL-03": ["SEC-06"],
}


def _build_reverse_map() -> dict[str, list[str]]:
    """Invert _FORWARD_ANCHOR → PRIMARY control: [GEN/REL overlays it informs]."""
    reverse: dict[str, list[str]] = {}
    for overlay, primaries in _FORWARD_ANCHOR.items():
        for primary in primaries:
            reverse.setdefault(primary, []).append(overlay)
    return reverse


_REVERSE_ANCHOR: dict[str, list[str]] = _build_reverse_map()


def run(findings: list[RawFinding]) -> list[RawFinding]:
    """Stamp each PRIMARY control finding with the GEN/REL overlays it informs.

    Parameters
    ----------
    findings: Flat list of RawFindings from S5 (all belong to PRIMARY controls).

    Returns
    -------
    Same list with overlay_relevance populated on each finding.
    """
    for finding in findings:
        finding.overlay_relevance = _REVERSE_ANCHOR.get(finding.control_id, [])
    return findings
