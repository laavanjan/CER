"""fairness_metrics_scanner plugin — checks for demographic parity, equalized odds, and fairness reports.

Targets controls FAR-03, FAR-04, FAR-05.
Reads files as text only — no code execution.
"""

from app.pipeline.models import EvidenceLocation, ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_FAIRNESS_FILENAMES = [
    "*fairness*",
    "*FAIRNESS*",
    "*equity*",
    "*EQUITY*",
    "*parity*",
    "*metrics*",
]

_DEMOGRAPHIC_PARITY_KEYWORDS = [
    "demographic parity",
    "statistical parity",
    "group fairness",
    "parity metric",
    "disparate impact ratio",
    "selection rate",
    "positive rate parity",
]

_EQUALIZED_ODDS_KEYWORDS = [
    "equalized odds",
    "equal opportunity",
    "individual fairness",
    "calibrated fairness",
    "predictive parity",
    "false positive rate",
    "true positive rate parity",
    "error rate balance",
]

_FAIRNESS_REPORT_KEYWORDS = [
    "fairness report",
    "fairness evaluation",
    "fairness results",
    "fairness metrics report",
    "protected group",
    "subgroup analysis",
    "disparity analysis",
    "fairness summary",
]


class FairnessMetricsScanner(BasePlugin):
    """Scans for demographic parity, equalized odds metrics, and fairness evaluation reports."""

    plugin_id = "fairness_metrics_scanner"

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

        if control_id == "FAR-03":
            keywords = _DEMOGRAPHIC_PARITY_KEYWORDS
            missing_msg = "No demographic parity or group fairness metric found"
        elif control_id == "FAR-04":
            keywords = _EQUALIZED_ODDS_KEYWORDS
            missing_msg = "No equalized odds or individual-fairness metric found"
        else:  # FAR-05
            keywords = _FAIRNESS_REPORT_KEYWORDS
            missing_msg = "No fairness evaluation report found"

        for pattern in _FAIRNESS_FILENAMES:
            for entry in self.filter_manifest(manifest, pattern):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in keywords if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.85)

        for entry in self.filter_manifest(manifest, "*.py"):
            content = self.read_text(repo_root, entry.path) or ""
            found = [k for k in keywords if k.lower() in content.lower()]
            if found and entry.path not in evidence:
                evidence.append(entry.path)
                confidence = max(confidence, 0.80)

        for entry in self.filter_manifest(manifest, "*.md"):
            content = self.read_text(repo_root, entry.path) or ""
            found = [k for k in keywords if k.lower() in content.lower()]
            if found and entry.path not in evidence:
                evidence.append(entry.path)
                confidence = max(confidence, 0.65)

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
                evidence_locations=ev_locs,
            )
        ]
