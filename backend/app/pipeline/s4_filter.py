"""S4 — Filter: filter controls by project profile, queue T3 controls for supplement.

Responsibilities
----------------
1. Accept all controls as a list of dicts (pre-loaded by the caller).
2. Apply profile-based filter rules:
   - Only include tier-1 controls if effective assurance level is "basic".
   - Include GEN overlay controls when uses_genai is True.
   - Include REL overlay controls when uses_rel_ai is True.
   - PRV-07 only activates when cross_border_transfer is True.
   - ACC-02 and ACC-04 only activate when user_facing is True.
   - vulnerable_users / rights_affecting raise minimum level to "capstone".
   - regulated_sector raises minimum level to "industrial".
3. Identify Tier-3 controls that need manual supplement review.
4. Return the filtered list of control dicts and the T3 supplement queue.
"""

from typing import Any

from app.pipeline.models import ProjectProfile

# Assurance level hierarchy: higher rank = stricter scrutiny
_LEVEL_RANK: dict[str, int] = {
    "basic": 1,
    "standard": 2,
    "enhanced": 3,
    "capstone": 4,
    "industrial": 5,
}
_RANK_TO_LEVEL = {v: k for k, v in _LEVEL_RANK.items()}

# Controls that are only relevant when personal data crosses borders
_CROSS_BORDER_CONTROLS = {"PRV-07"}

# Controls that only apply to public-facing systems (not internal tools)
_USER_FACING_CONTROLS = {"ACC-02", "ACC-04"}


def _effective_level_rank(profile: ProjectProfile) -> int:
    """Compute the minimum assurance rank required by the profile."""
    declared = _LEVEL_RANK.get(profile.assurance_level, 2)
    required = declared
    # vulnerable_users or rights_affecting → minimum capstone (rank 4)
    if getattr(profile, "vulnerable_users", False) or getattr(profile, "rights_affecting", False):
        required = max(required, 4)
    # regulated_sector → minimum industrial (rank 5, highest)
    if getattr(profile, "regulated_sector", False):
        required = max(required, 5)
    return required


def run(
    profile: ProjectProfile,
    all_controls: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Filter registry controls for this project.

    Parameters
    ----------
    profile:      Project profile with all intake fields set.
    all_controls: Full list of control dicts (loaded from the database by the caller).

    Returns
    -------
    (active_controls, t3_supplement_queue) — both are lists of control dicts.
    """
    active: list[dict[str, Any]] = []
    t3_queue: list[dict[str, Any]] = []

    effective_rank = _effective_level_rank(profile)
    cross_border = getattr(profile, "cross_border_transfer", False)
    user_facing = getattr(profile, "user_facing", True)

    for control in all_controls:
        control_id: str = control.get("control_id", control.get("id", ""))
        tier = control.get("tier", 1)

        # Basic assurance: only tier-1 automated controls
        if effective_rank == 1 and tier > 1:
            continue

        # GEN overlay: skip GEN-specific controls if project doesn't use generative AI
        if control_id.startswith("GEN") and not profile.uses_genai:
            continue

        # REL overlay: skip REL-specific controls if project doesn't use reliability/classical AI
        if control_id.startswith("REL") and not profile.uses_rel_ai:
            continue

        # PRV-07: only active when cross-border data transfer is declared
        if control_id in _CROSS_BORDER_CONTROLS and not cross_border:
            continue

        # ACC-02, ACC-04: only active for public-facing systems
        if control_id in _USER_FACING_CONTROLS and not user_facing:
            continue

        if tier == 3:
            # T3 controls require a human supplement — queue separately
            t3_queue.append(control)
        else:
            active.append(control)

    return active, t3_queue
