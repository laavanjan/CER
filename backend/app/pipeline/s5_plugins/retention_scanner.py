"""retention_scanner plugin — checks for data retention policies and right-to-erasure procedures.

Targets controls PRV-04 and PRV-05.
Reads files as text only — no code execution.
"""

from app.pipeline.models import ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_RETENTION_FILENAMES = [
    "*retention*",
    "*RETENTION*",
    "*data-policy*",
    "*data_policy*",
    "*privacy*",
    "*PRIVACY*",
    "*gdpr*",
    "*GDPR*",
]

_RETENTION_KEYWORDS = [
    "retention period",
    "data retention",
    "retention policy",
    "keep data for",
    "stored for",
    "deletion schedule",
    "purge",
    "data lifecycle",
    "expiry",
    "expiration",
]

_ERASURE_KEYWORDS = [
    "right to erasure",
    "right to be forgotten",
    "right of erasure",
    "data deletion",
    "delete personal data",
    "erasure request",
    "deletion request",
    "data removal",
    "GDPR Article 17",
    "subject access request",
]


class RetentionScanner(BasePlugin):
    """Scans for data retention policies and right-to-erasure procedures."""

    plugin_id = "retention_scanner"

    def run(
        self,
        control_id: str,
        manifest: list[ManifestEntry],
        repo_root: str,
    ) -> list[RawFinding]:
        evidence: list[str] = []
        missing: list[str] = []
        confidence = 0.0

        if control_id == "PRV-04":
            keywords = _RETENTION_KEYWORDS
            missing_msg = "No data retention policy found"
        else:  # PRV-05
            keywords = _ERASURE_KEYWORDS
            missing_msg = "No right-to-erasure procedure documented"

        for pattern in _RETENTION_FILENAMES:
            for entry in self.filter_manifest(manifest, pattern):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in keywords if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.85)

        for entry in self.filter_manifest(manifest, "*.md"):
            content = self.read_text(repo_root, entry.path) or ""
            found = [k for k in keywords if k.lower() in content.lower()]
            if found and entry.path not in evidence:
                evidence.append(entry.path)
                confidence = max(confidence, 0.60)

        if not evidence:
            missing.append(missing_msg)
            confidence = 0.0

        return [
            RawFinding(
                plugin_id=self.plugin_id,
                control_id=control_id,
                evidence_found=evidence,
                missing=missing,
                confidence=confidence,
            )
        ]
