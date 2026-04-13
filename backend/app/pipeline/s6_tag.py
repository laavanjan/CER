"""S6 — Tag: tag GEN/REL overlay findings from the registry anchor map.

Responsibilities
----------------
1. Accept the flat list of RawFindings from S5.
2. Build the registry anchor map (pillar → GEN/REL overlay tags) from the
   pre-loaded controls list passed by the caller.
3. Annotate each finding with appropriate overlay tags.
4. Return the tagged findings list.
"""

from typing import Any

from app.pipeline.models import RawFinding


def _build_anchor_map(registry: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Build control_id → list-of-tags mapping from the registry."""
    anchor: dict[str, list[str]] = {}
    for control in registry:
        tags: list[str] = []
        cid: str = control.get("id", "")
        pillar: str = control.get("pillar", "")
        if cid.startswith("GEN") or pillar.upper() == "GENERATIVE":
            tags.append("GEN_OVERLAY")
        if cid.startswith("REL") or pillar.upper() == "RELIABILITY":
            tags.append("REL_OVERLAY")
        if tags:
            anchor[cid] = tags
    return anchor


def run(
    findings: list[RawFinding],
    registry: list[dict[str, Any]],
) -> list[RawFinding]:
    """Tag each RawFinding with overlay labels derived from the registry.

    Parameters
    ----------
    findings: List of RawFindings from S5.
    registry: Full list of control dicts (pre-loaded from the database by the caller).

    Returns
    -------
    Same list of findings, each annotated with a ``tags`` attribute.
    """
    anchor_map = _build_anchor_map(registry)

    for finding in findings:
        tags = anchor_map.get(finding.control_id, [])
        # Attach tags as an ad-hoc attribute (pipeline convention)
        finding.tags = tags

    return findings
