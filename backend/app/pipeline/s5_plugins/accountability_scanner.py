"""accountability_scanner plugin — checks for accountability frameworks, incident response, and change approval docs.

Targets controls GOV-05, GOV-06, GOV-07.
Reads files as text only — no code execution.
"""

from app.pipeline.models import EvidenceLocation, ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_ACCOUNTABILITY_FILENAMES = [
    "*accountab*",
    "*ACCOUNTAB*",
    "*ownership*",
    "*OWNERSHIP*",
    "*responsible*",
    "*RESPONSIBLE*",
]

_INCIDENT_FILENAMES = [
    "*incident*",
    "*INCIDENT*",
    "*response*",
    "*RESPONSE*",
    "*runbook*",
    "*RUNBOOK*",
    "*playbook*",
    "*PLAYBOOK*",
]

_CHANGE_FILENAMES = [
    "*change*",
    "*CHANGE*",
    "*approval*",
    "*APPROVAL*",
    "*sign-off*",
    "*signoff*",
    "*release*",
    "*RELEASE*",
]

_ACCOUNTABILITY_KEYWORDS = [
    "accountability",
    "accountable",
    "decision owner",
    "AI owner",
    "responsible party",
    "ownership",
    "sign-off",
]

_INCIDENT_KEYWORDS = [
    "incident response",
    "AI failure",
    "incident management",
    "escalation",
    "remediation",
    "post-mortem",
    "root cause",
    "failure mode",
]

_CHANGE_KEYWORDS = [
    "change approval",
    "sign-off",
    "approval process",
    "release gate",
    "change control",
    "sign off",
    "review and approve",
]


class AccountabilityScanner(BasePlugin):
    """Scans for accountability frameworks, incident response plans, and change approval docs."""

    plugin_id = "accountability_scanner"

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

        if control_id == "GOV-05":
            for pattern in _ACCOUNTABILITY_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _ACCOUNTABILITY_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.8)
            # Also scan markdown files for accountability keywords
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _ACCOUNTABILITY_KEYWORDS if k.lower() in content.lower()]
                if len(found) >= 2 and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.55)
            if not evidence:
                missing.append("No accountability framework document found")

        elif control_id == "GOV-06":
            for pattern in _INCIDENT_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _INCIDENT_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.85)
            if not evidence:
                missing.append("No incident response plan found")

        elif control_id == "GOV-07":
            for pattern in _CHANGE_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _CHANGE_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.80)
            if not evidence:
                missing.append("No change approval or sign-off process documentation found")

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
