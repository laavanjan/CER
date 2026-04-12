"""escalation_scanner plugin — checks for escalation procedures and human-in-the-loop documentation.

Targets controls OVR-03 and OVR-04.
Reads files as text only — no code execution.
"""

from app.pipeline.models import ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_ESCALATION_KEYWORDS = [
    "escalation",
    "escalate",
    "anomaly threshold",
    "threshold breach",
    "escalation procedure",
    "escalation path",
    "on-call",
    "pager duty",
    "escalation owner",
    "escalation matrix",
]

_HITL_KEYWORDS = [
    "human-in-the-loop",
    "human in the loop",
    "HITL",
    "human review",
    "human checkpoint",
    "human approval",
    "human oversight",
    "manual review",
    "human validation",
    "human sign-off",
]

_HITL_CODE_PATTERNS = [
    "human_review",
    "human_approval",
    "hitl",
    "HITL",
    "require_human",
    "manual_review",
]


class EscalationScanner(BasePlugin):
    """Scans for escalation procedures and HITL documentation."""

    plugin_id = "escalation_scanner"

    def run(
        self,
        control_id: str,
        manifest: list[ManifestEntry],
        repo_root: str,
    ) -> list[RawFinding]:
        evidence: list[str] = []
        missing: list[str] = []
        confidence = 0.0

        if control_id == "OVR-03":
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _ESCALATION_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    # Higher confidence if thresholds and owners are mentioned
                    if len(found) >= 2:
                        confidence = max(confidence, 0.85)
                    else:
                        confidence = max(confidence, 0.55)
            if not evidence:
                missing.append("No escalation procedures documented")

        elif control_id == "OVR-04":
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                code_found = [p for p in _HITL_CODE_PATTERNS if p in content]
                kw_found = [k for k in _HITL_KEYWORDS if k.lower() in content.lower()]
                if code_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.90)
                elif kw_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.65)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _HITL_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.65)
            if not evidence:
                missing.append("No human-in-the-loop mechanism documented or implemented")

        return [
            RawFinding(
                plugin_id=self.plugin_id,
                control_id=control_id,
                evidence_found=evidence,
                missing=missing,
                confidence=confidence,
            )
        ]
