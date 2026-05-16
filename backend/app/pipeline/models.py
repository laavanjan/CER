"""Shared pipeline dataclasses used across S5–S10.

All pipeline stages communicate via typed dataclasses so that the type checker
can verify end-to-end correctness without relying on duck-typed dicts.
"""

from dataclasses import dataclass, field
from typing import Literal

# CER observation outcomes (§10, I-05).
# The CER NEVER produces Reviewer or Certifier statuses.
Outcome = Literal["evidence_found", "partial", "missing", "not_triggered", "not_evaluable"]

# CER severity values (§10.1)
Severity = Literal["critical", "major", "minor", "action_required", "info", "none"]


@dataclass
class EvidenceLocation:
    """A precise file + line reference produced by S5 plugins."""

    file: str        # Repo-relative file path
    line: int        # 1-based line number
    snippet: str     # Raw text of the matched line (stripped)
    reason: str = "" # Why this line is significant


@dataclass
class RawFinding:
    """Output of a single plugin run against a single control (produced by S5).

    Fields
    ------
    plugin_id:          Identifier of the plugin that produced this finding.
    control_id:         PRIMARY control this finding belongs to.
    evidence_found:     File paths / snippet strings that support a pass.
    missing:            Expected artefacts that were NOT found.
    confidence:         Float 0–1 representing certainty.
    evidence_locations: Line-level locations for pass/partial (T1 controls).
    issue_locations:    Line-level locations of active problems (T1 controls).
    overlay_relevance:  GEN/REL overlay IDs this PRIMARY finding informs (set by S6).
                        GEN/REL controls never receive direct status from CER.
    timed_out:          True if the plugin exceeded its 30-second timeout.
    """

    plugin_id: str
    control_id: str
    evidence_found: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence_locations: list[EvidenceLocation] = field(default_factory=list)
    issue_locations: list[EvidenceLocation] = field(default_factory=list)
    overlay_relevance: list[str] = field(default_factory=list)
    timed_out: bool = False


@dataclass
class SupplementEntry:
    """T3 Metadata Supplement entry produced by S4 for design-only controls."""

    control_id: str
    supplement_prompt: str
    artefact_type_expected: str          # E1 / E3 / E4 / E5 / E8 / E9
    declared_path: str | None = None     # Developer-provided path (null until submitted)
    existence_check_result: str = "pending"  # found | not_found | not_declared | pending
    status_after_supplement: str = "not_evaluable"  # partial | missing | not_evaluable


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
    uses_rel_ai: bool = False
    vulnerable_users: bool = False
    rights_affecting: bool = False
    regulated_sector: bool = False
    cross_border_transfer: bool = False
    jurisdiction: str | None = None
    user_facing: bool = True
    # Raw code-scan detection flags set by S3 — used by S8 for honesty check.
    gen_triggered: bool = False
    rel_triggered: bool = False


@dataclass
class ManifestEntry:
    """A single file in the repository manifest produced by S2."""

    path: str
    size_bytes: int
    sha256: str       # Per-file hex SHA-256
    masked: bool = False


@dataclass
class EvidenceResult:
    """Deterministic per-control outcome produced by S7 (I-05, I-07)."""

    control_id: str
    outcome: str        # evidence_found | partial | missing | not_triggered | not_evaluable
    cer_observability: str = "T1"   # T1 | T2 | T3
    assurance_tier: int = 1         # Registry tier (1|2|3) for assurance-level gating
    severity: str = "none"          # critical | major | minor | action_required | info | none
    raw_findings: list[RawFinding] = field(default_factory=list)
    evidence_paths: list[str] = field(default_factory=list)
    evidence_locations: list[EvidenceLocation] = field(default_factory=list)
    issue_locations: list[EvidenceLocation] = field(default_factory=list)
    overlay_relevance: list[str] = field(default_factory=list)
    recommended_next_artifact: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)


@dataclass
class EscalationHint:
    """Discrepancy flag produced by S8."""

    control_id: str
    hint: str
    severity: str = "INFO"  # INFO | WARNING | CRITICAL


@dataclass
class LLMAnnotation:
    """Structured LLM annotation for a single control (produced by S9)."""

    control_id: str
    developer_explanation: str    # max 150 words
    student_summary: str          # max 80 words
    what_is_present: str
    what_is_missing: str
    remediation_steps: list[dict] = field(default_factory=list)  # structured steps
    doc_classification: str = "NEEDS_IMPROVEMENT"  # ADEQUATE | NEEDS_IMPROVEMENT | ABSENT
    issue_detail: str = ""
