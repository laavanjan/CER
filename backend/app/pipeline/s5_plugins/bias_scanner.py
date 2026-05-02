"""bias_scanner plugin — checks for bias testing documentation and bias mitigation techniques.

Targets controls FAR-01 and FAR-02.
Reads files as text only — no code execution.
"""

from app.pipeline.models import EvidenceLocation, ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_BIAS_FILENAMES = [
    "*bias*",
    "*BIAS*",
    "*fairness*",
    "*FAIRNESS*",
    "*equity*",
    "*EQUITY*",
]

_BIAS_TEST_KEYWORDS = [
    "bias testing",
    "bias test",
    "bias evaluation",
    "bias detection",
    "bias analysis",
    "protected characteristic",
    "protected attribute",
    "disparate impact",
    "demographic bias",
    "bias audit",
]

_BIAS_MITIGATION_KEYWORDS = [
    "bias mitigation",
    "debiasing",
    "re-weighting",
    "reweighting",
    "resampling",
    "adversarial debiasing",
    "fairness constraint",
    "bias correction",
    "calibration",
    "counterfactual fairness",
]


class BiasScanner(BasePlugin):
    """Scans for bias testing documentation and bias mitigation techniques."""

    plugin_id = "bias_scanner"

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

        if control_id == "FAR-01":
            keywords = _BIAS_TEST_KEYWORDS
            missing_msg = "No bias testing documentation or tooling found"
        else:  # FAR-02
            keywords = _BIAS_MITIGATION_KEYWORDS
            missing_msg = "No bias mitigation techniques documented"

        for pattern in _BIAS_FILENAMES:
            for entry in self.filter_manifest(manifest, pattern):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in keywords if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.85)
                    ev_locs.extend(self.scan_lines(repo_root, entry.path, keywords, "Bias keyword"))

        for entry in self.filter_manifest(manifest, "*.py"):
            content = self.read_text(repo_root, entry.path) or ""
            found = [k for k in keywords if k.lower() in content.lower()]
            if found and entry.path not in evidence:
                evidence.append(entry.path)
                confidence = max(confidence, 0.80)
                ev_locs.extend(self.scan_lines(repo_root, entry.path, keywords, "Bias keyword"))

        for entry in self.filter_manifest(manifest, "*.md"):
            content = self.read_text(repo_root, entry.path) or ""
            found = [k for k in keywords if k.lower() in content.lower()]
            if found and entry.path not in evidence:
                evidence.append(entry.path)
                confidence = max(confidence, 0.60)
                ev_locs.extend(self.scan_lines(repo_root, entry.path, keywords, "Bias keyword"))

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
