"""inclusion_scanner plugin — checks for multi-language support, human-factors hazards, and accessibility testing.

Targets controls ACC-05, ACC-06, ACC-07.
Reads files as text only — no code execution.
"""

from app.pipeline.models import EvidenceLocation, ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_I18N_CODE_PATTERNS = [
    "i18n",
    "l10n",
    "gettext",
    "useTranslation",
    "t(",
    "intl.",
    "Intl.",
    "locale",
    "language",
]

_I18N_FILENAMES = [
    "*.po",
    "*.pot",
    "*locale*",
    "*i18n*",
    "*l10n*",
    "translations*",
    "*messages*",
]

_I18N_KEYWORDS = [
    "internationalisation",
    "internationalization",
    "i18n",
    "localisation",
    "localization",
    "l10n",
    "multi-language",
    "language support",
    "translation",
]

_HUMAN_FACTORS_KEYWORDS = [
    "human factors",
    "cognitive load",
    "automation bias",
    "complacency",
    "over-reliance",
    "mental model",
    "human error",
    "usability",
    "UX hazard",
    "automation complacency",
    "trust calibration",
]

_ACCESSIBILITY_TEST_KEYWORDS = [
    "accessibility test",
    "accessibility testing",
    "axe",
    "lighthouse",
    "screen reader test",
    "NVDA",
    "JAWS",
    "VoiceOver",
    "accessibility audit",
    "a11y test",
    "WAVE tool",
]

_ACCESSIBILITY_TEST_CODE_PATTERNS = [
    "axe",
    "lighthouse",
    "jest-axe",
    "cypress-axe",
    "pa11y",
    "accessibility",
]


class InclusionScanner(BasePlugin):
    """Scans for multi-language support, human-factors hazard docs, and accessibility testing evidence."""

    plugin_id = "inclusion_scanner"

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

        if control_id == "ACC-05":
            for pattern in _I18N_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    if content and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.90)
            for pattern in ("*.ts", "*.tsx", "*.js", "*.jsx", "*.py"):
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    code_found = [p for p in _I18N_CODE_PATTERNS if p in content]
                    if code_found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.80)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _I18N_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.60)
            if not evidence:
                missing.append("No multi-language or localisation support documented")

        elif control_id == "ACC-06":
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _HUMAN_FACTORS_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.85)
            if not evidence:
                missing.append("No human-factors hazard documentation found")

        elif control_id == "ACC-07":
            for pattern in ("*.ts", "*.tsx", "*.js", "*.jsx"):
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    code_found = [
                        p for p in _ACCESSIBILITY_TEST_CODE_PATTERNS if p in content.lower()
                    ]
                    if code_found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.85)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _ACCESSIBILITY_TEST_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.70)
            if not evidence:
                missing.append("No accessibility testing evidence found")

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
