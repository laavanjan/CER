"""explainability_scanner plugin — checks for explainability documentation and interpretability tooling.

Targets controls TRN-01 and TRN-02.
Reads files as text only — no code execution.
"""

from app.pipeline.models import ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_EXPLAINABILITY_FILENAMES = [
    "*explain*",
    "*EXPLAIN*",
    "*interpretab*",
    "*xai*",
    "*XAI*",
    "*transparency*",
    "*TRANSPARENCY*",
]

_EXPLAINABILITY_KEYWORDS = [
    "explainability",
    "explainable AI",
    "XAI",
    "explanation",
    "how decisions are made",
    "decision explanation",
    "model explanation",
    "why the model",
]

_INTERPRETABILITY_TOOLS = [
    "SHAP",
    "shap",
    "LIME",
    "lime",
    "attention map",
    "attention weight",
    "feature importance",
    "saliency",
    "grad-cam",
    "GradCAM",
    "integrated gradient",
    "counterfactual",
    "partial dependence",
]

_INTERPRETABILITY_KEYWORDS = [
    "interpretability",
    "interpretable",
    "model interpretability",
    "feature attribution",
    "local explanation",
    "global explanation",
]


class ExplainabilityScanner(BasePlugin):
    """Scans for explainability documentation and model interpretability tooling."""

    plugin_id = "explainability_scanner"

    def run(
        self,
        control_id: str,
        manifest: list[ManifestEntry],
        repo_root: str,
    ) -> list[RawFinding]:
        evidence: list[str] = []
        missing: list[str] = []
        confidence = 0.0

        if control_id == "TRN-01":
            for pattern in _EXPLAINABILITY_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _EXPLAINABILITY_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.85)
            # Also scan markdown files
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _EXPLAINABILITY_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.6)
            if not evidence:
                missing.append("No explainability approach documentation found")

        elif control_id == "TRN-02":
            # Check for interpretability tool references in code and docs
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                tools_found = [t for t in _INTERPRETABILITY_TOOLS if t in content]
                if tools_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.9)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                tools_found = [t for t in _INTERPRETABILITY_TOOLS if t in content]
                kw_found = [k for k in _INTERPRETABILITY_KEYWORDS if k.lower() in content.lower()]
                if (tools_found or kw_found) and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.7)
            if not evidence:
                missing.append(
                    "No model interpretability methods (SHAP, LIME, attention maps, etc.) referenced"
                )

        return [
            RawFinding(
                plugin_id=self.plugin_id,
                control_id=control_id,
                evidence_found=evidence,
                missing=missing,
                confidence=confidence,
            )
        ]
