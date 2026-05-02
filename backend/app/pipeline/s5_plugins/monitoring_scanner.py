"""monitoring_scanner plugin — checks for performance monitoring, alerting, and review cadence documentation.

Targets controls OVR-05, OVR-06, OVR-07.
Reads files as text only — no code execution.
"""

from app.pipeline.models import EvidenceLocation, ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_PERF_MONITORING_KEYWORDS = [
    "performance monitoring",
    "model performance",
    "accuracy monitoring",
    "drift monitoring",
    "performance metric",
    "KPI monitoring",
    "tracking performance",
    "performance tracking",
    "monitoring configuration",
]

_ALERTING_KEYWORDS = [
    "alert",
    "alerting",
    "notification",
    "alarm",
    "pagerduty",
    "opsgenie",
    "on-call alert",
    "alert threshold",
    "anomaly alert",
    "alert rule",
]

_ALERTING_CONFIG_PATTERNS = [
    "alert:",
    "alerting:",
    "alarms:",
    "notifications:",
    "pagerduty",
    "opsgenie",
    "webhook",
]

_REVIEW_CADENCE_KEYWORDS = [
    "review cadence",
    "quarterly review",
    "monthly review",
    "annual review",
    "periodic review",
    "review schedule",
    "review cycle",
    "performance review",
    "model review",
]


class MonitoringScanner(BasePlugin):
    """Scans for performance monitoring, alerting configuration, and review cadence documentation."""

    plugin_id = "monitoring_scanner"

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

        if control_id == "OVR-05":
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _PERF_MONITORING_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.80)
            for pattern in ("*.yml", "*.yaml"):
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _PERF_MONITORING_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.80)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _PERF_MONITORING_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.60)
            if not evidence:
                missing.append("No performance monitoring configuration found")

        elif control_id == "OVR-06":
            for pattern in ("*.yml", "*.yaml", ".github/workflows/*.yml"):
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    config_found = [p for p in _ALERTING_CONFIG_PATTERNS if p in content]
                    kw_found = [k for k in _ALERTING_KEYWORDS if k.lower() in content.lower()]
                    if (config_found or kw_found) and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.85)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _ALERTING_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.60)
            if not evidence:
                missing.append("No alerting mechanism found for AI anomaly detection")

        elif control_id == "OVR-07":
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _REVIEW_CADENCE_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.80)
            if not evidence:
                missing.append("No documented AI review cadence found")

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
