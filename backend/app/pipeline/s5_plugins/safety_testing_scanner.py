"""safety_testing_scanner plugin — checks for safety testing, harm prevention, and safety validation docs.

Targets controls SAF-04, SAF-05, SAF-06.
Reads files as text only — no code execution.
"""

from app.pipeline.models import EvidenceLocation, ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_SAFETY_TEST_KEYWORDS = [
    "safety test",
    "safety testing",
    "unsafe output",
    "harmful output",
    "safety scenario",
    "safety case",
    "safety evaluation",
    "safety check",
]

_SAFETY_TEST_CODE_PATTERNS = [
    "test_safety",
    "safety_test",
    "unsafe_output",
    "harmful_output",
    "safety_check",
]

_HARM_PREVENTION_KEYWORDS = [
    "harm prevention",
    "harmful content",
    "content moderation",
    "output filter",
    "content filter",
    "toxicity filter",
    "guardrail",
    "safety guardrail",
    "harmful output prevention",
]

_HARM_PREVENTION_CODE_PATTERNS = [
    "content_filter",
    "output_filter",
    "content_moderation",
    "guardrail",
    "filter_output",
    "moderate_content",
]

_SAFETY_VALIDATION_KEYWORDS = [
    "safety validation",
    "safety sign-off",
    "safety approved",
    "safety clearance",
    "safety review",
    "safety gate",
    "pre-deployment safety",
    "safety acceptance",
]


class SafetyTestingScanner(BasePlugin):
    """Scans for safety testing evidence, harm prevention controls, and safety validation."""

    plugin_id = "safety_testing_scanner"

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

        if control_id == "SAF-04":
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                code_found = [p for p in _SAFETY_TEST_CODE_PATTERNS if p in content]
                kw_found = [k for k in _SAFETY_TEST_KEYWORDS if k.lower() in content.lower()]
                if code_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.90)
                elif kw_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.70)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _SAFETY_TEST_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.65)
            if not evidence:
                missing.append("No safety testing evidence found")

        elif control_id == "SAF-05":
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                code_found = [p for p in _HARM_PREVENTION_CODE_PATTERNS if p in content]
                kw_found = [k for k in _HARM_PREVENTION_KEYWORDS if k.lower() in content.lower()]
                if code_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.90)
                elif kw_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.65)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _HARM_PREVENTION_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.60)
            if not evidence:
                missing.append("No harm prevention controls documented")

        elif control_id == "SAF-06":
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _SAFETY_VALIDATION_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.85)
            if not evidence:
                missing.append("No safety validation sign-off documentation found")

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
