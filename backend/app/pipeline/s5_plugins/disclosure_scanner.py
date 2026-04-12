"""disclosure_scanner plugin — checks for AI disclosure notices, uncertainty communication, and decision logging.

Targets controls TRN-03, TRN-04, TRN-05.
Reads files as text only — no code execution.
"""

from app.pipeline.models import ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_DISCLOSURE_FILENAMES = [
    "*disclos*",
    "*DISCLOS*",
    "*notice*",
    "*NOTICE*",
    "*ai-disclosure*",
    "*terms*",
    "*TERMS*",
]

_DISCLOSURE_KEYWORDS = [
    "AI disclosure",
    "you are interacting with an AI",
    "this is an AI",
    "AI system",
    "artificial intelligence",
    "automated decision",
    "AI-powered",
    "machine learning",
    "AI assistant",
]

_UNCERTAINTY_KEYWORDS = [
    "confidence score",
    "uncertainty",
    "confidence level",
    "prediction confidence",
    "probability",
    "confidence interval",
    "error margin",
    "reliability score",
    "calibration",
]

_DECISION_LOG_KEYWORDS = [
    "decision log",
    "decision logging",
    "log the decision",
    "audit log",
    "output log",
    "prediction log",
    "inference log",
    "decision record",
]

_DECISION_LOG_CODE_PATTERNS = [
    "log_decision",
    "decision_log",
    "log_prediction",
    "prediction_log",
    "audit_log",
    "log_output",
]


class DisclosureScanner(BasePlugin):
    """Scans for AI disclosure notices, uncertainty communication, and decision logging."""

    plugin_id = "disclosure_scanner"

    def run(
        self,
        control_id: str,
        manifest: list[ManifestEntry],
        repo_root: str,
    ) -> list[RawFinding]:
        evidence: list[str] = []
        missing: list[str] = []
        confidence = 0.0

        if control_id == "TRN-03":
            for pattern in _DISCLOSURE_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _DISCLOSURE_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.85)
            # Frontend files often contain disclosure notices
            for pattern in ("*.tsx", "*.jsx", "*.html", "*.vue"):
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _DISCLOSURE_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.80)
            if not evidence:
                missing.append("No AI disclosure notice found")

        elif control_id == "TRN-04":
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _UNCERTAINTY_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.80)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _UNCERTAINTY_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.60)
            if not evidence:
                missing.append("No output uncertainty or confidence level communication found")

        elif control_id == "TRN-05":
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                kw_found = [k for k in _DECISION_LOG_KEYWORDS if k.lower() in content.lower()]
                code_found = [p for p in _DECISION_LOG_CODE_PATTERNS if p in content]
                if (kw_found or code_found) and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.85)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _DECISION_LOG_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.55)
            if not evidence:
                missing.append("No decision logging implementation found")

        return [
            RawFinding(
                plugin_id=self.plugin_id,
                control_id=control_id,
                evidence_found=evidence,
                missing=missing,
                confidence=confidence,
            )
        ]
