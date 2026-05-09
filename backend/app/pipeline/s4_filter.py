"""S4 — Filter: filter controls by project profile, queue T3 controls for supplement.

Assurance level hierarchy (AIGAP):
  UG        → Tier 1 controls only  (undergraduate project, lowest scrutiny)
  PG        → Tier 1–2 controls     (postgraduate project)
  Capstone  → All tiers             (vulnerable users or rights-affecting decisions)
  Industrial → All tiers            (regulated sector — healthcare, finance, legal)

Override rules (profile flags can only raise the level, never lower it):
  vulnerable_users or rights_affecting → minimum Capstone
  regulated_sector                     → minimum Industrial

Other profile-driven rules:
  cross_border_transfer=False → PRV-07 skipped (not applicable)
  user_facing=False           → ACC-02, ACC-04 skipped (internal tool)
  uses_genai=False            → GEN overlay controls skipped
  uses_rel_ai=False           → REL overlay controls skipped
"""

from typing import Any

from app.pipeline.models import ProjectProfile

# AIGAP assurance level hierarchy — higher rank = stricter scrutiny
_LEVEL_RANK: dict[str, int] = {
    "ug": 1,
    "pg": 2,
    "capstone": 3,
    "industrial": 4,
}

# Max tier included per level rank
_TIER_THRESHOLD: dict[int, int] = {
    1: 1,   # UG: tier 1 only
    2: 2,   # PG: tier 1–2
    3: 99,  # Capstone: all tiers
    4: 99,  # Industrial: all tiers
}

# Controls that are only relevant when personal data crosses borders
_CROSS_BORDER_CONTROLS = {"PRV-07"}

# Controls that only apply to public-facing systems (not internal tools)
_USER_FACING_CONTROLS = {"ACC-02", "ACC-04"}


def _effective_level_rank(profile: ProjectProfile) -> int:
    """Compute the minimum assurance rank required by the profile.

    Override rules can only raise the declared level — never lower it.
    """
    declared = _LEVEL_RANK.get(profile.assurance_level, 1)
    required = declared
    # vulnerable_users or rights_affecting → minimum Capstone (rank 3)
    if getattr(profile, "vulnerable_users", False) or getattr(profile, "rights_affecting", False):
        required = max(required, 3)
    # regulated_sector → minimum Industrial (rank 4, highest)
    if getattr(profile, "regulated_sector", False):
        required = max(required, 4)
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
    tier_limit = _TIER_THRESHOLD.get(effective_rank, 1)
    cross_border = getattr(profile, "cross_border_transfer", False)
    user_facing = getattr(profile, "user_facing", True)

    for control in all_controls:
        control_id: str = control.get("control_id", control.get("id", ""))
        tier = control.get("tier", 1)

        # Tier gate — UG sees tier 1 only, PG sees tier 1–2, Capstone/Industrial see all
        if tier > tier_limit:
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
