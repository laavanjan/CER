"""discrimination_scanner plugin — checks for anti-discrimination policies and protected attribute handling docs.

Targets controls FAR-06 and FAR-07.
Reads files as text only — no code execution.
"""

from app.pipeline.models import EvidenceLocation, ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_POLICY_FILENAMES = [
    "*anti-discrimination*",
    "*nondiscrimination*",
    "*non-discrimination*",
    "*equal*",
    "*EQUAL*",
    "*policy*",
    "*POLICY*",
]

_ANTI_DISCRIMINATION_KEYWORDS = [
    "anti-discrimination",
    "non-discrimination",
    "no discrimination",
    "equal treatment",
    "protected class",
    "equitable outcome",
    "discrimination policy",
    "AI non-discrimination",
]

_PROTECTED_ATTR_KEYWORDS = [
    "protected attribute",
    "sensitive attribute",
    "race",
    "gender",
    "age",
    "religion",
    "disability",
    "national origin",
    "protected characteristic",
    "sensitive feature",
    "demographic feature",
]

_PROTECTED_ATTR_CODE_PATTERNS = [
    "protected_attribute",
    "sensitive_attribute",
    "protected_feature",
    "sensitive_feature",
    "demographic_group",
]


class DiscriminationScanner(BasePlugin):
    """Scans for anti-discrimination policies and protected attribute handling documentation."""

    plugin_id = "discrimination_scanner"

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

        if control_id == "FAR-06":
            for pattern in _POLICY_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _ANTI_DISCRIMINATION_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.85)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _ANTI_DISCRIMINATION_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.60)
            if not evidence:
                missing.append("No anti-discrimination policy for AI outputs found")

        elif control_id == "FAR-07":
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                code_found = [p for p in _PROTECTED_ATTR_CODE_PATTERNS if p in content]
                kw_found = [k for k in _PROTECTED_ATTR_KEYWORDS if k.lower() in content.lower()]
                if (code_found or kw_found) and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.80)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _PROTECTED_ATTR_KEYWORDS if k.lower() in content.lower()]
                if len(found) >= 2 and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.65)
            if not evidence:
                missing.append("No protected attribute handling documentation found")

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
