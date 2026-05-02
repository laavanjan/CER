"""S9 — LLM: 3-tier LLM pipeline with Anthropic → Ollama Cloud → Gemini fallback.

Responsibilities
----------------
1. For each control result from S7, call the LLM with tier-aware prompts:
   - Tier 1 PASS/PARTIAL : Include file:line evidence locations in explanation prompt.
   - Tier 1 ISSUE        : Include file:line issue locations + reason in a dedicated prompt.
   - Tier 1 MISSING      : Same as Tier 2/3 (no locations to show).
   - Tier 2/3            : Use the original prompts (no line-level context needed).
2. Three LLM calls per control: EXPLAIN, REMEDIATE, CLASSIFY_DOC.
3. Fallback order: Anthropic → Ollama Cloud → Gemini.
   Once a provider fails it is skipped for the rest of the run.
4. Return a list of LLMAnnotation objects.

NOTE: temperature=0 is mandatory for deterministic, auditable outputs.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.pipeline.models import EvidenceLocation, EvidenceResult, LLMAnnotation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tier 2/3 prompts (unchanged baseline)
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Tier 1 PASS / PARTIAL prompts (include file:line evidence)
# ---------------------------------------------------------------------------

_T1_EXPLAIN_PASS_PROMPT = """You are an AI ethics auditor. The following Tier 1 control PASSED.
Explain in 2-3 sentences what evidence was found and why this demonstrates compliance.

Control ID: {control_id}
Outcome: PASS

Evidence locations (file : line — matched text):
{evidence_locations}

Respond with only the explanation text."""

_T1_EXPLAIN_PARTIAL_PROMPT = """You are an AI ethics auditor. The following Tier 1 control is PARTIAL.
Explain what evidence was found, which lines support it, and what is still missing.

Control ID: {control_id}
Outcome: PARTIAL

Evidence locations (file : line — matched text):
{evidence_locations}

Respond with only the explanation text."""

# ---------------------------------------------------------------------------
# Tier 1 ISSUE prompt (include file:line problems + reason)
# ---------------------------------------------------------------------------

_T1_EXPLAIN_ISSUE_PROMPT = """You are an AI ethics auditor. The following Tier 1 control has ISSUES.
Active problems were detected in specific files. Explain what was found at each location
and why it represents a compliance risk.

Control ID: {control_id}
Outcome: ISSUE

Issue locations (file : line — content — reason):
{issue_locations}

Respond with only the explanation text (2-4 sentences)."""

_T1_ISSUE_REMEDIATE_PROMPT = """You are an AI ethics auditor. Active compliance issues were found
at specific lines in the repository. Provide 3-5 concrete remediation steps, referencing
the specific files and lines where fixes are needed.

Control ID: {control_id}
Outcome: ISSUE

Issue locations (file : line — content — reason):
{issue_locations}

Respond with only the numbered remediation steps."""

_T1_ISSUE_CLASSIFY_PROMPT = """You are a documentation quality classifier.
An active compliance ISSUE was detected (not just missing documentation).
Classify as one of: ADEQUATE | NEEDS_IMPROVEMENT | ABSENT.

Control ID: {control_id}
Outcome: ISSUE
Issue count: {issue_count}

Respond with only one of the three classification labels."""


def _fmt_evidence_locations(locs: list[EvidenceLocation]) -> str:
    """Format EvidenceLocation objects into a compact readable block."""
    if not locs:
        return "(none)"
    lines = []
    for loc in locs[:20]:  # cap at 20 to avoid token bloat
        lines.append(f"  {loc.file}:{loc.line} — {loc.snippet}")
    if len(locs) > 20:
        lines.append(f"  ... and {len(locs) - 20} more locations")
    return "\n".join(lines)


def _fmt_issue_locations(locs: list[EvidenceLocation]) -> str:
    """Format issue EvidenceLocation objects with reason field."""
    if not locs:
        return "(none)"
    lines = []
    for loc in locs[:20]:
        lines.append(f"  {loc.file}:{loc.line} — {loc.snippet} [{loc.reason}]")
    if len(locs) > 20:
        lines.append(f"  ... and {len(locs) - 20} more locations")
    return "\n".join(lines)


def _build_prompts(result: EvidenceResult) -> tuple[str, str, str]:
    """Return (explain_prompt, remediate_prompt, classify_prompt) for a result.

    Tier 1 controls get outcome-specific prompts that include file:line context.
    Tier 2 and 3 controls use the original baseline prompts.
    """
    cid = result.control_id
    outcome = result.outcome
    ev_paths = result.evidence_paths

    if result.tier == 1:
        if outcome == "PASS":
            ev_block = _fmt_evidence_locations(result.evidence_locations)
            explain = _T1_EXPLAIN_PASS_PROMPT.format(
                control_id=cid, evidence_locations=ev_block
            )
            remediate = _REMEDIATE_PROMPT.format(control_id=cid, outcome=outcome)
            classify = _CLASSIFY_DOC_PROMPT.format(
                control_id=cid, outcome=outcome, evidence_paths=ev_paths
            )

        elif outcome == "PARTIAL":
            ev_block = _fmt_evidence_locations(result.evidence_locations)
            explain = _T1_EXPLAIN_PARTIAL_PROMPT.format(
                control_id=cid, evidence_locations=ev_block
            )
            remediate = _REMEDIATE_PROMPT.format(control_id=cid, outcome=outcome)
            classify = _CLASSIFY_DOC_PROMPT.format(
                control_id=cid, outcome=outcome, evidence_paths=ev_paths
            )

        elif outcome == "ISSUE":
            issue_block = _fmt_issue_locations(result.issue_locations)
            explain = _T1_EXPLAIN_ISSUE_PROMPT.format(
                control_id=cid, issue_locations=issue_block
            )
            remediate = _T1_ISSUE_REMEDIATE_PROMPT.format(
                control_id=cid, issue_locations=issue_block
            )
            classify = _T1_ISSUE_CLASSIFY_PROMPT.format(
                control_id=cid, issue_count=len(result.issue_locations)
            )

        else:  # MISSING — no locations to show, use baseline
            explain = _EXPLAIN_PROMPT.format(
                control_id=cid, outcome=outcome, evidence_paths=ev_paths
            )
            remediate = _REMEDIATE_PROMPT.format(control_id=cid, outcome=outcome)
            classify = _CLASSIFY_DOC_PROMPT.format(
                control_id=cid, outcome=outcome, evidence_paths=ev_paths
            )

    else:
        # Tier 2 / 3 — baseline prompts unchanged
        explain = _EXPLAIN_PROMPT.format(
            control_id=cid, outcome=outcome, evidence_paths=ev_paths
        )
        remediate = _REMEDIATE_PROMPT.format(control_id=cid, outcome=outcome)
        classify = _CLASSIFY_DOC_PROMPT.format(
            control_id=cid, outcome=outcome, evidence_paths=ev_paths
        )

    return explain, remediate, classify


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
    Tier 1 controls receive outcome-specific prompts including file:line context.
    """
    if not anthropic_api_key and not ollama_api_key and not gemini_api_key:
        return [
            LLMAnnotation(
                control_id=r.control_id,
                explanation="[LLM unavailable — no API key configured]",
                remediation="[LLM unavailable — no API key configured]",
                doc_classification="NEEDS_IMPROVEMENT",
                issue_detail=_fmt_issue_locations(r.issue_locations) if r.issue_locations else "",
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
        explain_prompt, remediate_prompt, classify_prompt = _build_prompts(result)

        explain = _make_call(explain_prompt, anthropic_client, ollama_client, gemini_client, state)
        remediate = _make_call(remediate_prompt, anthropic_client, ollama_client, gemini_client, state)
        classify = _make_call(classify_prompt, anthropic_client, ollama_client, gemini_client, state)

        # For Tier 1 ISSUE outcomes, populate issue_detail with the structured locations
        issue_detail = ""
        if result.tier == 1 and result.issue_locations:
            issue_detail = _fmt_issue_locations(result.issue_locations)

        return LLMAnnotation(
            control_id=result.control_id,
            explanation=explain,
            remediation=remediate,
            doc_classification=classify,
            issue_detail=issue_detail,
        )

    # 4 workers — safe for Gemini free tier (15 req/min); Ollama Cloud has no strict limit
    annotations: list[LLMAnnotation] = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(_annotate, r): r for r in evidence_results}
        for future in as_completed(futures):
            annotations.append(future.result())

    return annotations
