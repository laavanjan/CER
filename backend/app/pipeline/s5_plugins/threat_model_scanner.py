"""threat_model_scanner plugin — checks for threat models and adversarial robustness testing documentation.

Targets controls SEC-01 and SEC-02.
Reads files as text only — no code execution.
"""

from app.pipeline.models import ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_THREAT_MODEL_FILENAMES = [
    "*threat*",
    "*THREAT*",
    "*threat-model*",
    "*threat_model*",
    "*security*",
    "*SECURITY*",
    "*attack*",
]

_THREAT_MODEL_KEYWORDS = [
    "threat model",
    "threat modelling",
    "threat modeling",
    "attack vector",
    "attack surface",
    "mitigation",
    "STRIDE",
    "PASTA",
    "data poisoning",
    "model inversion",
    "adversarial input",
    "prompt injection",
    "AI-specific threat",
]

_ADVERSARIAL_KEYWORDS = [
    "adversarial",
    "adversarial example",
    "adversarial testing",
    "adversarial robustness",
    "robustness test",
    "red team",
    "red-team",
    "prompt injection",
    "jailbreak",
    "adversarial attack",
    "perturbation",
]


class ThreatModelScanner(BasePlugin):
    """Scans for threat models and adversarial robustness testing documentation."""

    plugin_id = "threat_model_scanner"

    def run(
        self,
        control_id: str,
        manifest: list[ManifestEntry],
        repo_root: str,
    ) -> list[RawFinding]:
        evidence: list[str] = []
        missing: list[str] = []
        confidence = 0.0

        if control_id == "SEC-01":
            keywords = _THREAT_MODEL_KEYWORDS
            missing_msg = "No threat model document found"
        else:  # SEC-02
            keywords = _ADVERSARIAL_KEYWORDS
            missing_msg = "No adversarial robustness testing documentation found"

        for pattern in _THREAT_MODEL_FILENAMES:
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
                confidence = max(confidence, 0.65)

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
