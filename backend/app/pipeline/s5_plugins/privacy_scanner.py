"""privacy_scanner plugin — checks for privacy impact assessments and PII handling docs.

Targets controls with plugin_id "privacy_scanner" (e.g. PRV-01).
Reads files as text only — no code execution.
"""

from app.pipeline.models import EvidenceLocation, ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

# Filenames that commonly contain privacy impact assessments
_PIA_PATTERNS = [
    "*privacy*",
    "*PRIVACY*",
    "*pia*",
    "*PIA*",
    "*data-protection*",
    "*DATA-PROTECTION*",
    "*dpia*",
    "*DPIA*",
]

# Keywords indicating a genuine PIA document
_PIA_KEYWORDS = [
    "privacy impact",
    "data processing",
    "personal data",
    "GDPR",
    "data subject",
    "lawful basis",
    "privacy risk",
    "data protection",
]

# Keywords indicating data processing activities (required for PASS)
_DATA_PROCESSING_KEYWORDS = [
    "data processing activit",
    "processing operations",
    "data flows",
    "data inventory",
]


class PrivacyScanner(BasePlugin):
    """Scans for privacy impact assessments and PII-related documentation."""

    plugin_id = "privacy_scanner"

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

        for pattern in _PIA_PATTERNS:
            for entry in self.filter_manifest(manifest, pattern):
                content = self.read_text(repo_root, entry.path) or ""
                pia_found = [k for k in _PIA_KEYWORDS if k.lower() in content.lower()]
                dp_found = [k for k in _DATA_PROCESSING_KEYWORDS if k.lower() in content.lower()]

                if pia_found:
                    evidence.append(entry.path)
                    ev_locs.extend(self.scan_lines(repo_root, entry.path, _PIA_KEYWORDS, "PIA keyword"))
                    if dp_found:
                        confidence = max(confidence, 0.9)
                        ev_locs.extend(self.scan_lines(repo_root, entry.path, _DATA_PROCESSING_KEYWORDS, "Data processing keyword"))
                    else:
                        confidence = max(confidence, 0.5)
                        missing.append(
                            f"{entry.path}: PIA found but does not reference "
                            "data processing activities"
                        )

        if not evidence:
            missing.append("No privacy impact assessment (PIA/DPIA) document found")
            confidence = 0.0

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
