"""docs_scanner plugin — checks for model cards, system cards, and architecture docs.

Targets controls with plugin_id "docs_scanner" (e.g. DOC-01, DOC-02).
Reads files as text only — no code execution.
"""

from app.pipeline.models import EvidenceLocation, ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

# Filenames that commonly contain model cards or system cards
_MODEL_CARD_PATTERNS = [
    "*model_card*",
    "*MODEL_CARD*",
    "*system_card*",
    "*SYSTEM_CARD*",
    "*model-card*",
    "*MODEL-CARD*",
]

# Mandatory fields that should be present in a model card
_MANDATORY_FIELDS = ["purpose", "limitations", "intended use", "intended_use"]

# Patterns for architecture decision records (DOC-02)
_ADR_PATTERNS = [
    "*adr*",
    "*ADR*",
    "*/decisions/*",
    "*architecture*",
    "*ARCHITECTURE*",
]

_ADR_KEYWORDS = ["decision", "architecture", "AI component", "design choice", "rationale"]


class DocsScanner(BasePlugin):
    """Scans for model cards, system cards, and architectural documentation."""

    plugin_id = "docs_scanner"

    def run(
        self,
        control_id: str,
        manifest: list[ManifestEntry],
        repo_root: str,
    ) -> list[RawFinding]:
        evidence: list[str] = []
        missing: list[str] = []
        confidence = 0.0
        ev_locs: list[EvidenceLocation] = []

        if control_id == "DOC-01":
            # Check for model card with mandatory fields
            for pattern in _MODEL_CARD_PATTERNS:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found_fields = [f for f in _MANDATORY_FIELDS if f.lower() in content.lower()]
                    if found_fields:
                        evidence.append(entry.path)
                        if len(found_fields) >= 3:
                            confidence = max(confidence, 0.9)
                        else:
                            confidence = max(confidence, 0.5)
                        ev_locs.extend(self.scan_lines(repo_root, entry.path, _MANDATORY_FIELDS, "Model card field"))
                    else:
                        # File exists but fields missing
                        evidence.append(entry.path)
                        missing.extend(
                            [f for f in _MANDATORY_FIELDS if f.lower() not in content.lower()]
                        )
                        confidence = max(confidence, 0.3)

            if not evidence:
                missing.append("No model card or system card found")

        elif control_id == "DOC-02":
            # Check for ADRs or architecture documentation
            for pattern in _ADR_PATTERNS:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    keywords_found = [k for k in _ADR_KEYWORDS if k.lower() in content.lower()]
                    if keywords_found:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.75)
                        ev_locs.extend(self.scan_lines(repo_root, entry.path, _ADR_KEYWORDS, "ADR keyword"))

            if not evidence:
                missing.append("No ADR or architecture documentation found")

        return [
            RawFinding(
                plugin_id=self.plugin_id,
                control_id=control_id,
                evidence_found=evidence,
                missing=missing,
                confidence=confidence,
                evidence_locations=ev_locs,
            )
        ]
