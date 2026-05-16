"""S9 — LLM Explanation: structured JSON annotations per control (§12).

Three prompts per control (§12.1–12.3):
  CODE_REVIEWER_EXPLAIN    — plain-language finding explanation
  CODE_REVIEWER_REMEDIATE  — specific actionable remediation steps
  CODE_REVIEWER_CLASSIFY_DOC — documentation quality classification

Guardrails (§12.1):
  Must not use 'certified', 'compliant', 'passed', 'failed', or 'legally required'.
  Must only reference explicitly detected evidence.

Fallback order: Anthropic → Ollama Cloud → Gemini.
temperature=0 is mandatory for deterministic, auditable outputs (I-07, I-10).
"""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.pipeline.models import EvidenceLocation, EvidenceResult, LLMAnnotation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates (§12)
# ---------------------------------------------------------------------------

_EXPLAIN_PROMPT = """You are an AI ethics auditor reviewing code evidence for the AIGAP framework.
Respond with a JSON object ONLY — no markdown, no explanation outside the JSON.

Control ID: {control_id}
Observation: {outcome}
Evidence paths: {evidence_paths}
Evidence locations: {evidence_locations}
Assurance level: {assurance_level}

Required JSON structure:
{{
  "developer_explanation": "<max 150 words — what was found and why it matters for ethical AI. Do NOT use the words: certified, compliant, passed, failed, legally required>",
  "student_summary": "<max 80 words — plain language for a student. Same word restrictions.>",
  "what_is_present": "<specific artefacts detected, or 'Nothing detected'>",
  "what_is_missing": "<specific artefacts absent, or 'Nothing missing'>"
}}"""

_REMEDIATE_PROMPT = """You are an AI ethics auditor helping developers improve their AI system.
Respond with a JSON object ONLY — no markdown, no explanation outside the JSON.

Control ID: {control_id}
Observation: {outcome}
Gaps detected: {gaps}
Repository language/framework signals: {evidence_paths}
Assurance level: {assurance_level}

Required JSON structure:
{{
  "remediation_steps": [
    {{
      "step_number": 1,
      "action": "<specific action>",
      "artifact_to_produce": "<file or artefact type>",
      "example_approach": "<concrete example referencing detected language/framework>",
      "priority": "<immediate | before_reviewer | before_certifier>"
    }}
  ]
}}
Rules: max 5 steps. Must reference specific detected language/framework. Must NOT fabricate library names."""

_CLASSIFY_PROMPT = """You are a documentation quality classifier for AI ethics artefacts.
Respond with a JSON object ONLY — no markdown, no explanation outside the JSON.

Control ID: {control_id}
Observation: {outcome}
Evidence paths: {evidence_paths}
Evidence locations: {evidence_locations}

Required JSON structure:
{{
  "best_match": "<artefact type or 'none'>",
  "confidence": "<high | medium | low>",
  "doc_classification": "<ADEQUATE | NEEDS_IMPROVEMENT | ABSENT>",
  "reasoning": "<max 50 words citing specific text from the document>"
}}
Rules: Return 'none' for best_match if no clear match. Must cite specific text in reasoning if evidence found."""


def _fmt_evidence_locations(locs: list[EvidenceLocation]) -> str:
    if not locs:
        return "(none)"
    lines = [f"  {loc.file}:{loc.line} — {loc.snippet}" for loc in locs[:20]]
    if len(locs) > 20:
        lines.append(f"  ... and {len(locs) - 20} more")
    return "\n".join(lines)


def _build_prompts(result: EvidenceResult, assurance_level: str) -> tuple[str, str, str]:
    cid = result.control_id
    outcome = result.outcome
    ev_paths = result.evidence_paths or []
    ev_locs = _fmt_evidence_locations(result.evidence_locations)
    gaps = result.gaps or []

    explain = _EXPLAIN_PROMPT.format(
        control_id=cid,
        outcome=outcome,
        evidence_paths=ev_paths,
        evidence_locations=ev_locs,
        assurance_level=assurance_level,
    )
    remediate = _REMEDIATE_PROMPT.format(
        control_id=cid,
        outcome=outcome,
        gaps=gaps,
        evidence_paths=ev_paths,
        assurance_level=assurance_level,
    )
    classify = _CLASSIFY_PROMPT.format(
        control_id=cid,
        outcome=outcome,
        evidence_paths=ev_paths,
        evidence_locations=ev_locs,
    )
    return explain, remediate, classify


def _parse_explain(raw: str) -> dict:
    try:
        return json.loads(raw)
    except Exception:
        return {
            "developer_explanation": raw[:600],
            "student_summary": raw[:300],
            "what_is_present": "",
            "what_is_missing": "",
        }


def _parse_remediate(raw: str) -> list[dict]:
    try:
        data = json.loads(raw)
        return data.get("remediation_steps", [])
    except Exception:
        return [{"step_number": 1, "action": raw[:300], "artifact_to_produce": "", "example_approach": "", "priority": "before_reviewer"}]


def _parse_classify(raw: str) -> dict:
    try:
        return json.loads(raw)
    except Exception:
        return {"doc_classification": "NEEDS_IMPROVEMENT", "best_match": "none", "confidence": "low", "reasoning": ""}


def _call_claude(client: Any, prompt: str) -> str:
    message = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=1024,
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
                options={"temperature": 0, "num_predict": 1024},
            )
            return response["message"]["content"].strip()
        except Exception as exc:
            if "429" in str(exc) and attempt < 3:
                time.sleep(10 * (attempt + 1))
            else:
                raise
    raise RuntimeError("_call_ollama exhausted retries without returning or raising")


def _call_gemini(client: Any, prompt: str) -> str:
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model="gemma-4-26b-a4b-it",
                contents=prompt,
                config={"temperature": 0, "max_output_tokens": 1024},
            )
            return response.text.strip()
        except Exception as exc:
            if "429" in str(exc) and attempt < 4:
                time.sleep(35 * (attempt + 1))
            else:
                raise
    raise RuntimeError("_call_gemini exhausted retries without returning or raising")


def _make_call(prompt: str, anthropic_client: Any, ollama_client: Any, gemini_client: Any, state: dict) -> str:
    if anthropic_client and not state.get("anthropic_failed"):
        try:
            return _call_claude(anthropic_client, prompt)
        except Exception as exc:
            logger.warning("Anthropic failed (%s) — switching to Ollama.", exc)
            state["anthropic_failed"] = True

    if ollama_client and not state.get("ollama_failed"):
        try:
            return _call_ollama(ollama_client, prompt)
        except Exception as exc:
            logger.warning("Ollama failed (%s) — switching to Gemini.", exc)
            if "429" not in str(exc):
                state["ollama_failed"] = True

    if gemini_client:
        return _call_gemini(gemini_client, prompt)

    raise RuntimeError("All LLM providers failed.")


def run(
    evidence_results: list[EvidenceResult],
    anthropic_api_key: str,
    assurance_level: str = "ug",
    ollama_api_key: str = "",
    gemini_api_key: str = "",
) -> list[LLMAnnotation]:
    """Generate structured LLM annotations for every evidence result.

    Only annotates controls with actionable outcomes (evidence_found/partial/missing).
    Skips not_triggered and not_evaluable (T3 supplement handles those).
    """
    # Skip controls with no actionable LLM content needed
    annotatable = [r for r in evidence_results if r.outcome in ("evidence_found", "partial", "missing")]

    if not anthropic_api_key and not ollama_api_key and not gemini_api_key:
        return [
            LLMAnnotation(
                control_id=r.control_id,
                developer_explanation="[LLM unavailable — no API key configured]",
                student_summary="[LLM unavailable]",
                what_is_present="",
                what_is_missing="",
                doc_classification="NEEDS_IMPROVEMENT",
            )
            for r in annotatable
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

    state: dict = {}

    def _annotate(result: EvidenceResult) -> LLMAnnotation:
        explain_prompt, remediate_prompt, classify_prompt = _build_prompts(result, assurance_level)

        raw_explain = _make_call(explain_prompt, anthropic_client, ollama_client, gemini_client, state)
        raw_remediate = _make_call(remediate_prompt, anthropic_client, ollama_client, gemini_client, state)
        raw_classify = _make_call(classify_prompt, anthropic_client, ollama_client, gemini_client, state)

        explain_data = _parse_explain(raw_explain)
        remediation_steps = _parse_remediate(raw_remediate)
        classify_data = _parse_classify(raw_classify)

        issue_detail = ""
        if result.issue_locations:
            issue_detail = _fmt_evidence_locations(result.issue_locations)

        return LLMAnnotation(
            control_id=result.control_id,
            developer_explanation=explain_data.get("developer_explanation", ""),
            student_summary=explain_data.get("student_summary", ""),
            what_is_present=explain_data.get("what_is_present", ""),
            what_is_missing=explain_data.get("what_is_missing", ""),
            remediation_steps=remediation_steps,
            doc_classification=classify_data.get("doc_classification", "NEEDS_IMPROVEMENT"),
            issue_detail=issue_detail,
        )

    annotations: list[LLMAnnotation] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_annotate, r): r for r in annotatable}
        for future in as_completed(futures):
            annotations.append(future.result())

    return annotations
