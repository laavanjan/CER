"""audit_governance_scanner plugin — checks for internal audit schedules, third-party governance, and decommission plans.

Targets controls GOV-08, GOV-09, GOV-10.
Reads files as text only — no code execution.
"""

from app.pipeline.models import EvidenceLocation, ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_AUDIT_KEYWORDS = [
    "internal audit",
    "audit schedule",
    "audit review",
    "periodic review",
    "quarterly review",
    "annual review",
    "compliance review",
    "audit cadence",
]

_THIRD_PARTY_KEYWORDS = [
    "third-party",
    "third party",
    "supplier",
    "subprocessor",
    "vendor",
    "procurement",
    "due diligence",
    "supplier governance",
    "vendor assessment",
]

_DECOMMISSION_KEYWORDS = [
    "decommission",
    "end-of-life",
    "end of life",
    "retirement",
    "sunset",
    "shutdown plan",
    "deprecation",
    "migration plan",
]

_AUDIT_FILENAMES = [
    "*audit*",
    "*AUDIT*",
    "*review*",
    "*compliance*",
    "*COMPLIANCE*",
]

_SUPPLIER_FILENAMES = [
    "*supplier*",
    "*SUPPLIER*",
    "*vendor*",
    "*VENDOR*",
    "*third*party*",
    "*procurement*",
]

_DECOMMISSION_FILENAMES = [
    "*decommission*",
    "*DECOMMISSION*",
    "*end-of-life*",
    "*eol*",
    "*retirement*",
    "*sunset*",
]


class AuditGovernanceScanner(BasePlugin):
    """Scans for audit schedules, third-party governance, and decommission plans."""

    plugin_id = "audit_governance_scanner"

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

        if control_id == "GOV-08":
            for pattern in _AUDIT_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _AUDIT_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.80)
            if not evidence:
                missing.append("No internal audit schedule or periodic review documentation found")

        elif control_id == "GOV-09":
            for pattern in _SUPPLIER_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _THIRD_PARTY_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.80)
            # Also scan all markdown files
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _THIRD_PARTY_KEYWORDS if k.lower() in content.lower()]
                if len(found) >= 2 and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.55)
            if not evidence:
                missing.append("No third-party supplier or subprocessor governance documentation found")

        elif control_id == "GOV-10":
            for pattern in _DECOMMISSION_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _DECOMMISSION_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.85)
            # Also scan markdown files for decommission keywords
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _DECOMMISSION_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.60)
            if not evidence:
                missing.append("No decommission or end-of-life plan found")

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
