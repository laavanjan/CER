"""Shared pipeline dataclasses used across S5–S10.

All pipeline stages communicate via typed dataclasses so that the type checker
can verify end-to-end correctness without relying on duck-typed dicts.
"""

from dataclasses import dataclass, field


@dataclass
class RawFinding:
    """Output of a single plugin run against a single control (produced by S5).

    Fields
    ------
    plugin_id:     Identifier of the plugin that produced this finding.
    control_id:    Control from controls_v1.json that this finding relates to.
    evidence_found: List of file paths / snippet strings that support a PASS.
    missing:       List of expected artefacts that were NOT found.
    confidence:    Float 0–1 representing how certain the plugin is.
    """

    plugin_id: str
    control_id: str
    evidence_found: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class ProjectProfile:
    """Intake-time project description flowing from S1 through the pipeline."""

    project_id: str
    name: str
    github_url: str | None
    zip_path: str | None
    assurance_level: str
    uses_genai: bool
    registry_version: str


@dataclass
class ManifestEntry:
    """A single file in the repository manifest produced by S2."""

    path: str          # Repo-relative file path
    size_bytes: int
    sha256: str        # Hex digest of file content
    masked: bool = False  # True if secrets were redacted


@dataclass
class EvidenceResult:
    """Deterministic per-control outcome produced by S7."""

    control_id: str
    outcome: str       # PASS | PARTIAL | MISSING
    raw_findings: list[RawFinding] = field(default_factory=list)
    evidence_paths: list[str] = field(default_factory=list)


@dataclass
class EscalationHint:
    """Discrepancy flag produced by S8 when declared profile differs from detected signals."""

    control_id: str
    hint: str
    severity: str = "INFO"  # INFO | WARNING | CRITICAL


@dataclass
class LLMAnnotation:
    """LLM-generated annotation for a single control (produced by S9)."""

    control_id: str
    explanation: str
    remediation: str
    doc_classification: str
