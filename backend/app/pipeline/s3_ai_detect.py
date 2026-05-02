"""S3 — AI Detection: scan imports/keywords, set gen_triggered / rel_triggered flags.

Responsibilities
----------------
1. Inspect the file manifest for imports and keywords associated with generative AI
   (gen_triggered) and reliance-critical AI (rel_triggered).
2. Return an updated ProjectProfile with the two flags set.

IMPORTANT: files are read as text only — no code execution.
"""

import re
from pathlib import Path

from app.pipeline.models import ManifestEntry, ProjectProfile

# Libraries / modules that indicate *generative* AI usage
_GEN_AI_INDICATORS = re.compile(
    r"""(?ix)
    \b(
        openai | anthropic | langchain | llama[_-]index | transformers |
        diffusers | stable[_-]diffusion | dalle | gpt[-_]? | claude |
        cohere | huggingface | generate | GenerativePipeline
    )\b
    """
)

# Libraries / modules that indicate *reliance-critical* AI usage (safety decisions)
_REL_AI_INDICATORS = re.compile(
    r"""(?ix)
    \b(
        tensorflow | torch | sklearn | xgboost | lightgbm |
        keras | onnx | autosklearn | pycaret | mlflow |
        bentoml | triton | tflite | coreml
    )\b
    """
)


def run(
    profile: ProjectProfile,
    manifest: list[ManifestEntry],
    repo_root: Path,
) -> ProjectProfile:
    """Scan the repository files and update AI-detection flags on the profile.

    Parameters
    ----------
    profile:   Validated project profile from S2.
    manifest:  File manifest from S2.
    repo_root: Root directory where the repository was materialised.

    Returns
    -------
    Updated ProjectProfile with gen_triggered / rel_triggered attributes set.
    """
    gen_triggered = False
    rel_triggered = False

    for entry in manifest:
        filepath = repo_root / entry.path
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        if _GEN_AI_INDICATORS.search(content):
            gen_triggered = True
        if _REL_AI_INDICATORS.search(content):
            rel_triggered = True

        if gen_triggered and rel_triggered:
            break  # No need to scan further

    # Merge declared flags with auto-detected signals.
    # A user ticking the checkbox OR detection finding the pattern both count.
    profile.uses_genai = profile.uses_genai or gen_triggered
    profile.uses_rel_ai = profile.uses_rel_ai or rel_triggered
    # Store raw detection flags as extra attributes for S8 honesty check.
    profile.gen_triggered = gen_triggered
    profile.rel_triggered = rel_triggered

    return profile
