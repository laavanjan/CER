"""safe_failure_scanner plugin — checks for safe failure modes, fallback mechanisms, and hazard identification.

Targets controls SAF-01, SAF-02, SAF-03.
Reads files as text only — no code execution.
"""

from app.pipeline.models import ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_SAFE_FAILURE_KEYWORDS = [
    "safe failure",
    "fail safe",
    "fail-safe",
    "graceful degradation",
    "graceful failure",
    "safe mode",
    "safe default",
    "failure mode",
    "error handling",
]

_FALLBACK_KEYWORDS = [
    "fallback",
    "fall back",
    "fallback mechanism",
    "default response",
    "rule-based fallback",
    "human handoff",
    "backup system",
    "degraded mode",
    "circuit breaker",
]

_HAZARD_KEYWORDS = [
    "hazard",
    "hazard identification",
    "hazard analysis",
    "FMEA",
    "failure mode and effects",
    "hazard register",
    "risk hazard",
    "safety hazard",
    "hazardous scenario",
]

_FALLBACK_CODE_PATTERNS = [
    "fallback",
    "circuit_breaker",
    "CircuitBreaker",
    "default_response",
    "safe_default",
    "handle_failure",
    "on_error",
]


class SafeFailureScanner(BasePlugin):
    """Scans for safe failure modes, fallback mechanisms, and hazard identification."""

    plugin_id = "safe_failure_scanner"

    def run(
        self,
        control_id: str,
        manifest: list[ManifestEntry],
        repo_root: str,
    ) -> list[RawFinding]:
        evidence: list[str] = []
        missing: list[str] = []
        confidence = 0.0

        if control_id == "SAF-01":
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _SAFE_FAILURE_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.80)
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _SAFE_FAILURE_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.70)
            if not evidence:
                missing.append("No safe failure mode documentation found")

        elif control_id == "SAF-02":
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                code_found = [p for p in _FALLBACK_CODE_PATTERNS if p in content]
                kw_found = [k for k in _FALLBACK_KEYWORDS if k.lower() in content.lower()]
                if code_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.85)
                elif kw_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.65)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _FALLBACK_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.60)
            if not evidence:
                missing.append("No fallback mechanism documented or implemented")

        elif control_id == "SAF-03":
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _HAZARD_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.85)
            for pattern in ("*hazard*", "*HAZARD*", "*fmea*", "*FMEA*", "*safety*"):
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    if content and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.85)
            if not evidence:
                missing.append("No hazard identification documentation found")

        return [
            RawFinding(
                plugin_id=self.plugin_id,
                control_id=control_id,
                evidence_found=evidence,
                missing=missing,
                confidence=confidence,
            )
        ]
