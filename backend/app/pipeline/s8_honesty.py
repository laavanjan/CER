"""S8 — Honesty check: compare declared profile vs detected signals, produce escalation_hints.

Responsibilities
----------------
1. Compare what the user declared at intake (profile.uses_genai, assurance_level)
   against what S3 detected in the repository.
2. Produce EscalationHint objects where discrepancies exist.
3. These hints are later embedded in the S10 output packages.
"""

from app.pipeline.models import EscalationHint, ProjectProfile


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

    # Basic assurance but reliance-critical AI declared or detected
    if profile.assurance_level == "basic" and (profile.uses_rel_ai or rel_triggered):
        hints.append(
            EscalationHint(
                control_id="GOV-02",
                hint=(
                    "assurance_level='basic' is insufficient for reliance-critical AI systems. "
                    "Consider upgrading to 'standard' or 'enhanced'."
                ),
                severity="CRITICAL",
            )
        )

    return hints
