"""wcag_scanner plugin — checks for WCAG compliance, alt text, keyboard navigation, and colour contrast docs.

Targets controls ACC-01, ACC-02, ACC-03, ACC-04.
Reads files as text only — no code execution.
"""

from app.pipeline.models import EvidenceLocation, ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_ACCESSIBILITY_FILENAMES = [
    "*accessib*",
    "*ACCESSIB*",
    "*a11y*",
    "*A11Y*",
    "*wcag*",
    "*WCAG*",
]

_WCAG_KEYWORDS = [
    "WCAG",
    "WCAG 2.1",
    "WCAG 2.2",
    "accessibility standard",
    "AA compliance",
    "accessibility compliance",
    "accessibility guidelines",
    "Web Content Accessibility",
]

_ALT_TEXT_CODE_PATTERNS = [
    "alt=",
    'alt="',
    "alt='",
    "aria-label",
    "aria_label",
    "alt_text",
    "altText",
]

_ALT_TEXT_KEYWORDS = [
    "alt text",
    "alternative text",
    "image description",
    "aria-label",
    "screen reader",
    "non-text content",
]

_KEYBOARD_NAV_CODE_PATTERNS = [
    "onKeyDown",
    "onKeyUp",
    "onKeyPress",
    "tabIndex",
    "tabindex",
    "KeyboardEvent",
    "focus(",
    "focusable",
]

_KEYBOARD_NAV_KEYWORDS = [
    "keyboard navigation",
    "keyboard accessible",
    "keyboard support",
    "focus management",
    "tab order",
    "keyboard shortcut",
    "keyboard interaction",
]

_CONTRAST_KEYWORDS = [
    "colour contrast",
    "color contrast",
    "contrast ratio",
    "WCAG contrast",
    "4.5:1",
    "3:1",
    "contrast checker",
    "contrast compliance",
]


class WcagScanner(BasePlugin):
    """Scans for WCAG compliance, alt text, keyboard navigation, and colour contrast."""

    plugin_id = "wcag_scanner"

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

        if control_id == "ACC-01":
            for pattern in _ACCESSIBILITY_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _WCAG_KEYWORDS if k in content]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.90)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _WCAG_KEYWORDS if k in content]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.70)
            if not evidence:
                missing.append("No WCAG 2.1 AA compliance documentation found")

        elif control_id == "ACC-02":
            for pattern in ("*.tsx", "*.jsx", "*.html", "*.ts", "*.js"):
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    code_found = [p for p in _ALT_TEXT_CODE_PATTERNS if p in content]
                    if code_found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.85)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _ALT_TEXT_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.60)
            if not evidence:
                missing.append("No alt text implementation found for AI-generated content")

        elif control_id == "ACC-03":
            for pattern in ("*.tsx", "*.jsx", "*.ts", "*.js"):
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    code_found = [p for p in _KEYBOARD_NAV_CODE_PATTERNS if p in content]
                    if code_found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.80)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _KEYBOARD_NAV_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.60)
            if not evidence:
                missing.append("No keyboard navigation implementation found")

        elif control_id == "ACC-04":
            for pattern in _ACCESSIBILITY_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _CONTRAST_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.85)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _CONTRAST_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.65)
            if not evidence:
                missing.append("No colour contrast compliance documentation found")

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
