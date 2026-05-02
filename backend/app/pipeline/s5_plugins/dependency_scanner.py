"""dependency_scanner plugin — checks for dependency lockfiles and vulnerability scanning configuration.

Targets controls SEC-03 and SEC-04.
Reads files as text only — no code execution.
"""

from app.pipeline.models import EvidenceLocation, ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

# Lockfile and pinned dependency file names
_LOCKFILE_PATTERNS = [
    "requirements*.txt",
    "Pipfile.lock",
    "poetry.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Cargo.lock",
    "go.sum",
    "Gemfile.lock",
    "composer.lock",
]

# Vulnerability scanning configuration files
_VULN_SCAN_FILENAMES = [
    ".github/dependabot.yml",
    ".github/dependabot.yaml",
    "*snyk*",
    "*SNYK*",
    "*.snyk",
    "*pip-audit*",
    "*safety*",
    "*trivy*",
    "*TRIVY*",
    "*grype*",
]

_VULN_SCAN_KEYWORDS = [
    "dependabot",
    "snyk",
    "pip-audit",
    "safety check",
    "trivy",
    "grype",
    "vulnerability scan",
    "security scan",
    "dependency scan",
    "CVE",
]


class DependencyScanner(BasePlugin):
    """Scans for dependency lockfiles and vulnerability scanning configuration."""

    plugin_id = "dependency_scanner"

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

        if control_id == "SEC-03":
            # Check for lockfiles
            for pattern in _LOCKFILE_PATTERNS:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    if content and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.90)
            if not evidence:
                missing.append("No dependency lockfile or pinned manifest found")

        elif control_id == "SEC-04":
            for pattern in _VULN_SCAN_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    if content and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.90)
            # Also check CI config files for vulnerability scanning steps
            for pattern in (".github/workflows/*.yml", ".github/workflows/*.yaml", "*.yml", "*.yaml"):
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _VULN_SCAN_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.80)
            if not evidence:
                missing.append("No dependency vulnerability scanning configuration found")

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
