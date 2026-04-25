"""S9 — LLM: 3-tier LLM pipeline with Anthropic → Ollama Cloud → Gemini fallback.

Responsibilities
----------------
1. For each control result from S7, call the LLM with three prompts:
   - EXPLAIN:      Explain the finding in plain language.
   - REMEDIATE:    Provide concrete remediation steps.
   - CLASSIFY_DOC: Classify the documentation quality.
2. Fallback order: Anthropic → Ollama Cloud → Gemini.
   Once a provider fails it is skipped for the rest of the run.
3. Return a list of LLMAnnotation objects.

NOTE: temperature=0 is mandatory for deterministic, auditable outputs.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def _call_ollama(client: Any, prompt: str) -> str:
    for attempt in range(4):
        try:
            response = client.chat(
                model="gpt-oss:120b",
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0, "num_predict": 512},
            )
            return response["message"]["content"].strip()
        except Exception as exc:
            if "429" in str(exc) and attempt < 3:
                wait = 10 * (attempt + 1)
                logger.warning("Ollama 429 — waiting %ss before retry %s/4.", wait, attempt + 1)
                time.sleep(wait)
            else:
                raise


def _call_gemini(client: Any, prompt: str) -> str:
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model="gemma-4-26b-a4b-it",
                contents=prompt,
                config={"temperature": 0, "max_output_tokens": 512},
            )
            return response.text.strip()
        except Exception as exc:
            if "429" in str(exc) and attempt < 4:
                wait = 35 * (attempt + 1)
                logger.warning("Gemini 429 rate limit — waiting %ss before retry %s/5.", wait, attempt + 1)
                time.sleep(wait)
            else:
                raise


def _make_call(
    prompt: str,
    anthropic_client: Any,
    ollama_client: Any,
    gemini_client: Any,
    state: dict,
) -> str:
    """Try Anthropic → Ollama → Gemini, permanently skipping any provider that fails."""
    if anthropic_client and not state.get("anthropic_failed"):
        try:
            return _call_claude(anthropic_client, prompt)
        except Exception as exc:
            logger.warning("Anthropic failed (%s) — switching to Ollama Cloud.", exc)
            state["anthropic_failed"] = True

    if ollama_client and not state.get("ollama_failed"):
        try:
            return _call_ollama(ollama_client, prompt)
        except Exception as exc:
            logger.warning("Ollama Cloud failed (%s) — switching to Gemini.", exc)
            # Only permanently switch if it's not a recoverable 429
            if "429" not in str(exc):
                state["ollama_failed"] = True

    if gemini_client:
        return _call_gemini(gemini_client, prompt)

    raise RuntimeError("All LLM providers failed — no fallback available.")


def run(
    evidence_results: list[EvidenceResult],
    anthropic_api_key: str,
    ollama_api_key: str = "",
    gemini_api_key: str = "",
) -> list[LLMAnnotation]:
    """Generate LLM annotations for every evidence result.

    Fallback order: Anthropic → Ollama Cloud → Gemini.
    """
    if not anthropic_api_key and not ollama_api_key and not gemini_api_key:
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
    ollama_client = None
    gemini_client = None

    if anthropic_api_key:
        try:
            import anthropic  # type: ignore[import]
            anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
        except ImportError as exc:
            raise ImportError("pip install anthropic") from exc

    if ollama_api_key:
        try:
            from ollama import Client as OllamaClient  # type: ignore[import]
            ollama_client = OllamaClient(
                host="https://ollama.com",
                headers={"Authorization": f"Bearer {ollama_api_key}"},
            )
        except ImportError as exc:
            raise ImportError("pip install ollama") from exc

    if gemini_api_key:
        try:
            from google import genai  # type: ignore[import]
            gemini_client = genai.Client(api_key=gemini_api_key)
        except ImportError as exc:
            raise ImportError("pip install google-genai") from exc

    state: dict = {}  # tracks which providers have failed this run

    def _annotate(result: EvidenceResult) -> LLMAnnotation:
        explain = _make_call(
            _EXPLAIN_PROMPT.format(
                control_id=result.control_id,
                outcome=result.outcome,
                evidence_paths=result.evidence_paths,
            ),
            anthropic_client, ollama_client, gemini_client, state,
        )
        remediate = _make_call(
            _REMEDIATE_PROMPT.format(
                control_id=result.control_id,
                outcome=result.outcome,
            ),
            anthropic_client, ollama_client, gemini_client, state,
        )
        classify = _make_call(
            _CLASSIFY_DOC_PROMPT.format(
                control_id=result.control_id,
                outcome=result.outcome,
                evidence_paths=result.evidence_paths,
            ),
            anthropic_client, ollama_client, gemini_client, state,
        )
        return LLMAnnotation(
            control_id=result.control_id,
            explanation=explain,
            remediation=remediate,
            doc_classification=classify,
        )

    # 4 workers — safe for Gemini free tier (15 req/min); Ollama Cloud has no strict limit
    annotations: list[LLMAnnotation] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_annotate, r): r for r in evidence_results}
        for future in as_completed(futures):
            annotations.append(future.result())

    return annotations
