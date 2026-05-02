"""human_override_scanner plugin — checks for human override mechanisms and monitoring dashboards.

Targets controls OVR-01 and OVR-02.
Reads files as text only — no code execution.
"""

from app.pipeline.models import EvidenceLocation, ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_OVERRIDE_KEYWORDS = [
    "human override",
    "manual override",
    "override mechanism",
    "human intervention",
    "operator override",
    "kill switch",
    "stop AI",
    "disable AI",
    "human control",
    "human takeover",
]

_MONITORING_KEYWORDS = [
    "monitoring dashboard",
    "observability",
    "real-time monitoring",
    "system monitoring",
    "model monitoring",
    "performance dashboard",
    "grafana",
    "prometheus",
    "kibana",
    "datadog",
    "cloudwatch",
    "metrics dashboard",
]

_MONITORING_CODE_PATTERNS = [
    "prometheus",
    "grafana",
    "datadog",
    "cloudwatch",
    "metrics.gauge",
    "metrics.counter",
    "StatsD",
    "statsd",
    "telemetry",
]


class HumanOverrideScanner(BasePlugin):
    """Scans for human override mechanisms and monitoring dashboard documentation."""

    plugin_id = "human_override_scanner"

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

        if control_id == "OVR-01":
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _OVERRIDE_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.85)
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _OVERRIDE_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.75)
            if not evidence:
                missing.append("No human override mechanism documented")

        elif control_id == "OVR-02":
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                code_found = [p for p in _MONITORING_CODE_PATTERNS if p.lower() in content.lower()]
                if code_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.85)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _MONITORING_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.70)
            for pattern in ("*.yml", "*.yaml", "docker-compose*.yml"):
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    code_found = [p for p in _MONITORING_CODE_PATTERNS if p.lower() in content.lower()]
                    if code_found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.80)
            if not evidence:
                missing.append("No AI monitoring dashboard or visibility tool found")

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
