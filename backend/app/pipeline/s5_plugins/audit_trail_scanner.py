"""audit_trail_scanner plugin — checks for audit trail documentation, user notifications, and version transparency.

Targets controls TRN-06, TRN-07, TRN-08.
Reads files as text only — no code execution.
"""

from app.pipeline.models import ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_AUDIT_DOC_FILENAMES = [
    "*audit*",
    "*AUDIT*",
    "*logging*",
    "*LOGGING*",
    "*log-policy*",
    "*log_policy*",
]

_AUDIT_DOC_KEYWORDS = [
    "audit trail",
    "audit log",
    "what is logged",
    "log retention",
    "retention period",
    "log access",
    "access control",
    "log events",
    "logged events",
]

_NOTIFICATION_KEYWORDS = [
    "notify user",
    "user notification",
    "limitation notice",
    "system limitation",
    "AI limitation",
    "inform the user",
    "warn the user",
    "user warning",
    "disclaimer",
]

_VERSION_CODE_PATTERNS = [
    "__version__",
    "model_version",
    "MODEL_VERSION",
    "version_id",
    "VERSION",
    "model.version",
]

_VERSION_KEYWORDS = [
    "model version",
    "version transparency",
    "version reporting",
    "current version",
    "model v",
    "version manifest",
]


class AuditTrailScanner(BasePlugin):
    """Scans for audit trail docs, user notification mechanisms, and version transparency."""

    plugin_id = "audit_trail_scanner"

    def run(
        self,
        control_id: str,
        manifest: list[ManifestEntry],
        repo_root: str,
    ) -> list[RawFinding]:
        evidence: list[str] = []
        missing: list[str] = []
        confidence = 0.0

        if control_id == "TRN-06":
            for pattern in _AUDIT_DOC_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _AUDIT_DOC_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        # Higher confidence if retention AND access controls mentioned
                        if any(
                            "retention" in k.lower() for k in found
                        ) and any(
                            "access" in k.lower() for k in found
                        ):
                            confidence = max(confidence, 0.90)
                        else:
                            confidence = max(confidence, 0.60)
            if not evidence:
                missing.append(
                    "No audit trail documentation found covering retention and access controls"
                )

        elif control_id == "TRN-07":
            for pattern in ("*.py", "*.tsx", "*.jsx", "*.ts", "*.js"):
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _NOTIFICATION_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.80)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _NOTIFICATION_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.55)
            if not evidence:
                missing.append("No user notification mechanism for AI limitations documented")

        elif control_id == "TRN-08":
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                code_found = [p for p in _VERSION_CODE_PATTERNS if p in content]
                if code_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.85)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _VERSION_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.65)
            if not evidence:
                missing.append("No model version transparency mechanism found")

        return [
            RawFinding(
                plugin_id=self.plugin_id,
                control_id=control_id,
                evidence_found=evidence,
                missing=missing,
                confidence=confidence,
            )
        ]
