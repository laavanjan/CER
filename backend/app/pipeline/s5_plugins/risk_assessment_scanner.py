"""risk_assessment_scanner plugin — checks for AI risk assessment and risk register documents.

Targets controls GOV-03 and GOV-04.
Reads files as text only — no code execution.
"""

from app.pipeline.models import ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_RISK_FILENAMES = [
    "*risk*",
    "*RISK*",
    "*risk-assessment*",
    "*risk_assessment*",
    "*risk-register*",
    "*risk_register*",
]

_RISK_KEYWORDS = [
    "risk assessment",
    "risk identification",
    "risk mitigation",
    "risk management",
    "risk analysis",
    "AI risk",
    "threat",
    "vulnerability",
]

_REGISTER_KEYWORDS = [
    "risk register",
    "risk log",
    "risk owner",
    "risk status",
    "risk id",
    "likelihood",
    "impact",
    "residual risk",
]


class RiskAssessmentScanner(BasePlugin):
    """Scans for AI risk assessment documents and risk registers."""

    plugin_id = "risk_assessment_scanner"

    def run(
        self,
        control_id: str,
        manifest: list[ManifestEntry],
        repo_root: str,
    ) -> list[RawFinding]:
        evidence: list[str] = []
        missing: list[str] = []
        confidence = 0.0

        for pattern in _RISK_FILENAMES:
            for entry in self.filter_manifest(manifest, pattern):
                content = self.read_text(repo_root, entry.path) or ""
                if control_id == "GOV-03":
                    keywords_found = [k for k in _RISK_KEYWORDS if k.lower() in content.lower()]
                    if keywords_found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.85)
                elif control_id == "GOV-04":
                    register_found = [k for k in _REGISTER_KEYWORDS if k.lower() in content.lower()]
                    if register_found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.80)

        if not evidence:
            if control_id == "GOV-03":
                missing.append("No AI risk assessment document found")
            else:
                missing.append("No risk register or risk tracking artefact found")
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
