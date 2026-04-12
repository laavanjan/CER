"""drift_scanner plugin — checks for data drift detection, data validation, and data quality metrics.

Targets controls DQ-04, DQ-05, DQ-06.
Reads files as text only — no code execution.
"""

from app.pipeline.models import ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_DRIFT_FILENAMES = [
    "*drift*",
    "*DRIFT*",
    "*monitor*",
    "*MONITOR*",
    "*validation*",
    "*VALIDATION*",
]

_DRIFT_KEYWORDS = [
    "data drift",
    "concept drift",
    "drift detection",
    "distribution shift",
    "covariate shift",
    "feature drift",
    "population drift",
    "drift monitoring",
]

_DRIFT_CODE_PATTERNS = [
    "drift",
    "EvidentlyAI",
    "evidently",
    "alibi-detect",
    "alibi",
    "deepchecks",
    "detect_drift",
    "DriftDetector",
    "KSDrift",
    "MMDDrift",
]

_VALIDATION_KEYWORDS = [
    "schema validation",
    "data validation",
    "range check",
    "completeness check",
    "data quality check",
    "null check",
    "outlier detection",
    "data integrity",
    "data contract",
]

_VALIDATION_CODE_PATTERNS = [
    "pandera",
    "great_expectations",
    "cerberus",
    "pydantic",
    "jsonschema",
    "validate_schema",
    "check_schema",
    "DataContract",
]

_DQ_METRICS_KEYWORDS = [
    "data quality metric",
    "completeness",
    "accuracy metric",
    "consistency metric",
    "data quality report",
    "data quality score",
    "missing values",
    "duplicate records",
    "data freshness",
]


class DriftScanner(BasePlugin):
    """Scans for data drift detection, data validation, and data quality metrics."""

    plugin_id = "drift_scanner"

    def run(
        self,
        control_id: str,
        manifest: list[ManifestEntry],
        repo_root: str,
    ) -> list[RawFinding]:
        evidence: list[str] = []
        missing: list[str] = []
        confidence = 0.0

        if control_id == "DQ-04":
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                code_found = [p for p in _DRIFT_CODE_PATTERNS if p.lower() in content.lower()]
                kw_found = [k for k in _DRIFT_KEYWORDS if k.lower() in content.lower()]
                if code_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.90)
                elif kw_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.70)
            for pattern in _DRIFT_FILENAMES:
                for entry in self.filter_manifest(manifest, pattern):
                    content = self.read_text(repo_root, entry.path) or ""
                    found = [k for k in _DRIFT_KEYWORDS if k.lower() in content.lower()]
                    if found and entry.path not in evidence:
                        evidence.append(entry.path)
                        confidence = max(confidence, 0.80)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _DRIFT_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.60)
            if not evidence:
                missing.append("No data drift detection found")

        elif control_id == "DQ-05":
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                code_found = [p for p in _VALIDATION_CODE_PATTERNS if p in content]
                kw_found = [k for k in _VALIDATION_KEYWORDS if k.lower() in content.lower()]
                if code_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.90)
                elif kw_found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.70)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _VALIDATION_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.60)
            if not evidence:
                missing.append("No data validation checks found")

        elif control_id == "DQ-06":
            for entry in self.filter_manifest(manifest, "*.py"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _DQ_METRICS_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.80)
            for entry in self.filter_manifest(manifest, "*.md"):
                content = self.read_text(repo_root, entry.path) or ""
                found = [k for k in _DQ_METRICS_KEYWORDS if k.lower() in content.lower()]
                if found and entry.path not in evidence:
                    evidence.append(entry.path)
                    confidence = max(confidence, 0.70)
            if not evidence:
                missing.append("No data quality metrics found")

        return [
            RawFinding(
                plugin_id=self.plugin_id,
                control_id=control_id,
                evidence_found=evidence,
                missing=missing,
                confidence=confidence,
            )
        ]
