"""S5-LLM Runner: LLM-based file selection + content evaluation, one finding per control.

Two-step process per control:
  Step 1 (Haiku)  — select files from the manifest most likely to contain evidence
  Step 2 (Sonnet) — read those files and judge pass/partial/missing vs control criteria

Fallback order: Anthropic → Ollama → Gemini  (mirrors S9).
temperature=0 is mandatory for deterministic, auditable outputs (I-07, I-10).
Returns an empty list when no API keys are configured — keyword scanner results stand alone.
"""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from app.pipeline.models import LLMFinding, ManifestEntry
from app.pipeline.s5_plugins.base import BasePlugin

logger = logging.getLogger(__name__)

_MAX_WORKERS = 4
_MAX_FILES_IN_SELECTOR_PROMPT = 500  # cap paths listed for the file-selector call
_MAX_FILE_CHARS = 3_000              # cap per-file content for the evaluator call
_MAX_SELECTED_FILES = 5             # max files the selector may return

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_FILE_SELECTOR_PROMPT = """\
You are an AI ethics code auditor.

Given the repository file paths listed below, identify which files are MOST LIKELY \
to contain evidence for the following control requirement.

Control ID:    {control_id}
Pass criteria: {pass_criteria}
Also consider: {partial_criteria}
File scope:    {scope_note}

Repository files ({file_count} total):
{file_list}

Respond with JSON ONLY — no markdown, no text outside the JSON:
{{
  "selected_files": ["path/to/file1", "path/to/file2"],
  "reasoning": "one-sentence explanation"
}}

Rules:
- Return at most {max_files} paths
- Only use paths that appear verbatim in the list above
- Return an empty selected_files list if nothing seems relevant
- Do NOT invent file paths"""

_CONTENT_EVALUATOR_PROMPT = """\
You are an AI ethics code auditor evaluating a repository for the AIGAP framework.

Control ID:       {control_id}
Pass criteria:    {pass_criteria}
Partial criteria: {partial_criteria}
Missing criteria: {missing_criteria}

--- FILE CONTENTS ---
{file_contents}
--- END ---

Respond with JSON ONLY — no markdown, no text outside the JSON:
{{
  "outcome": "evidence_found",
  "confidence": 0.85,
  "reasoning": "concise explanation citing specific content from the files",
  "quoted_evidence": ["verbatim excerpt 1", "verbatim excerpt 2"]
}}

Rules:
- outcome must be exactly one of: evidence_found, partial, missing
- confidence is a float 0.0–1.0
- quoted_evidence: verbatim text from the files, max 200 chars each, max 5 quotes
- Do NOT use the words: certified, compliant, passed, failed, legally required"""


# ---------------------------------------------------------------------------
# LLM call helpers  (mirrors s9_llm.py pattern)
# ---------------------------------------------------------------------------

def _strip_fences(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```"):
        s = s[s.index("\n") + 1:] if "\n" in s else s[3:]
    if s.endswith("```"):
        s = s[: s.rfind("```")]
    return s.strip()


def _call_anthropic(client: Any, prompt: str, model: str) -> str:
    msg = client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def _call_ollama(client: Any, prompt: str) -> str:
    for attempt in range(4):
        try:
            resp = client.chat(
                model="gpt-oss:120b",
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0, "num_predict": 1024},
            )
            return resp["message"]["content"].strip()
        except Exception as exc:
            if "429" in str(exc) and attempt < 3:
                time.sleep(10 * (attempt + 1))
            else:
                raise
    raise RuntimeError("_call_ollama exhausted retries")


def _call_gemini(client: Any, prompt: str) -> str:
    for attempt in range(5):
        try:
            resp = client.models.generate_content(
                model="gemma-4-26b-a4b-it",
                contents=prompt,
                config={"temperature": 0, "max_output_tokens": 1024},
            )
            return resp.text.strip()
        except Exception as exc:
            if "429" in str(exc) and attempt < 4:
                time.sleep(35 * (attempt + 1))
            else:
                raise
    raise RuntimeError("_call_gemini exhausted retries")


def _make_call(
    prompt: str,
    anthropic_client: Any,
    ollama_client: Any,
    gemini_client: Any,
    state: dict,
    anthropic_model: str = "claude-haiku-4-5-20251001",
) -> str:
    """Try providers in order: Anthropic → Ollama → Gemini.

    `state` is shared across calls within a scan run — once a provider fails
    it is skipped for all subsequent calls (same pattern as s9_llm.py).
    """
    if anthropic_client and not state.get("anthropic_failed"):
        try:
            return _call_anthropic(anthropic_client, prompt, anthropic_model)
        except Exception as exc:
            logger.warning("S5-LLM: Anthropic failed (%s) — switching to Ollama.", exc)
            state["anthropic_failed"] = True

    if ollama_client and not state.get("ollama_failed"):
        try:
            return _call_ollama(ollama_client, prompt)
        except Exception as exc:
            logger.warning("S5-LLM: Ollama failed (%s) — switching to Gemini.", exc)
            if "429" not in str(exc):
                state["ollama_failed"] = True

    if gemini_client:
        return _call_gemini(gemini_client, prompt)

    raise RuntimeError("All LLM providers failed for S5-LLM.")


# ---------------------------------------------------------------------------
# Per-control scan logic
# ---------------------------------------------------------------------------

def _scan_control(
    control: dict[str, Any],
    manifest: list[ManifestEntry],
    repo_root: str,
    anthropic_client: Any,
    ollama_client: Any,
    gemini_client: Any,
    state: dict,
) -> LLMFinding:
    control_id = control.get("id", "unknown")
    observability = control.get("cer_observability", "T2")
    pass_criteria = control.get("pass_criteria", "")
    partial_criteria = control.get("partial_criteria", "")
    missing_criteria = control.get("missing_criteria", "")

    # Respect the same T1/T2 file-scope rule as the keyword scanner
    if observability == "T1":
        eligible = [e for e in manifest if BasePlugin.is_code_file(e)]
        scope_note = "T1 — code and config files only (no .md/.txt documentation)"
    else:
        eligible = list(manifest)
        scope_note = "T2 — all files including documentation"

    # Cap path list to avoid oversized prompts
    selector_files = eligible[:_MAX_FILES_IN_SELECTOR_PROMPT]
    file_list_str = "\n".join(e.path for e in selector_files)

    # ------------------------------------------------------------------
    # Step 1: File selector  (Haiku — fast, cheap)
    # ------------------------------------------------------------------
    selector_prompt = _FILE_SELECTOR_PROMPT.format(
        control_id=control_id,
        pass_criteria=pass_criteria,
        partial_criteria=partial_criteria,
        scope_note=scope_note,
        file_count=len(eligible),
        file_list=file_list_str,
        max_files=_MAX_SELECTED_FILES,
    )

    try:
        raw_selector = _make_call(
            selector_prompt,
            anthropic_client, ollama_client, gemini_client,
            state,
            anthropic_model="claude-haiku-4-5-20251001",
        )
        selector_data = json.loads(_strip_fences(raw_selector))
        selected_paths: list[str] = selector_data.get("selected_files", [])
        selector_reasoning: str = selector_data.get("reasoning", "")
    except Exception as exc:
        logger.warning("S5-LLM: file selector failed for %s: %s", control_id, exc)
        return LLMFinding(
            control_id=control_id,
            outcome="error",
            confidence=0.0,
            reasoning=f"File selector error: {exc}",
        )

    # Validate returned paths exist in the manifest (prevent hallucination)
    manifest_path_set = {e.path for e in eligible}
    selected_paths = [p for p in selected_paths if p in manifest_path_set][:_MAX_SELECTED_FILES]

    if not selected_paths:
        return LLMFinding(
            control_id=control_id,
            outcome="missing",
            confidence=0.0,
            selected_files=[],
            reasoning=f"No relevant files identified by LLM. Selector: {selector_reasoning}",
        )

    # ------------------------------------------------------------------
    # Step 2: Content evaluator  (Sonnet — more capable reasoning)
    # ------------------------------------------------------------------
    file_contents_parts: list[str] = []
    for path in selected_paths:
        full_path = Path(repo_root) / path
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")[:_MAX_FILE_CHARS]
        except OSError:
            content = "(file not readable)"
        file_contents_parts.append(f"### {path}\n{content}")
    file_contents_str = "\n\n".join(file_contents_parts)

    evaluator_prompt = _CONTENT_EVALUATOR_PROMPT.format(
        control_id=control_id,
        pass_criteria=pass_criteria,
        partial_criteria=partial_criteria,
        missing_criteria=missing_criteria,
        file_contents=file_contents_str,
    )

    try:
        raw_eval = _make_call(
            evaluator_prompt,
            anthropic_client, ollama_client, gemini_client,
            state,
            anthropic_model="claude-sonnet-4-6",
        )
        eval_data = json.loads(_strip_fences(raw_eval))
        outcome = eval_data.get("outcome", "missing")
        if outcome not in ("evidence_found", "partial", "missing"):
            outcome = "missing"
        return LLMFinding(
            control_id=control_id,
            outcome=outcome,
            confidence=float(eval_data.get("confidence", 0.0)),
            selected_files=selected_paths,
            reasoning=eval_data.get("reasoning", ""),
            quoted_evidence=eval_data.get("quoted_evidence", []),
        )
    except Exception as exc:
        logger.warning("S5-LLM: content evaluator failed for %s: %s", control_id, exc)
        return LLMFinding(
            control_id=control_id,
            outcome="error",
            confidence=0.0,
            selected_files=selected_paths,
            reasoning=f"Content evaluator error: {exc}",
        )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(
    active_controls: list[dict[str, Any]],
    manifest: list[ManifestEntry],
    repo_root: str,
    anthropic_api_key: str = "",
    ollama_api_key: str = "",
    gemini_api_key: str = "",
) -> list[LLMFinding]:
    """Run the LLM-based scanner for all active controls.

    Returns one LLMFinding per control.  Returns an empty list when no API
    keys are configured so that keyword scanner results still stand.
    """
    if not anthropic_api_key and not ollama_api_key and not gemini_api_key:
        logger.info("S5-LLM: no API keys configured — skipping LLM scan path")
        return []

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

    # Shared provider-failure state — once a provider fails it is skipped
    # for the rest of this scan run (thread-safe under CPython GIL).
    state: dict = {}

    findings: list[LLMFinding] = []
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        futures = {
            executor.submit(
                _scan_control,
                control, manifest, repo_root,
                anthropic_client, ollama_client, gemini_client,
                state,
            ): control
            for control in active_controls
        }
        for future in as_completed(futures):
            control = futures[future]
            cid = control.get("id", "unknown")
            try:
                findings.append(future.result())
            except Exception as exc:
                logger.error("S5-LLM: unexpected error for %s: %s", cid, exc)
                findings.append(LLMFinding(
                    control_id=cid,
                    outcome="error",
                    confidence=0.0,
                    reasoning=f"Unexpected error: {exc}",
                ))

    logger.info("S5-LLM: completed %d findings", len(findings))
    return findings
