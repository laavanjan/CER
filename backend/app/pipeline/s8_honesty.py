"""S8 — Honesty check: compare declared profile vs detected signals, produce escalation_hints.

Responsibilities
----------------
1. Compare what the user declared at intake against what S3 detected in the repository.
2. Check that the declared assurance_level meets the minimum required by the risk profile.
3. Produce EscalationHint objects where discrepancies exist.
4. These hints are later embedded in the S10 output packages.
"""

from app.pipeline.models import EscalationHint, ProjectProfile

# AIGAP assurance level hierarchy
_LEVEL_RANK: dict[str, int] = {
    "ug": 1,
    "pg": 2,
    "capstone": 3,
    "industrial": 4,
}

# Cross-border transfer patterns detectable in code
import re as _re
_CROSS_BORDER_PATTERNS = _re.compile(
    r"""(?ix)\b(
        cross[-_]border | data[-_]transfer | gdpr | adequacy[-_]decision |
        standard[-_]contractual[-_]clauses | scc | binding[-_]corporate[-_]rules |
        international[-_]transfer | data[-_]export
    )\b"""
)


def run(profile: ProjectProfile) -> list[EscalationHint]:
    """Compare declared profile with auto-detected signals and emit hints.

    Parameters
    ----------
    profile: Project profile updated by S3 with gen_triggered / rel_triggered flags.

    Returns
    -------
    List of EscalationHint objects (may be empty if no discrepancies).
    """
    hints: list[EscalationHint] = []

    gen_triggered: bool = getattr(profile, "gen_triggered", False)
    rel_triggered: bool = getattr(profile, "rel_triggered", False)
    declared_rank = _LEVEL_RANK.get(profile.assurance_level, 1)

    # ── AI type honesty checks ────────────────────────────────────────────────

    # Declared no genAI but we found generative-AI indicators in the code
    if not profile.uses_genai and gen_triggered:
        hints.append(
            EscalationHint(
                control_id="GOV-01",
                hint=(
                    "Project declared uses_genai=False but generative-AI library "
                    "imports were detected in the repository. "
                    "Review GOV-01, DOC-01 for completeness."
                ),
                severity="WARNING",
            )
        )

    # Declared no rel-AI but we found reliability/classical AI indicators in the code
    if not profile.uses_rel_ai and rel_triggered:
        hints.append(
            EscalationHint(
                control_id="GOV-02",
                hint=(
                    "Project declared uses_rel_ai=False but reliability/classical AI library "
                    "imports were detected in the repository (e.g. TensorFlow, PyTorch, sklearn). "
                    "REL overlay controls were not applied — consider re-running with uses_rel_ai=True."
                ),
                severity="WARNING",
            )
        )

    # Declared rel-AI — flag for human review of safety-critical controls
    if profile.uses_rel_ai:
        hints.append(
            EscalationHint(
                control_id="GOV-02",
                hint=(
                    "Reliability/classical AI declared or detected (e.g. TensorFlow, PyTorch). "
                    "Ensure safety-critical REL overlay controls are reviewed by a human auditor."
                ),
                severity="WARNING",
            )
        )

    # ── Assurance level adequacy checks ──────────────────────────────────────

    # UG assurance but reliance-critical AI declared or detected
    if profile.assurance_level == "ug" and (profile.uses_rel_ai or rel_triggered):
        hints.append(
            EscalationHint(
                control_id="GOV-02",
                hint=(
                    "assurance_level='UG' is insufficient for reliance-critical AI systems. "
                    "Consider upgrading to 'PG', 'Capstone', or 'Industrial'."
                ),
                severity="CRITICAL",
            )
        )

    # vulnerable_users or rights_affecting require at least Capstone (rank 3)
    if (getattr(profile, "vulnerable_users", False) or getattr(profile, "rights_affecting", False)) \
            and declared_rank < 3:
        context = []
        if getattr(profile, "vulnerable_users", False):
            context.append("vulnerable users declared")
        if getattr(profile, "rights_affecting", False):
            context.append("rights-affecting decisions declared")
        hints.append(
            EscalationHint(
                control_id="GOV-05",
                hint=(
                    f"Profile flags ({', '.join(context)}) require a minimum assurance level of "
                    f"'Capstone', but '{profile.assurance_level.upper()}' was declared. "
                    "Upgrade to Capstone or Industrial."
                ),
                severity="CRITICAL",
            )
        )

    # regulated_sector requires Industrial (rank 4, highest)
    if getattr(profile, "regulated_sector", False) and declared_rank < 4:
        hints.append(
            EscalationHint(
                control_id="GOV-08",
                hint=(
                    "regulated_sector=True requires assurance_level='Industrial', "
                    f"but '{profile.assurance_level.upper()}' was declared. "
                    "Regulated deployments (healthcare, finance, insurance, legal) must meet "
                    "the highest AIGAP scrutiny bar."
                ),
                severity="CRITICAL",
            )
        )

    # ── Cross-border transfer honesty check ───────────────────────────────────

    # Declared no cross-border transfer — S3 cannot reliably detect this in code,
    # but if cross_border_transfer=False and jurisdiction spans multiple regions, flag it.
    jurisdiction = getattr(profile, "jurisdiction", None) or ""
    cross_border = getattr(profile, "cross_border_transfer", False)
    multi_jurisdiction = "," in jurisdiction or len(jurisdiction.split()) > 1

    if not cross_border and multi_jurisdiction:
        hints.append(
            EscalationHint(
                control_id="PRV-07",
                hint=(
                    "cross_border_transfer=False but multiple jurisdictions were declared "
                    f"({jurisdiction!r}). If personal data flows between these regions, "
                    "PRV-07 must be activated and re-scan triggered."
                ),
                severity="WARNING",
            )
        )

    # ── Jurisdiction check ────────────────────────────────────────────────────

    if not jurisdiction:
        hints.append(
            EscalationHint(
                control_id="GOV-03",
                hint=(
                    "No jurisdiction declared at intake. Jurisdiction-specific regulation "
                    "mapping (EU AI Act, NIST RMF, ISO 42001) could not be applied. "
                    "Re-declare with a jurisdiction for accurate regulatory alignment."
                ),
                severity="INFO",
            )
        )

    return hints
