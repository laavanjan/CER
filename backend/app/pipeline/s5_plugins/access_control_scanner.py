"""access_control_scanner plugin — checks for access controls, secrets management, input validation, and security testing.

Targets controls SEC-05, SEC-06, SEC-07, SEC-08.
Reads files as text only — no code execution.
"""

from app.pipeline.models import ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_ACCESS_CONTROL_KEYWORDS = [
    "access control",
    "role-based access",
    "RBAC",
    "permission",
    "authorisation",
    "authorization",
    "authentication",
    "least privilege",
    "access policy",
    "model access",
    "data access",
]

# Patterns suggesting hardcoded secrets
_SECRET_PATTERNS = [
    'password = "',
    "password = '",
    'api_key = "',
    "api_key = '",
    'secret = "',
    "secret = '",
    'token = "',
    "token = '",
    "AWS_SECRET",
    "PRIVATE_KEY",
    "-----BEGIN",
]

# Patterns indicating proper secrets management
_SECRETS_MANAGEMENT_PATTERNS = [
    "os.environ",
    "os.getenv",
    "dotenv",
    ".env",
    "secrets manager",
    "vault",
    "KeyVault",
    "Secret Manager",
    "environment variable",
]

_INPUT_VALIDATION_CODE_PATTERNS = [
    "validate(",
    "validator",
    "schema.validate",
    "pydantic",
    "marshmallow",
    "cerberus",
    "jsonschema",
    "sanitize",
    "sanitise",
]

_INPUT_VALIDATION_KEYWORDS = [
    "input validation",
    "validate input",
    "sanitize input",
    "input sanitisation",
    "schema validation",
    "input schema",
]

_SECURITY_TEST_KEYWORDS = [
    "SAST",
    "DAST",
    "penetration test",
    "pentest",
    "security scan",
    "bandit",
    "semgrep",
    "CodeQL",
    "OWASP",
    "security audit",
]


class AccessControlScanner(BasePlugin):
    """Scans for access controls, secrets management, input validation, and security testing."""

    plugin_id = "access_control_scanner"

    def run(
        self,
        control_id: str,
        manifest: list[ManifestEntry],
        repo_root: str,
    ) -> list[RawFinding]:
        evidence: list[str] = []
        missing: list[str] = []
        confidence = 0.0

        if control_id == "SEC-05":
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _ACCESS_CONTROL_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.80)
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _ACCESS_CONTROL_KEYWORDS if k.lower() in content.lower()]
                if len(found) >= 2 and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.75)
            if not evidence:
                missing.append("No access control documentation for AI artefacts found")

        elif control_id == "SEC-06":
            # Look for proper secrets management AND absence of hardcoded secrets
            secrets_found = False
            env_patterns_found = False
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                if any(p in content for p in _SECRET_PATTERNS):
                    secrets_found = True
                    missing.append(f"{entry.path}: potential hardcoded credential detected")
                if any(p in content for p in _SECRETS_MANAGEMENT_PATTERNS):
                    env_patterns_found = True
                    if entry.path not in evidence:
                        evidence.append(entry.path)
            if env_patterns_found and not secrets_found:
                confidence = 0.85
            elif env_patterns_found and secrets_found:
                confidence = 0.40
            elif not env_patterns_found:
                if not missing:
                    missing.append("No secrets management pattern found")
                confidence = 0.0

        elif control_id == "SEC-07":
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                code_found = [p for p in _INPUT_VALIDATION_CODE_PATTERNS if p in content]
                kw_found = [k for k in _INPUT_VALIDATION_KEYWORDS if k.lower() in content.lower()]
                if code_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.85)
                elif kw_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.60)
            if not evidence:
                missing.append("No input validation implementation found in the AI pipeline")

        elif control_id == "SEC-08":
            for pattern in (".github/workflows/*.yml", ".github/workflows/*.yaml", "*.yml", "*.yaml"):
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _SECURITY_TEST_KEYWORDS if k in content]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.85)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _SECURITY_TEST_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.65)
            if not evidence:
                missing.append("No security testing documentation found")

        return [
            RawFinding(
                plugin_id=self.plugin_id,
                control_id=control_id,
                evidence_found=evidence,
                missing=missing,
                confidence=confidence,
            )
        ]
