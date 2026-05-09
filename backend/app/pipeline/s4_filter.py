"""S4 — Control Activation & Routing.

Responsibilities
----------------
1. Select applicable controls from the canonical registry.
2. Read cer_observability field per control (T1 | T2 | T3).
3. Route T1/T2 controls to the S5 plugin queue.
4. Route T3 controls to the Metadata Supplement path (status = not_evaluable).
5. Apply profile-driven applicability rules (assurance level, GEN/REL, PRV-07, ACC).
6. Apply mandatory override rules that can only raise, never lower, the assurance level.

Assurance level hierarchy (AIGAP):
  UG        → Tier 1 controls only
  PG        → Tier 1–2 controls
  Capstone  → All tiers
  Industrial → All tiers (highest scrutiny)

Override rules (profile flags can only raise the level, never lower it):
  vulnerable_users or rights_affecting → minimum Capstone
  regulated_sector                     → minimum Industrial
"""

from typing import Any

from app.pipeline.models import ProjectProfile, SupplementEntry

_LEVEL_RANK: dict[str, int] = {
    "ug": 1,
    "pg": 2,
    "capstone": 3,
    "industrial": 4,
}

_TIER_THRESHOLD: dict[int, int] = {
    1: 1,   # UG: assurance tier 1 only
    2: 2,   # PG: assurance tiers 1–2
    3: 99,  # Capstone: all tiers
    4: 99,  # Industrial: all tiers
}

_CROSS_BORDER_CONTROLS = {"PRV-07"}
_USER_FACING_CONTROLS = {"ACC-02", "ACC-04"}


def _effective_level_rank(profile: ProjectProfile) -> int:
    declared = _LEVEL_RANK.get(profile.assurance_level, 1)
    required = declared
    if profile.vulnerable_users or profile.rights_affecting:
        required = max(required, 3)
    if profile.regulated_sector:
        required = max(required, 4)
    return required


def run(
    profile: ProjectProfile,
    all_controls: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[SupplementEntry]]:
    """Filter and route registry controls for this project.

    Returns
    -------
    (active_controls, t3_queue, supplement_entries)
      active_controls    — T1/T2 controls that passed all filters → go to S5
      t3_queue           — T3 controls that are in scope (kept for reference)
      supplement_entries — SupplementEntry per active T3 control (status=not_evaluable)
    """
    active: list[dict[str, Any]] = []
    t3_queue: list[dict[str, Any]] = []
    supplement_entries: list[SupplementEntry] = []

    effective_rank = _effective_level_rank(profile)
    tier_limit = _TIER_THRESHOLD.get(effective_rank, 1)
    cross_border = profile.cross_border_transfer
    user_facing = profile.user_facing

    for control in all_controls:
        control_id: str = control.get("id", control.get("control_id", ""))
        assurance_tier = int(control.get("tier", 1))
        cer_obs: str = control.get("cer_observability", "T2")

        # Assurance-tier gate
        if assurance_tier > tier_limit:
            continue

        # GEN overlay — skip if project has no generative AI
        if control_id.startswith("GEN") and not profile.uses_genai:
            continue

        # REL overlay — skip if project has no classical AI
        if control_id.startswith("REL") and not profile.uses_rel_ai:
            continue

        # PRV-07 only active when cross-border transfer declared
        if control_id in _CROSS_BORDER_CONTROLS and not cross_border:
            continue

        # ACC-02, ACC-04 only active for public-facing systems
        if control_id in _USER_FACING_CONTROLS and not user_facing:
            continue

        # T3 — design-only, no plugins run, emit Metadata Supplement (I-03, I-04)
        if cer_obs == "T3":
            t3_queue.append(control)
            supplement_entries.append(
                SupplementEntry(
                    control_id=control_id,
                    supplement_prompt=control.get(
                        "supplement_prompt",
                        f"Please declare the artefact path for {control_id}.",
                    ),
                    artefact_type_expected=control.get("artefact_type_expected", "E4"),
                )
            )
        else:
            # T1 or T2 — goes to S5 plugin queue
            active.append(control)

    return active, t3_queue, supplement_entries
