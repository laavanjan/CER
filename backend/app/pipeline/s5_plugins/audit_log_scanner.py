"""audit_log_scanner plugin — checks for audit log documentation and WORM/append-only compliance.

Targets controls DOC-05 and DOC-06.
Reads files as text only — no code execution.
"""

from app.pipeline.models import ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_AUDIT_LOG_FILENAMES = [
    "*audit*",
    "*AUDIT*",
    "*logging*",
    "*LOGGING*",
    "*log-doc*",
    "*log_doc*",
]

_AUDIT_LOG_DOC_KEYWORDS = [
    "audit log",
    "what is logged",
    "log events",
    "logged events",
    "log retention",
    "log access",
    "audit trail",
    "event logging",
    "log format",
]

_WORM_KEYWORDS = [
    "WORM",
    "write-once",
    "write once",
    "append-only",
    "append only",
    "immutable log",
    "immutable audit",
    "tamper-proof",
    "tamper proof",
    "S3 Object Lock",
    "log immutability",
]

_WORM_CODE_PATTERNS = [
    "append_only",
    "WORM",
    "immutable",
    "object_lock",
    "ObjectLock",
    "s3_lock",
]


class AuditLogScanner(BasePlugin):
    """Scans for audit log documentation and WORM/append-only compliance."""

    plugin_id = "audit_log_scanner"

    def run(
        self,
        control_id: str,
        manifest: list[ManifestEntry],
        repo_root: str,
    ) -> list[RawFinding]:
        evidence: list[str] = []
        missing: list[str] = []
        confidence = 0.0

        if control_id == "DOC-05":
            for pattern in _AUDIT_LOG_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _AUDIT_LOG_DOC_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.85)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _AUDIT_LOG_DOC_KEYWORDS if k.lower() in content.lower()]
                if len(found) >= 2 and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.65)
            if not evidence:
                missing.append("No audit log documentation found")

        elif control_id == "DOC-06":
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                code_found = [p for p in _WORM_CODE_PATTERNS if p in content]
                kw_found = [k for k in _WORM_KEYWORDS if k in content]
                if code_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.85)
                elif kw_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.70)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _WORM_KEYWORDS if k in content]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.80)
            if not evidence:
                missing.append("No WORM or append-only audit store documentation found")

        return [
            RawFinding(
                plugin_id=self.plugin_id,
                control_id=control_id,
                evidence_found=evidence,
                missing=missing,
                confidence=confidence,
            )
        ]
