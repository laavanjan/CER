"""dependency_doc_scanner plugin — checks for dependency documentation and training data documentation.

Targets controls DOC-07 and DOC-08.
Reads files as text only — no code execution.
"""

from app.pipeline.models import ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_DEPENDENCY_DOC_FILENAMES = [
    "requirements*.txt",
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    "package.json",
    "Pipfile",
    "pom.xml",
    "build.gradle",
    "*dependencies*",
    "*DEPENDENCIES*",
]

_DEPENDENCY_DOC_KEYWORDS = [
    "dependencies",
    "library",
    "framework",
    "package",
    "licence",
    "license",
    "version",
    "AI framework",
    "ML framework",
]

_DATA_CARD_FILENAMES = [
    "*data_card*",
    "*data-card*",
    "*DATA_CARD*",
    "*DATA-CARD*",
    "*dataset*",
    "*DATASET*",
    "*training_data*",
    "*training-data*",
]

_DATA_CARD_KEYWORDS = [
    "data card",
    "dataset card",
    "training data",
    "training dataset",
    "data source",
    "data collection",
    "dataset description",
    "data provenance",
    "data licence",
    "data license",
    "dataset README",
]


class DependencyDocScanner(BasePlugin):
    """Scans for dependency documentation and training data / data card documentation."""

    plugin_id = "dependency_doc_scanner"

    def run(
        self,
        control_id: str,
        manifest: list[ManifestEntry],
        repo_root: str,
    ) -> list[RawFinding]:
        evidence: list[str] = []
        missing: list[str] = []
        confidence = 0.0

        if control_id == "DOC-07":
            for pattern in _DEPENDENCY_DOC_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    if content:
                        found = [k for k in _DEPENDENCY_DOC_KEYWORDS if k.lower() in content.lower()]
                        if found and entry.path not in evidence:
                            evidence.append(entry.path)
                            # Higher confidence if licence/license info is present
                            if any(
                                "licen" in k.lower() for k in found
                            ):
                                confidence = max(confidence, 0.90)
                            else:
                                confidence = max(confidence, 0.75)
            if not evidence:
                missing.append("No dependency documentation with version and licence information found")

        elif control_id == "DOC-08":
            for pattern in _DATA_CARD_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _DATA_CARD_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.85)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _DATA_CARD_KEYWORDS if k.lower() in content.lower()]
                if len(found) >= 2 and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.65)
            if not evidence:
                missing.append("No training data documentation or data card found")

        return [
            RawFinding(
                plugin_id=self.plugin_id,
                control_id=control_id,
                evidence_found=evidence,
                missing=missing,
                confidence=confidence,
            )
        ]
