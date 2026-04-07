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
                control_id="GOV-01",  # Governance is the primary escalation pillar
                hint=(
                    "Project declared uses_genai=False but generative-AI library "
                    "imports were detected in the repository. "
                    "Review GOV-01, DOC-01 for completeness."
                ),
                severity="WARNING",
            )
        )

    # Reliance-critical AI detected — flag for human review regardless of declaration
    if rel_triggered:
        hints.append(
            EscalationHint(
                control_id="GOV-02",
                hint=(
                    "Reliance-critical AI libraries detected (e.g. TensorFlow, PyTorch). "
                    "Ensure safety-critical controls are reviewed by a human auditor."
                ),
                severity="WARNING",
            )
        )

    # Basic assurance but reliance-critical AI detected
    if profile.assurance_level == "basic" and rel_triggered:
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
