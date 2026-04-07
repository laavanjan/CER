"""S9 — LLM: call Anthropic Claude API (temp=0) with 3 prompts per control.

Responsibilities
----------------
1. For each control result from S7, call Claude with three prompts:
   - EXPLAIN:      Explain the finding in plain language.
   - REMEDIATE:    Provide concrete remediation steps.
   - CLASSIFY_DOC: Classify the documentation quality.
2. Return a list of LLMAnnotation objects.

NOTE: temperature=0 is mandatory for deterministic, auditable outputs.
"""

from typing import Any

from app.pipeline.models import EvidenceResult, LLMAnnotation

_EXPLAIN_PROMPT = """You are an AI ethics auditor. Given the following control and evidence, 
explain in 2-3 sentences what was found and why it matters for ethical AI compliance.

Control ID: {control_id}
Outcome: {outcome}
Evidence paths: {evidence_paths}

Respond with only the explanation text."""

_REMEDIATE_PROMPT = """You are an AI ethics auditor. Given the following control finding,
provide 3-5 specific, actionable remediation steps that the development team should take.

Control ID: {control_id}
Outcome: {outcome}

Respond with only the numbered remediation steps."""

_CLASSIFY_DOC_PROMPT = """You are a documentation quality classifier.
Given the outcome of a documentation control check, classify the documentation quality
as one of: ADEQUATE | NEEDS_IMPROVEMENT | ABSENT.

Control ID: {control_id}
Outcome: {outcome}
Evidence paths: {evidence_paths}

Respond with only one of the three classification labels."""


def _call_claude(client: Any, prompt: str) -> str:
    """Call the Anthropic Claude API and return the text response."""
    message = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=512,
        temperature=0,  # Mandatory: deterministic / auditable
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def run(
    evidence_results: list[EvidenceResult],
    anthropic_api_key: str,
) -> list[LLMAnnotation]:
    """Generate LLM annotations for every evidence result.

    Parameters
    ----------
    evidence_results: Per-control outcomes from S7.
    anthropic_api_key: API key for Anthropic (from settings).

    Returns
    -------
    List of LLMAnnotation objects (one per control).
    """
    if not anthropic_api_key:
        # Return stub annotations when no API key is configured (e.g. CI / tests)
        return [
            LLMAnnotation(
                control_id=r.control_id,
                explanation="[LLM unavailable — no API key configured]",
                remediation="[LLM unavailable — no API key configured]",
                doc_classification="NEEDS_IMPROVEMENT",
            )
            for r in evidence_results
        ]

    try:
        import anthropic  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "anthropic package is required for S9. Install it with: pip install anthropic"
        ) from exc

    client = anthropic.Anthropic(api_key=anthropic_api_key)
    annotations: list[LLMAnnotation] = []

    for result in evidence_results:
        explain = _call_claude(
            client,
            _EXPLAIN_PROMPT.format(
                control_id=result.control_id,
                outcome=result.outcome,
                evidence_paths=result.evidence_paths,
            ),
        )
        remediate = _call_claude(
            client,
            _REMEDIATE_PROMPT.format(
                control_id=result.control_id,
                outcome=result.outcome,
            ),
        )
        classify = _call_claude(
            client,
            _CLASSIFY_DOC_PROMPT.format(
                control_id=result.control_id,
                outcome=result.outcome,
                evidence_paths=result.evidence_paths,
            ),
        )
        annotations.append(
            LLMAnnotation(
                control_id=result.control_id,
                explanation=explain,
                remediation=remediate,
                doc_classification=classify,
            )
        )

    return annotations
