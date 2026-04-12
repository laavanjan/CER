"""pii_code_scanner plugin — checks for PII masking, anonymisation, and third-party data sharing controls.

Targets controls PRV-06, PRV-07, PRV-08.
Reads files as text only — no code execution.
"""

from app.pipeline.models import ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_PII_MASKING_CODE_PATTERNS = [
    "mask_pii",
    "redact_pii",
    "pii_mask",
    "pii_redact",
    "anonymize",
    "anonymise",
    "pseudonymize",
    "pseudonymise",
    "hash_pii",
    "mask_email",
    "mask_phone",
    "redact(",
    "REDACTED",
]

_PII_MASKING_KEYWORDS = [
    "PII masking",
    "PII redaction",
    "personally identifiable",
    "data masking",
    "data redaction",
    "no PII logged",
    "PII is masked",
    "sensitive data masked",
]

_ANONYMISATION_KEYWORDS = [
    "anonymisation",
    "anonymization",
    "pseudonymisation",
    "pseudonymization",
    "k-anonymity",
    "differential privacy",
    "data de-identification",
    "tokenisation",
    "tokenization",
]

_THIRD_PARTY_SHARING_KEYWORDS = [
    "third-party sharing",
    "third party sharing",
    "data sharing agreement",
    "data transfer",
    "data processor agreement",
    "DPA",
    "data sharing policy",
    "sharing with third parties",
    "external data transfer",
]


class PiiCodeScanner(BasePlugin):
    """Scans for PII masking in code, anonymisation techniques, and third-party sharing controls."""

    plugin_id = "pii_code_scanner"

    def run(
        self,
        control_id: str,
        manifest: list[ManifestEntry],
        repo_root: str,
    ) -> list[RawFinding]:
        evidence: list[str] = []
        missing: list[str] = []
        confidence = 0.0

        if control_id == "PRV-06":
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                code_found = [p for p in _PII_MASKING_CODE_PATTERNS if p in content]
                kw_found = [k for k in _PII_MASKING_KEYWORDS if k.lower() in content.lower()]
                if code_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.90)
                elif kw_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.65)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _PII_MASKING_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.55)
            if not evidence:
                missing.append("No PII masking or redaction found in the codebase")

        elif control_id == "PRV-07":
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _ANONYMISATION_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.85)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _ANONYMISATION_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.65)
            if not evidence:
                missing.append("No data anonymisation or pseudonymisation documentation found")

        elif control_id == "PRV-08":
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _THIRD_PARTY_SHARING_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.80)
            for pattern in ("*dpa*", "*DPA*", "*data-sharing*", "*data_sharing*", "*processor*"):
                for entry in self.filter_manifest(manifest, pattern):
                    if entry.path not in evidence:
                        content = self.read_text(repo_root, entry.path) or ""
                        if content:
                            evidence.append(entry.path)
                            confidence = max(confidence, 0.85)
            if not evidence:
                missing.append("No third-party data sharing agreements or controls documented")

        return [
            RawFinding(
                plugin_id=self.plugin_id,
                control_id=control_id,
                evidence_found=evidence,
                missing=missing,
                confidence=confidence,
            )
        ]
