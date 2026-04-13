"""S4 — Filter: filter controls by project profile, queue T3 controls for supplement.

Responsibilities
----------------
1. Accept all controls as a list of dicts (pre-loaded by the caller).
2. Apply profile-based filter rules:
   - Only include tier-1 controls if assurance_level == "basic".
   - Include gen-AI overlay controls when uses_genai is True.
3. Identify Tier-3 controls that need manual supplement review.
4. Return the filtered list of control dicts and the T3 supplement queue.
"""

from typing import Any

from app.pipeline.models import ProjectProfile


def run(
    profile: ProjectProfile,
    all_controls: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Filter registry controls for this project.

    Parameters
    ----------
    profile:      Project profile with assurance_level and uses_genai set.
    all_controls: Full list of control dicts (loaded from the database by the caller).

    Returns
    -------
    (active_controls, t3_supplement_queue) — both are lists of control dicts.
    """
    active: list[dict[str, Any]] = []
    t3_queue: list[dict[str, Any]] = []

    for control in all_controls:
        tier = control.get("tier", 1)
        # Basic assurance: only tier-1 automated controls
        if profile.assurance_level == "basic" and tier > 1:
            continue
        # GEN overlay: skip GEN-specific controls if project doesn't use gen-AI
        # (Pillar prefix "GEN" indicates generative-AI-specific control)
        if control.get("id", "").startswith("GEN") and not profile.uses_genai:
            continue

        if tier == 3:
            # T3 controls require a human supplement — queue separately
            t3_queue.append(control)
        else:
            active.append(control)

    return active, t3_queue
