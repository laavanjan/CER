"""version_manifest_scanner plugin — checks for version manifests and changelogs.

Targets controls DOC-03 and DOC-04.
Reads files as text only — no code execution.
"""

from app.pipeline.models import ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_VERSION_MANIFEST_FILENAMES = [
    "*version*",
    "*VERSION*",
    "*manifest*",
    "*MANIFEST*",
    "versions.json",
    "version.yaml",
    "version.yml",
    "*model-manifest*",
]

_VERSION_MANIFEST_KEYWORDS = [
    "model version",
    "dataset version",
    "library version",
    "version manifest",
    "component version",
    "dependency version",
    "version lock",
    "pinned version",
]

_CHANGELOG_FILENAMES = [
    "CHANGELOG*",
    "changelog*",
    "CHANGES*",
    "changes*",
    "HISTORY*",
    "history*",
    "RELEASE*",
    "release-notes*",
    "NEWS*",
]

_CHANGELOG_KEYWORDS = [
    "changelog",
    "change log",
    "release notes",
    "version history",
    "what's new",
    "breaking change",
    "added",
    "changed",
    "fixed",
    "deprecated",
]


class VersionManifestScanner(BasePlugin):
    """Scans for version manifests and changelog documentation."""

    plugin_id = "version_manifest_scanner"

    def run(
        self,
        control_id: str,
        manifest: list[ManifestEntry],
        repo_root: str,
    ) -> list[RawFinding]:
        evidence: list[str] = []
        missing: list[str] = []
        confidence = 0.0

        if control_id == "DOC-03":
            for pattern in _VERSION_MANIFEST_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _VERSION_MANIFEST_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        if len(found) >= 3:
                            confidence = max(confidence, 0.90)
                        else:
                            confidence = max(confidence, 0.65)
            if not evidence:
                missing.append("No version manifest found")

        elif control_id == "DOC-04":
            for pattern in _CHANGELOG_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    if content:
                        found = [k for k in _CHANGELOG_KEYWORDS if k.lower() in content.lower()]
                        if found and entry.path not in evidence:
                            evidence.append(entry.path)
                            confidence = max(confidence, 0.90)
            if not evidence:
                missing.append("No changelog or release notes found")

        return [
            RawFinding(
                plugin_id=self.plugin_id,
                control_id=control_id,
                evidence_found=evidence,
                missing=missing,
                confidence=confidence,
            )
        ]
