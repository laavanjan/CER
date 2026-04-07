"""Tests for the pipeline stages — no database or network required."""

import json
from pathlib import Path

import pytest

from app.pipeline import s1_intake, s4_filter, s7_evidence
from app.pipeline.models import (
    ManifestEntry,
    ProjectProfile,
    RawFinding,
)
from app.pipeline.s5_plugins.docs_scanner import DocsScanner
from app.pipeline.s5_plugins.governance_scanner import GovernanceScanner
from app.pipeline.s5_plugins.privacy_scanner import PrivacyScanner

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REGISTRY_SAMPLE = [
    {
        "id": "GOV-01",
        "pillar": "Governance",
        "tier": 1,
        "auto": True,
        "plugins": ["governance_scanner"],
        "pass_criteria": "An AI governance policy document exists.",
        "partial_criteria": "A governance policy exists but is incomplete.",
        "missing_criteria": "No governance policy document found.",
    },
    {
        "id": "DOC-01",
        "pillar": "Documentation",
        "tier": 1,
        "auto": True,
        "plugins": ["docs_scanner"],
        "pass_criteria": "A model card is present with all mandatory fields.",
        "partial_criteria": "A model card is present but missing fields.",
        "missing_criteria": "No model card found.",
    },
    {
        "id": "PRV-01",
        "pillar": "Privacy",
        "tier": 2,
        "auto": True,
        "plugins": ["privacy_scanner"],
        "pass_criteria": "A PIA document is present.",
        "partial_criteria": "A PIA exists but incomplete.",
        "missing_criteria": "No PIA found.",
    },
]


@pytest.fixture()
def registry_file(tmp_path: Path) -> str:
    """Write a minimal controls_v1.json and return its path."""
    registry_path = tmp_path / "controls_v1.json"
    registry_path.write_text(json.dumps(REGISTRY_SAMPLE), encoding="utf-8")
    return str(registry_path)


@pytest.fixture()
def base_profile() -> ProjectProfile:
    return ProjectProfile(
        project_id="proj-001",
        name="Test Project",
        github_url=None,
        zip_path=None,
        assurance_level="standard",
        uses_genai=False,
        registry_version="v1",
    )


# ---------------------------------------------------------------------------
# S1 — Intake
# ---------------------------------------------------------------------------


class TestS1Intake:
    def test_valid_github_url(self, registry_file: str, base_profile: ProjectProfile) -> None:
        base_profile.github_url = "https://github.com/example/repo"
        result = s1_intake.run(base_profile, registry_file)
        assert result is base_profile

    def test_missing_source_raises(self, registry_file: str, base_profile: ProjectProfile) -> None:
        with pytest.raises(FileNotFoundError):
            s1_intake.run(base_profile, registry_file)

    def test_wrong_registry_version_raises(
        self, registry_file: str, base_profile: ProjectProfile
    ) -> None:
        base_profile.github_url = "https://github.com/example/repo"
        base_profile.registry_version = "v99"
        with pytest.raises(s1_intake.RegistryVersionError):
            s1_intake.run(base_profile, registry_file)

    def test_missing_registry_file_raises(self, base_profile: ProjectProfile) -> None:
        base_profile.github_url = "https://github.com/example/repo"
        with pytest.raises(FileNotFoundError):
            s1_intake.run(base_profile, "/nonexistent/controls_v1.json")


# ---------------------------------------------------------------------------
# S4 — Filter
# ---------------------------------------------------------------------------


class TestS4Filter:
    def test_standard_assurance_includes_tier2(
        self, registry_file: str, base_profile: ProjectProfile
    ) -> None:
        active, t3 = s4_filter.run(base_profile, registry_file)
        control_ids = [c["id"] for c in active]
        # PRV-01 is tier 2 and should be included for standard assurance
        assert "PRV-01" in control_ids

    def test_basic_assurance_excludes_tier2(
        self, registry_file: str, base_profile: ProjectProfile
    ) -> None:
        base_profile.assurance_level = "basic"
        active, t3 = s4_filter.run(base_profile, registry_file)
        control_ids = [c["id"] for c in active]
        assert "PRV-01" not in control_ids

    def test_t3_queue_empty_for_sample_registry(
        self, registry_file: str, base_profile: ProjectProfile
    ) -> None:
        # Sample registry has no tier-3 controls
        _, t3 = s4_filter.run(base_profile, registry_file)
        assert t3 == []


# ---------------------------------------------------------------------------
# S7 — Evidence (deterministic scoring)
# ---------------------------------------------------------------------------


class TestS7Evidence:
    def test_pass_outcome(self) -> None:
        findings = [
            RawFinding(
                plugin_id="governance_scanner",
                control_id="GOV-01",
                evidence_found=["governance.md"],
                missing=[],
                confidence=0.9,
            )
        ]
        controls = [{"id": "GOV-01"}]
        results = s7_evidence.run(findings, controls)
        assert results[0].outcome == "PASS"

    def test_missing_outcome_no_evidence(self) -> None:
        findings = [
            RawFinding(
                plugin_id="governance_scanner",
                control_id="GOV-01",
                evidence_found=[],
                missing=["No governance doc"],
                confidence=0.0,
            )
        ]
        controls = [{"id": "GOV-01"}]
        results = s7_evidence.run(findings, controls)
        assert results[0].outcome == "MISSING"

    def test_partial_outcome_low_confidence(self) -> None:
        findings = [
            RawFinding(
                plugin_id="governance_scanner",
                control_id="GOV-01",
                evidence_found=["partial_doc.md"],
                missing=[],
                confidence=0.5,  # Below PASS threshold of 0.75
            )
        ]
        controls = [{"id": "GOV-01"}]
        results = s7_evidence.run(findings, controls)
        assert results[0].outcome == "PARTIAL"

    def test_no_findings_gives_missing(self) -> None:
        controls = [{"id": "GOV-01"}]
        results = s7_evidence.run([], controls)
        assert results[0].outcome == "MISSING"

    def test_deterministic_same_input(self) -> None:
        """S7 must produce identical output for identical input — no randomness."""
        findings = [
            RawFinding(
                plugin_id="governance_scanner",
                control_id="GOV-01",
                evidence_found=["gov.md"],
                missing=[],
                confidence=0.8,
            )
        ]
        controls = [{"id": "GOV-01"}]
        result1 = s7_evidence.run(findings, controls)
        result2 = s7_evidence.run(findings, controls)
        assert result1[0].outcome == result2[0].outcome


# ---------------------------------------------------------------------------
# Plugin tests
# ---------------------------------------------------------------------------


class TestGovernanceScanner:
    def test_finds_governance_doc(self, tmp_path: Path) -> None:
        # Create a fake repo with a governance file
        gov_file = tmp_path / "governance.md"
        gov_file.write_text("# AI Governance Policy\nThis policy establishes governance for AI.")
        manifest = [ManifestEntry(path="governance.md", size_bytes=100, sha256="abc")]
        plugin = GovernanceScanner()
        findings = plugin.run("GOV-01", manifest, str(tmp_path))
        assert findings[0].evidence_found == ["governance.md"]
        assert findings[0].confidence > 0

    def test_no_governance_doc(self, tmp_path: Path) -> None:
        manifest: list[ManifestEntry] = []
        plugin = GovernanceScanner()
        findings = plugin.run("GOV-01", manifest, str(tmp_path))
        assert findings[0].evidence_found == []
        assert findings[0].confidence == 0.0


class TestDocsScanner:
    def test_finds_model_card(self, tmp_path: Path) -> None:
        card = tmp_path / "model_card.md"
        card.write_text(
            "# Model Card\n## Purpose\nThis model does X.\n"
            "## Limitations\nNone known.\n## Intended Use\nResearch."
        )
        manifest = [ManifestEntry(path="model_card.md", size_bytes=200, sha256="def")]
        plugin = DocsScanner()
        findings = plugin.run("DOC-01", manifest, str(tmp_path))
        assert findings[0].evidence_found == ["model_card.md"]
        assert findings[0].confidence >= 0.5


class TestPrivacyScanner:
    def test_finds_pia_with_processing_activities(self, tmp_path: Path) -> None:
        pia = tmp_path / "privacy_impact.md"
        pia.write_text(
            "# Privacy Impact Assessment\n"
            "This document covers GDPR compliance and data processing activities "
            "including personal data handling."
        )
        manifest = [ManifestEntry(path="privacy_impact.md", size_bytes=300, sha256="ghi")]
        plugin = PrivacyScanner()
        findings = plugin.run("PRV-01", manifest, str(tmp_path))
        assert findings[0].evidence_found == ["privacy_impact.md"]
        assert findings[0].confidence >= 0.8
