"""data_provenance_scanner plugin — checks for data provenance, data lineage, and labelling quality docs.

Targets controls DQ-01, DQ-02, DQ-03.
Reads files as text only — no code execution.
"""

from app.pipeline.models import EvidenceLocation, ManifestEntry, RawFinding
from app.pipeline.s5_plugins.base import BasePlugin

_DATA_FILENAMES = [
    "*data*",
    "*DATA*",
    "*dataset*",
    "*DATASET*",
    "*provenance*",
    "*PROVENANCE*",
    "*lineage*",
    "*LINEAGE*",
]

_PROVENANCE_KEYWORDS = [
    "data provenance",
    "data origin",
    "data source",
    "collection method",
    "data collection",
    "where the data came from",
    "source of data",
    "dataset origin",
    "collected from",
]

_LINEAGE_KEYWORDS = [
    "data lineage",
    "data flow",
    "data pipeline",
    "transformation",
    "preprocessing step",
    "data processing",
    "ETL",
    "feature engineering",
    "data transformation",
    "pipeline step",
]

_LABELLING_KEYWORDS = [
    "labelling",
    "labeling",
    "annotation",
    "ground truth",
    "inter-annotator",
    "annotator agreement",
    "labelling guidelines",
    "annotation guideline",
    "label quality",
    "Cohen's kappa",
    "Fleiss kappa",
]


class DataProvenanceScanner(BasePlugin):
    """Scans for data provenance, data lineage, and labelling quality documentation."""

    plugin_id = "data_provenance_scanner"

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

        if control_id == "DQ-01":
            keywords = _PROVENANCE_KEYWORDS
            missing_msg = "No data provenance documentation found"
        elif control_id == "DQ-02":
            keywords = _LINEAGE_KEYWORDS
            missing_msg = "No data lineage documentation found"
        else:  # DQ-03
            keywords = _LABELLING_KEYWORDS
            missing_msg = "No labelling quality documentation found"

        for pattern in _DATA_FILENAMES:
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
                confidence = max(confidence, 0.70)

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
                evidence_locations=ev_locs,
            )
        ]
