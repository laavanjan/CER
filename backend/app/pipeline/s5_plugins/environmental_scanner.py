"""environmental_scanner plugin — checks for compute efficiency, carbon tracking, and energy consumption reports.

Targets controls ENV-01, ENV-02, ENV-03.
Reads files as text only — no code execution.
"""

from app.pipeline.models import ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_ENV_FILENAMES = [
    "*environment*",
    "*ENVIRONMENT*",
    "*sustainability*",
    "*SUSTAINABILITY*",
    "*carbon*",
    "*CARBON*",
    "*energy*",
    "*ENERGY*",
    "*green*",
]

_COMPUTE_EFFICIENCY_KEYWORDS = [
    "compute efficiency",
    "model size",
    "model compression",
    "quantization",
    "quantisation",
    "pruning",
    "hardware utilisation",
    "hardware utilization",
    "batching strategy",
    "inference optimisation",
    "inference optimization",
    "efficient inference",
    "model distillation",
]

_CARBON_KEYWORDS = [
    "carbon",
    "carbon footprint",
    "carbon emissions",
    "CO2",
    "CO₂",
    "greenhouse gas",
    "carbon tracking",
    "energy consumption",
    "power usage",
    "watt",
    "kWh",
    "codecarbon",
    "carbontracker",
    "mlco2",
]

_ENERGY_REPORT_KEYWORDS = [
    "energy report",
    "energy consumption report",
    "power consumption",
    "energy usage report",
    "training energy",
    "inference energy",
    "compute carbon",
    "carbon report",
]


class EnvironmentalScanner(BasePlugin):
    """Scans for compute efficiency documentation, carbon tracking, and energy consumption reports."""

    plugin_id = "environmental_scanner"

    def run(
        self,
        control_id: str,
        manifest: list[ManifestEntry],
        repo_root: str,
    ) -> list[RawFinding]:
        evidence: list[str] = []
        missing: list[str] = []
        confidence = 0.0

        if control_id == "ENV-01":
            keywords = _COMPUTE_EFFICIENCY_KEYWORDS
            missing_msg = "No compute efficiency documentation found"
        elif control_id == "ENV-02":
            keywords = _CARBON_KEYWORDS
            missing_msg = "No carbon tracking or energy measurement documentation found"
        else:  # ENV-03
            keywords = _ENERGY_REPORT_KEYWORDS
            missing_msg = "No energy consumption report found"

        for pattern in _ENV_FILENAMES:
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
                confidence = max(confidence, 0.70)

        for entry in self.filter_manifest(manifest, "*.py"):
            content = self.read_text(repo_root, entry.path) or ""
            found = [k for k in keywords if k.lower() in content.lower()]
            if found and entry.path not in evidence:
                evidence.append(entry.path)
                confidence = max(confidence, 0.75)

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
