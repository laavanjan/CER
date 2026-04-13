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
from app.pipeline.s5_plugins.access_control_scanner import AccessControlScanner
from app.pipeline.s5_plugins.accountability_scanner import AccountabilityScanner
from app.pipeline.s5_plugins.audit_governance_scanner import AuditGovernanceScanner
from app.pipeline.s5_plugins.audit_log_scanner import AuditLogScanner
from app.pipeline.s5_plugins.audit_trail_scanner import AuditTrailScanner
from app.pipeline.s5_plugins.bias_scanner import BiasScanner
from app.pipeline.s5_plugins.consent_scanner import ConsentScanner
from app.pipeline.s5_plugins.data_provenance_scanner import DataProvenanceScanner
from app.pipeline.s5_plugins.dependency_doc_scanner import DependencyDocScanner
from app.pipeline.s5_plugins.dependency_scanner import DependencyScanner
from app.pipeline.s5_plugins.disclosure_scanner import DisclosureScanner
from app.pipeline.s5_plugins.discrimination_scanner import DiscriminationScanner
from app.pipeline.s5_plugins.docs_scanner import DocsScanner
from app.pipeline.s5_plugins.drift_scanner import DriftScanner
from app.pipeline.s5_plugins.environmental_scanner import EnvironmentalScanner
from app.pipeline.s5_plugins.escalation_scanner import EscalationScanner
from app.pipeline.s5_plugins.explainability_scanner import ExplainabilityScanner
from app.pipeline.s5_plugins.fairness_metrics_scanner import FairnessMetricsScanner
from app.pipeline.s5_plugins.governance_scanner import GovernanceScanner
from app.pipeline.s5_plugins.human_override_scanner import HumanOverrideScanner
from app.pipeline.s5_plugins.inclusion_scanner import InclusionScanner
from app.pipeline.s5_plugins.monitoring_scanner import MonitoringScanner
from app.pipeline.s5_plugins.pii_code_scanner import PiiCodeScanner
from app.pipeline.s5_plugins.privacy_scanner import PrivacyScanner
from app.pipeline.s5_plugins.retention_scanner import RetentionScanner
from app.pipeline.s5_plugins.risk_assessment_scanner import RiskAssessmentScanner
from app.pipeline.s5_plugins.safe_failure_scanner import SafeFailureScanner
from app.pipeline.s5_plugins.safety_testing_scanner import SafetyTestingScanner
from app.pipeline.s5_plugins.threat_model_scanner import ThreatModelScanner
from app.pipeline.s5_plugins.version_manifest_scanner import VersionManifestScanner
from app.pipeline.s5_plugins.wcag_scanner import WcagScanner

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
        self, base_profile: ProjectProfile
    ) -> None:
        active, t3 = s4_filter.run(base_profile, REGISTRY_SAMPLE)
        control_ids = [c["id"] for c in active]
        # PRV-01 is tier 2 and should be included for standard assurance
        assert "PRV-01" in control_ids

    def test_basic_assurance_excludes_tier2(
        self, base_profile: ProjectProfile
    ) -> None:
        base_profile.assurance_level = "basic"
        active, t3 = s4_filter.run(base_profile, REGISTRY_SAMPLE)
        control_ids = [c["id"] for c in active]
        assert "PRV-01" not in control_ids

    def test_t3_queue_empty_for_sample_registry(
        self, base_profile: ProjectProfile
    ) -> None:
        # Sample registry has no tier-3 controls
        _, t3 = s4_filter.run(base_profile, REGISTRY_SAMPLE)
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


# ---------------------------------------------------------------------------
# New plugin tests — one positive + one negative per plugin
# ---------------------------------------------------------------------------


class TestRiskAssessmentScanner:
    def test_finds_risk_assessment(self, tmp_path: Path) -> None:
        f = tmp_path / "risk_assessment.md"
        f.write_text("# AI Risk Assessment\nKey risks: data poisoning. Mitigation: input validation.")
        manifest = [ManifestEntry(path="risk_assessment.md", size_bytes=100, sha256="r1")]
        findings = RiskAssessmentScanner().run("GOV-03", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = RiskAssessmentScanner().run("GOV-03", [], str(tmp_path))
        assert findings[0].evidence_found == []
        assert findings[0].confidence == 0.0


class TestAccountabilityScanner:
    def test_finds_incident_response(self, tmp_path: Path) -> None:
        f = tmp_path / "incident_response.md"
        f.write_text("# Incident Response Plan\nAI failure incident management and root cause analysis.")
        manifest = [ManifestEntry(path="incident_response.md", size_bytes=100, sha256="a1")]
        findings = AccountabilityScanner().run("GOV-06", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = AccountabilityScanner().run("GOV-06", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestAuditGovernanceScanner:
    def test_finds_audit_schedule(self, tmp_path: Path) -> None:
        f = tmp_path / "audit_plan.md"
        f.write_text("# Internal Audit Schedule\nQuarterly review of AI system compliance.")
        manifest = [ManifestEntry(path="audit_plan.md", size_bytes=100, sha256="ag1")]
        findings = AuditGovernanceScanner().run("GOV-08", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = AuditGovernanceScanner().run("GOV-08", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestExplainabilityScanner:
    def test_finds_explainability_doc(self, tmp_path: Path) -> None:
        f = tmp_path / "explainability.md"
        f.write_text("# Explainability Approach\nWe use SHAP for feature attribution and model explanation.")
        manifest = [ManifestEntry(path="explainability.md", size_bytes=100, sha256="e1")]
        findings = ExplainabilityScanner().run("TRN-01", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_finds_shap_in_code(self, tmp_path: Path) -> None:
        f = tmp_path / "explain.py"
        f.write_text("import shap\nexplainer = shap.TreeExplainer(model)\nshap_values = explainer.shap_values(X)")
        manifest = [ManifestEntry(path="explain.py", size_bytes=100, sha256="e2")]
        findings = ExplainabilityScanner().run("TRN-02", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence >= 0.9

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = ExplainabilityScanner().run("TRN-01", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestDisclosureScanner:
    def test_finds_decision_logging(self, tmp_path: Path) -> None:
        f = tmp_path / "logger.py"
        f.write_text("def log_decision(input, output):\n    audit_log.write(input, output)\n")
        manifest = [ManifestEntry(path="logger.py", size_bytes=100, sha256="d1")]
        findings = DisclosureScanner().run("TRN-05", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = DisclosureScanner().run("TRN-03", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestAuditTrailScanner:
    def test_finds_version_transparency(self, tmp_path: Path) -> None:
        f = tmp_path / "config.py"
        f.write_text("MODEL_VERSION = '1.2.3'\nmodel_version = MODEL_VERSION\n")
        manifest = [ManifestEntry(path="config.py", size_bytes=100, sha256="at1")]
        findings = AuditTrailScanner().run("TRN-08", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = AuditTrailScanner().run("TRN-06", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestBiasScanner:
    def test_finds_bias_testing(self, tmp_path: Path) -> None:
        f = tmp_path / "bias_tests.md"
        f.write_text("# Bias Testing\nBias evaluation across protected characteristics including gender.")
        manifest = [ManifestEntry(path="bias_tests.md", size_bytes=100, sha256="b1")]
        findings = BiasScanner().run("FAR-01", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = BiasScanner().run("FAR-01", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestFairnessMetricsScanner:
    def test_finds_demographic_parity(self, tmp_path: Path) -> None:
        f = tmp_path / "fairness.py"
        f.write_text("# Calculate demographic parity\ndemo_parity = group_a_rate / group_b_rate\n")
        manifest = [ManifestEntry(path="fairness.py", size_bytes=100, sha256="fm1")]
        findings = FairnessMetricsScanner().run("FAR-03", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = FairnessMetricsScanner().run("FAR-03", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestDiscriminationScanner:
    def test_finds_anti_discrimination_policy(self, tmp_path: Path) -> None:
        f = tmp_path / "policy.md"
        f.write_text("# Anti-Discrimination Policy\nAI outputs must not discriminate against protected classes.")
        manifest = [ManifestEntry(path="policy.md", size_bytes=100, sha256="ds1")]
        findings = DiscriminationScanner().run("FAR-06", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = DiscriminationScanner().run("FAR-06", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestConsentScanner:
    def test_finds_consent_mechanism(self, tmp_path: Path) -> None:
        f = tmp_path / "consent.md"
        f.write_text("# Consent Mechanism\nUsers must provide explicit consent before data collection.")
        manifest = [ManifestEntry(path="consent.md", size_bytes=100, sha256="cs1")]
        findings = ConsentScanner().run("PRV-02", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = ConsentScanner().run("PRV-02", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestRetentionScanner:
    def test_finds_retention_policy(self, tmp_path: Path) -> None:
        f = tmp_path / "privacy.md"
        f.write_text("# Data Retention Policy\nData retention period is 90 days. Deletion schedule is automated.")
        manifest = [ManifestEntry(path="privacy.md", size_bytes=100, sha256="rs1")]
        findings = RetentionScanner().run("PRV-04", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = RetentionScanner().run("PRV-04", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestPiiCodeScanner:
    def test_finds_pii_masking_in_code(self, tmp_path: Path) -> None:
        f = tmp_path / "utils.py"
        f.write_text("import os\ndef process(data):\n    return mask_pii(data)\n")
        manifest = [ManifestEntry(path="utils.py", size_bytes=100, sha256="pcs1")]
        findings = PiiCodeScanner().run("PRV-06", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = PiiCodeScanner().run("PRV-06", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestThreatModelScanner:
    def test_finds_threat_model(self, tmp_path: Path) -> None:
        f = tmp_path / "threat_model.md"
        f.write_text("# Threat Model\nAttack vectors include data poisoning and prompt injection. Mitigations applied.")
        manifest = [ManifestEntry(path="threat_model.md", size_bytes=100, sha256="tm1")]
        findings = ThreatModelScanner().run("SEC-01", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = ThreatModelScanner().run("SEC-01", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestDependencyScanner:
    def test_finds_lockfile(self, tmp_path: Path) -> None:
        f = tmp_path / "requirements.txt"
        f.write_text("fastapi==0.104.0\npydantic==2.5.0\n")
        manifest = [ManifestEntry(path="requirements.txt", size_bytes=100, sha256="dep1")]
        findings = DependencyScanner().run("SEC-03", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_lockfile_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = DependencyScanner().run("SEC-03", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestAccessControlScanner:
    def test_finds_input_validation(self, tmp_path: Path) -> None:
        f = tmp_path / "api.py"
        f.write_text("from pydantic import BaseModel\nclass InputSchema(BaseModel):\n    query: str\n")
        manifest = [ManifestEntry(path="api.py", size_bytes=100, sha256="ac1")]
        findings = AccessControlScanner().run("SEC-07", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = AccessControlScanner().run("SEC-05", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestHumanOverrideScanner:
    def test_finds_override_doc(self, tmp_path: Path) -> None:
        f = tmp_path / "ops.md"
        f.write_text("# Operations Guide\nHuman override mechanism allows operators to disable AI decisions.")
        manifest = [ManifestEntry(path="ops.md", size_bytes=100, sha256="ho1")]
        findings = HumanOverrideScanner().run("OVR-01", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = HumanOverrideScanner().run("OVR-01", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestEscalationScanner:
    def test_finds_hitl_in_code(self, tmp_path: Path) -> None:
        f = tmp_path / "pipeline.py"
        f.write_text("def review_step(output):\n    if requires_human_review(output):\n        return human_approval(output)\n")
        manifest = [ManifestEntry(path="pipeline.py", size_bytes=100, sha256="esc1")]
        findings = EscalationScanner().run("OVR-04", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = EscalationScanner().run("OVR-03", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestMonitoringScanner:
    def test_finds_review_cadence(self, tmp_path: Path) -> None:
        f = tmp_path / "governance.md"
        f.write_text("## Review Cadence\nQuarterly review of AI system performance and behaviour is mandatory.")
        manifest = [ManifestEntry(path="governance.md", size_bytes=100, sha256="mon1")]
        findings = MonitoringScanner().run("OVR-07", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = MonitoringScanner().run("OVR-07", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestSafeFailureScanner:
    def test_finds_fallback_in_code(self, tmp_path: Path) -> None:
        f = tmp_path / "handler.py"
        f.write_text("def on_error(err):\n    return fallback_response()\n")
        manifest = [ManifestEntry(path="handler.py", size_bytes=100, sha256="sf1")]
        findings = SafeFailureScanner().run("SAF-02", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = SafeFailureScanner().run("SAF-01", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestSafetyTestingScanner:
    def test_finds_harm_prevention(self, tmp_path: Path) -> None:
        f = tmp_path / "filter.py"
        f.write_text("def content_filter(text):\n    return guardrail.check(text)\n")
        manifest = [ManifestEntry(path="filter.py", size_bytes=100, sha256="st1")]
        findings = SafetyTestingScanner().run("SAF-05", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = SafetyTestingScanner().run("SAF-04", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestEnvironmentalScanner:
    def test_finds_carbon_tracking(self, tmp_path: Path) -> None:
        f = tmp_path / "training.py"
        f.write_text("from codecarbon import EmissionsTracker\ntracker = EmissionsTracker()\n")
        manifest = [ManifestEntry(path="training.py", size_bytes=100, sha256="env1")]
        findings = EnvironmentalScanner().run("ENV-02", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = EnvironmentalScanner().run("ENV-01", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestVersionManifestScanner:
    def test_finds_changelog(self, tmp_path: Path) -> None:
        f = tmp_path / "CHANGELOG.md"
        f.write_text("# Changelog\n## v1.2.0\n### Added\n- New feature X\n### Fixed\n- Bug Y\n")
        manifest = [ManifestEntry(path="CHANGELOG.md", size_bytes=100, sha256="vm1")]
        findings = VersionManifestScanner().run("DOC-04", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = VersionManifestScanner().run("DOC-03", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestAuditLogScanner:
    def test_finds_worm_in_code(self, tmp_path: Path) -> None:
        f = tmp_path / "audit.py"
        f.write_text(
            "class AuditStore:\n"
            "    def write(self, entry):\n"
            "        # append_only - WORM compliant\n"
            "        self.store.append(entry)\n"
        )
        manifest = [ManifestEntry(path="audit.py", size_bytes=100, sha256="al1")]
        findings = AuditLogScanner().run("DOC-06", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = AuditLogScanner().run("DOC-05", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestDependencyDocScanner:
    def test_finds_requirements_txt(self, tmp_path: Path) -> None:
        f = tmp_path / "requirements.txt"
        f.write_text("# AI framework dependencies\ntorch==2.1.0  # MIT license\ntransformers==4.35.0\n")
        manifest = [ManifestEntry(path="requirements.txt", size_bytes=100, sha256="dd1")]
        findings = DependencyDocScanner().run("DOC-07", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = DependencyDocScanner().run("DOC-08", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestWcagScanner:
    def test_finds_wcag_doc(self, tmp_path: Path) -> None:
        f = tmp_path / "accessibility.md"
        f.write_text("# Accessibility\nAll interfaces comply with WCAG 2.1 AA standards.")
        manifest = [ManifestEntry(path="accessibility.md", size_bytes=100, sha256="wc1")]
        findings = WcagScanner().run("ACC-01", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_finds_alt_text_in_tsx(self, tmp_path: Path) -> None:
        f = tmp_path / "Image.tsx"
        f.write_text('<img src={src} alt="AI-generated chart showing trend" />\n')
        manifest = [ManifestEntry(path="Image.tsx", size_bytes=100, sha256="wc2")]
        findings = WcagScanner().run("ACC-02", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = WcagScanner().run("ACC-01", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestInclusionScanner:
    def test_finds_i18n_locale_file(self, tmp_path: Path) -> None:
        locale_dir = tmp_path / "locales"
        locale_dir.mkdir()
        f = locale_dir / "en.po"
        f.write_text('msgid "Hello"\nmsgstr "Hello"\n')
        manifest = [ManifestEntry(path="locales/en.po", size_bytes=50, sha256="inc1")]
        findings = InclusionScanner().run("ACC-05", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_finds_human_factors_doc(self, tmp_path: Path) -> None:
        f = tmp_path / "ux.md"
        f.write_text("# UX Design\nWe mitigate cognitive load and automation bias through clear UI design.")
        manifest = [ManifestEntry(path="ux.md", size_bytes=100, sha256="inc2")]
        findings = InclusionScanner().run("ACC-06", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = InclusionScanner().run("ACC-05", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestDataProvenanceScanner:
    def test_finds_provenance_doc(self, tmp_path: Path) -> None:
        f = tmp_path / "data_card.md"
        f.write_text("# Data Card\nData provenance: collected from public web crawl. Data source: CommonCrawl.")
        manifest = [ManifestEntry(path="data_card.md", size_bytes=100, sha256="dp1")]
        findings = DataProvenanceScanner().run("DQ-01", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = DataProvenanceScanner().run("DQ-01", [], str(tmp_path))
        assert findings[0].evidence_found == []


class TestDriftScanner:
    def test_finds_drift_detection_in_code(self, tmp_path: Path) -> None:
        f = tmp_path / "monitor.py"
        f.write_text("from evidently import EvidentlyAI\ndetector = EvidentlyAI()\n")
        manifest = [ManifestEntry(path="monitor.py", size_bytes=100, sha256="dr1")]
        findings = DriftScanner().run("DQ-04", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_finds_data_validation_in_code(self, tmp_path: Path) -> None:
        f = tmp_path / "validate.py"
        f.write_text("import pandera as pa\nschema = pa.DataFrameSchema({'col': pa.Column(int)})\n")
        manifest = [ManifestEntry(path="validate.py", size_bytes=100, sha256="dr2")]
        findings = DriftScanner().run("DQ-05", manifest, str(tmp_path))
        assert findings[0].evidence_found
        assert findings[0].confidence > 0

    def test_missing_returns_no_evidence(self, tmp_path: Path) -> None:
        findings = DriftScanner().run("DQ-04", [], str(tmp_path))
        assert findings[0].evidence_found == []
