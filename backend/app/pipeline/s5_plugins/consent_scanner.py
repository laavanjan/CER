"""consent_scanner plugin — checks for consent mechanisms and data minimisation documentation.

Targets controls PRV-02 and PRV-03.
Reads files as text only — no code execution.
"""

from app.pipeline.models import ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_CONSENT_FILENAMES = [
    "*consent*",
    "*CONSENT*",
    "*terms*",
    "*TERMS*",
    "*cookie*",
    "*COOKIE*",
]

_CONSENT_KEYWORDS = [
    "consent",
    "opt-in",
    "opt in",
    "user consent",
    "informed consent",
    "explicit consent",
    "data consent",
    "consent mechanism",
    "permission",
    "authorisation",
]

_MINIMISATION_KEYWORDS = [
    "data minimisation",
    "data minimization",
    "minimum necessary",
    "least privilege",
    "only necessary",
    "purpose limitation",
    "minimal data",
    "data reduction",
    "collect only",
]


class ConsentScanner(BasePlugin):
    """Scans for consent mechanisms and data minimisation documentation."""

    plugin_id = "consent_scanner"

    def run(
        self,
        control_id: str,
        manifest: list[ManifestEntry],
        repo_root: str,
    ) -> list[RawFinding]:
        evidence: list[str] = []
        missing: list[str] = []
        confidence = 0.0

        if control_id == "PRV-02":
            for pattern in _CONSENT_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _CONSENT_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.85)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _CONSENT_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.60)
            for pattern in ("*.py", "*.ts", "*.tsx"):
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _CONSENT_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.70)
            if not evidence:
                missing.append("No consent mechanism documented or implemented")

        elif control_id == "PRV-03":
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _MINIMISATION_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.80)
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _MINIMISATION_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.70)
            if not evidence:
                missing.append("No data minimisation principles documented or applied")

        return [
            RawFinding(
                plugin_id=self.plugin_id,
                control_id=control_id,
                evidence_found=evidence,
                missing=missing,
                confidence=confidence,
            )
        ]
