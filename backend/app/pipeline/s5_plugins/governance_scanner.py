"""governance_scanner plugin — checks for AI governance policy documents.

Targets controls with plugin_id "governance_scanner" (e.g. GOV-01, GOV-02).
Reads files as text only — no code execution.
"""

from app.pipeline.models import ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

# Filenames that commonly contain AI governance policies
_GOVERNANCE_FILENAMES = [
    "*governance*",
    "*GOVERNANCE*",
    "*ai-policy*",
    "*AI-POLICY*",
    "*ethics*",
    "*ETHICS*",
    "*responsible-ai*",
    "*RESPONSIBLE-AI*",
]

# Keywords indicating governance content
_GOVERNANCE_KEYWORDS = [
    "governance",
    "oversight",
    "accountability",
    "responsible AI",
    "AI policy",
    "ethics committee",
    "AI ethics",
]

# Keywords for roles/responsibilities (GOV-02)
_ROLES_KEYWORDS = [
    "role",
    "responsibility",
    "responsible",
    "owner",
    "accountable",
    "AI lead",
    "data officer",
]


class GovernanceScanner(BasePlugin):
    """Scans for AI governance and oversight documentation."""

    plugin_id = "governance_scanner"

    def run(
        self,
        control_id: str,
        manifest: list[ManifestEntry],
        repo_root: str,
    ) -> list[RawFinding]:
        evidence: list[str] = []
        missing: list[str] = []
        confidence = 0.0

        # Find candidate governance documents
        for pattern in _GOVERNANCE_FILENAMES:
            matched = self.filter_manifest(manifest, pattern)
            for entry in matched:
                content = self.read_text(repo_root, entry.path) or ""
                keywords_found = [k for k in _GOVERNANCE_KEYWORDS if k.lower() in content.lower()]
                if keywords_found:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.8)

        if control_id == "GOV-02":
            # Extra check: look for roles/responsibilities keywords
            for entry in self.filter_manifest(manifest, "**/*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                roles_found = [k for k in _ROLES_KEYWORDS if k.lower() in content.lower()]
                if roles_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.5)

        if not evidence:
            missing.append("No governance policy document found")
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
