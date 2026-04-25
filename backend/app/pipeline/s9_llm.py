"""S9 — LLM: call Anthropic Claude API (temp=0) with 3 prompts per control.

Responsibilities
----------------
1. For each control result from S7, call Claude with three prompts:
   - EXPLAIN:      Explain the finding in plain language.
   - REMEDIATE:    Provide concrete remediation steps.
   - CLASSIFY_DOC: Classify the documentation quality.
2. Falls back to Google Gemini automatically if Anthropic fails.
3. Return a list of LLMAnnotation objects.

NOTE: temperature=0 is mandatory for deterministic, auditable outputs.
"""

import logging
from typing import Any

from app.pipeline.models import EvidenceResult, LLMAnnotation

logger = logging.getLogger(__name__)

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
    message = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=512,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def _call_gemini(client: Any, prompt: str) -> str:
    response = client.models.generate_content(
        model="gemma-4-26b-a4b-it",
        contents=prompt,
        config={"temperature": 0, "max_output_tokens": 512},
    )
    return response.text.strip()


def _make_call(prompt: str, anthropic_client: Any, gemini_client: Any) -> str:
    """Try Anthropic first; if it raises any error, fall back to Gemini."""
    if anthropic_client:
        try:
            return _call_claude(anthropic_client, prompt)
        except Exception as exc:
            logger.warning("Anthropic call failed (%s) — switching to Gemini.", exc)
            if gemini_client:
                return _call_gemini(gemini_client, prompt)
            raise
    if gemini_client:
        return _call_gemini(gemini_client, prompt)
    raise RuntimeError("No LLM client available")


def run(
    evidence_results: list[EvidenceResult],
    anthropic_api_key: str,
    gemini_api_key: str = "",
) -> list[LLMAnnotation]:
    """Generate LLM annotations for every evidence result.

    Parameters
    ----------
    evidence_results: Per-control outcomes from S7.
    anthropic_api_key: API key for Anthropic (primary).
    gemini_api_key: API key for Google Gemini (fallback).
    """
    if not anthropic_api_key and not gemini_api_key:
        return [
            LLMAnnotation(
                control_id=r.control_id,
                explanation="[LLM unavailable — no API key configured]",
                remediation="[LLM unavailable — no API key configured]",
                doc_classification="NEEDS_IMPROVEMENT",
            )
            for r in evidence_results
        ]

    anthropic_client = None
    gemini_client = None

    if anthropic_api_key:
        try:
            import anthropic  # type: ignore[import]
            anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
        except ImportError as exc:
            raise ImportError("pip install anthropic") from exc

    if gemini_api_key:
        try:
            from google import genai  # type: ignore[import]
            gemini_client = genai.Client(api_key=gemini_api_key)
        except ImportError as exc:
            raise ImportError("pip install google-genai") from exc

    annotations: list[LLMAnnotation] = []

    for result in evidence_results:
        explain = _make_call(
            _EXPLAIN_PROMPT.format(
                control_id=result.control_id,
                outcome=result.outcome,
                evidence_paths=result.evidence_paths,
            ),
            anthropic_client,
            gemini_client,
        )
        remediate = _make_call(
            _REMEDIATE_PROMPT.format(
                control_id=result.control_id,
                outcome=result.outcome,
            ),
            anthropic_client,
            gemini_client,
        )
        classify = _make_call(
            _CLASSIFY_DOC_PROMPT.format(
                control_id=result.control_id,
                outcome=result.outcome,
                evidence_paths=result.evidence_paths,
            ),
            anthropic_client,
            gemini_client,
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
