# ethiksa-cer

> **AIGAP · Code Ethics Reviewer (CER)** — Automated pipeline that scans AI system repositories against 84 ethical controls across 11 pillars, producing structured findings, remediation guidance, and handoff packages for human reviewers and certifiers.

---

## What is this?

The **Code Ethics Reviewer (CER)** is Tool 02 in the AIGAP (AI Governance Assurance Platform) lifecycle built by **Ethiksa (Pvt) Ltd**. It sits between dataset ethics analysis and human design review — giving developers a detailed pre-assurance scan of their AI codebase before the formal certification process begins.

It does **not** certify. It **never** says "compliant", "passed", or "failed". It observes, maps evidence, and tells you exactly what is present, partial, or missing — so you can fix it before a human reviewer sees it.

```
DEA (Tool 01) → CER (Tool 02) ← you are here → ADR (Tool 03) → AC (Tool 04)
```

---

## How it works

The CER runs an **11-step deterministic pipeline**. Only one step (S9) uses an LLM — everything else is rule-based and reproducible.

| Step | Name | What happens |
|------|------|-------------|
| S1 | Intake | GitHub URL / ZIP ingested. Registry version verified. Profile validated. Hard stop on mismatch. |
| S2 | Manifest | Repository downloaded via GitHub API (zip). Full file manifest built. Secrets masked before storage. `commit_sha` and `workspace_hash` captured for audit seal. |
| S3 | AI Detect | Import patterns scanned. `gen_triggered` and `rel_triggered` flags set on the project profile. |
| S4 | Filter | 84 controls filtered by project profile and assurance level. T1/T2 → plugin queue. T3 → Metadata Supplement queue (never plugin-evaluated). |
| S5 | Runner | 32 scanner plugins run in parallel with no time limit. Each produces a `RawFinding` JSON. Never executes repository code. |
| S6 | Tag | GEN and REL overlay findings tagged via a hardcoded reverse anchor map. Overlays derive their status from the primary controls they anchor to — they never receive a direct outcome. |
| S7 | Evidence | `RawFindings` → `pass / partial / missing / not_triggered / not_evaluable` per control. 100% deterministic. No AI. T3 controls always emit `not_evaluable`. |
| S8 | Honesty | Declared profile vs detected signals. Conflicts → `escalation_hints[]`. |
| S9 | LLM | Claude API (temp=0, with Ollama/Gemini fallback). Writes `developer_explanation`, `student_summary`, `what_is_present`, `what_is_missing`, `remediation_steps`, `doc_classification` for every evaluable result. |
| S10 | Assemble | 10 output packages (P1–P10) assembled for different audiences. Zero new decisions. |
| S11 | Audit | Every stage decision, input, and output written to append-only audit log. |

---

## Observability tiers (CER-specific)

Controls are classified into three tiers that determine how they are evaluated:

| Tier | Name | Count | How evaluated |
|------|------|-------|---------------|
| **T1** | Code-observable | 22 | Plugin suite reads files, detects patterns — produces `pass/partial/missing` |
| **T2** | Document-observable | 48 | Plugin suite reads docs/configs — produces `pass/partial/missing` |
| **T3** | Design supplement | 14 | Cannot be assessed from code. Developer must declare artefact path via the Supplement form. Status: `not_evaluable` until submitted, then `partial` (declared) or `missing` (blank). |

T3 controls have a `supplement_prompt` and `artefact_type_expected` field in the registry. They are never sent to the S5 plugin runner.

---

## The 84 controls across 11 pillars

| Pillar | Prefix | Controls |
|--------|--------|----------|
| Governance & Accountability | GOV | GOV-01 → GOV-10 (10) |
| Data Governance & Privacy | PRIV | PRIV-01 → PRIV-09 (9) |
| Transparency & Explainability | TRAN | TRAN-01 → TRAN-08 (8) |
| Safety, Robustness & Reliability | SAFE | SAFE-01 → SAFE-06 (6) |
| Fairness & Non-Discrimination | FAIR | FAIR-01 → FAIR-07 (7) |
| Security, Misuse Prevention & Resilience | SEC | SEC-01 → SEC-07 (7) |
| Human Oversight & Recourse | HUMO | HUMO-01 → HUMO-07 (7) |
| Accessibility, Inclusion & Human Factors | ACC | ACC-01 → ACC-08 (8) |
| Documentation, Traceability & Auditability | DOC | DOC-01 → DOC-08 (8) |
| Risk Management & Impact Assessment | RISK | RISK-01 → RISK-06 (6) |
| Societal & Environmental Well-being | SOC | SOC-01 → SOC-08 (8) |

**Overlays** (conditionally activated, derive status from primary control anchors):

| Overlay | Activation | Anchors to |
|---------|-----------|-----------|
| GEN-01 → GEN-04 | `uses_genai = true` | SAFE-01, SAFE-04, TRAN-01, TRAN-06, TRAN-02, SAFE-06, TRAN-04, SAFE-02 |
| REL-01 → REL-03 | `uses_rel_ai = true` | SEC-01, SEC-03, PRIV-06, DOC-01, SEC-06 |

---

## Control outcomes

| Status | Meaning |
|--------|---------|
| `pass` | All required evidence found and verified |
| `partial` | Some evidence present; one or more components missing |
| `missing` | No evidence found for this control |
| `not_triggered` | Control does not apply to this project type (filtered at S4) |
| `not_evaluable` | T3 supplement not yet submitted by developer |

---

## Assurance levels

The project profile declares an assurance level which gates which controls activate:

| Level | Controls activated |
|-------|--------------------|
| `ug` (Undergraduate) | Tier 1 controls only |
| `pg` (Postgraduate) | Tier 1–2 controls |
| `capstone` | All tiers |
| `industrial` | All tiers (highest scrutiny) |

Override rules (profile flags can only raise the level, never lower it):
- `vulnerable_users` or `rights_affecting` → minimum Capstone
- `regulated_sector` → minimum Industrial

---

## Output packages (P1–P10)

| Package | Audience | Contents |
|---------|----------|----------|
| P1 | Executive | Summary with per-tier coverage stats (T1/T2/T3 reported separately — never aggregated) |
| P2 | Developer | Full findings with evidence paths and gaps per control |
| P3 | Developer | Remediation steps only (structured JSON) |
| P4 | Reviewer | Escalation hints from S8 honesty check |
| P5 | Auditor | Audit reference — workspace_hash, commit_sha, registry version |
| P6 | Machine | All 84 control statuses as structured JSON |
| P7 | Reviewer | Full handoff package for the human AI Design Reviewer |
| P8 | Certifier | Pre-registration package for AIGAP certification |
| P9 | CI/CD | SARIF 2.1.0 export for GitHub code scanning integration |
| P10 | Developer | Metadata Supplement package — T3 prompts and declared artefact paths |

Only P7 and P8 are persisted to the database as `handoff_exports`. All are accessible via API.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14 (App Router), Tailwind CSS, TanStack React Query v5 |
| **Backend** | FastAPI (Python 3.11), Celery + Redis (async task queue) |
| **Scanners** | 32 Python plugin modules, parallel execution via `ThreadPoolExecutor` |
| **LLM** | Anthropic Claude API (temp=0), Ollama fallback, Gemini fallback |
| **Database** | PostgreSQL via Neon (cloud-hosted), SQLAlchemy ORM, Alembic migrations |
| **Infra** | Single Docker container (HuggingFace Spaces), supervisord (uvicorn + celery worker), entrypoint.sh |
| **Repo ingestion** | GitHub API zip download (`urllib.request`) — no git CLI, avoids TTY/credential issues |

---

## Project structure

```
ethiksa-cer/
│
├── registry/
│   └── controls_v2.json          # 84-control ethics registry (source of truth)
│
├── Dockerfile                    # Single image: uvicorn + celery via supervisord
├── supervisord.conf              # Process manager: uvicorn (port 7860) + celery worker
├── entrypoint.sh                 # Startup: alembic upgrade head → seed controls → supervisord
│
├── backend/
│   ├── alembic.ini
│   ├── alembic/versions/
│   │   ├── 0001_initial.py
│   │   ├── 0002_add_controls_table.py
│   │   ├── 0003_add_extended_profile_fields.py
│   │   ├── 0004_add_rel_ai_scan_audit_tables.py   # workspace_hash, commit_sha, handoff_exports, metadata_supplements
│   │   ├── 0005_controls_cer_observability.py      # cer_observability, supplement_prompt, artefact_type_expected on controls
│   │   └── 0006_control_result_llm_fields.py       # student_summary, what_is_present, what_is_missing, doc_classification
│   ├── requirements.txt
│   │
│   ├── scripts/
│   │   └── seed_controls.py      # Upsert all 84 controls from registry JSON into DB (runs on every boot)
│   │
│   └── app/
│       ├── main.py               # FastAPI app, CORS, rate limiting (slowapi), router mounting
│       ├── registry_loader.py    # Load controls from DB (seeded from JSON); returns full dicts incl. cer_observability
│       │
│       ├── core/
│       │   ├── config.py         # Settings: DATABASE_URL, REDIS_URL, ANTHROPIC_API_KEY, GITHUB_TOKEN, etc.
│       │   ├── database.py       # SQLAlchemy engine + session factory
│       │   └── limiter.py        # slowapi rate limiter instance
│       │
│       ├── models/
│       │   ├── project.py              # projects table
│       │   ├── scan.py                 # scans table (status, commit_sha, workspace_hash, escalation_hints, cer_observability_summary)
│       │   ├── control.py              # controls table (cer_observability, supplement_prompt, artefact_type_expected)
│       │   ├── control_result.py       # control_results (outcome, evidence, explanation, remediation, student_summary, what_is_present, what_is_missing, doc_classification)
│       │   ├── metadata_supplement.py  # metadata_supplements (T3 supplement entries, declared_path, status_after_supplement)
│       │   ├── handoff_export.py       # handoff_exports (P7 reviewer, P8 certifier packages as JSONB)
│       │   └── audit_log.py            # audit_logs (append-only, one entry per pipeline stage)
│       │
│       ├── schemas/
│       │   ├── project.py
│       │   ├── scan.py            # ScanCreate, ScanRead, SupplementPatch, SupplementRead
│       │   └── audit_log.py
│       │
│       ├── api/v1/
│       │   ├── projects.py        # CRUD for projects
│       │   ├── scans.py           # Start scan, poll status, results, findings, report, SARIF, escalation-hints, supplement PATCH, handoff packages
│       │   ├── reports.py         # GET findings + audit log by scan
│       │   └── controls.py        # CRUD for control registry + registry-info
│       │
│       ├── pipeline/
│       │   ├── models.py          # ProjectProfile, ManifestEntry, RawFinding, SupplementEntry, EvidenceResult, LLMAnnotation
│       │   ├── s1_intake.py       # Validate profile + registry version
│       │   ├── s2_manifest.py     # GitHub API zip download, manifest build, workspace_hash, commit_sha
│       │   ├── s3_ai_detect.py    # Import scan → gen_triggered / rel_triggered
│       │   ├── s4_filter.py       # Assurance-level gate, T1/T2 → active, T3 → supplement_entries
│       │   ├── s5_runner.py       # ThreadPoolExecutor, no timeout, 32 plugins in parallel
│       │   ├── s5_plugins/        # 32 scanner plugins (see table below)
│       │   ├── s6_tag.py          # Reverse anchor map: stamps overlay_relevance on RawFindings
│       │   ├── s7_evidence.py     # 6-step decision tree → EvidenceResult per control
│       │   ├── s8_honesty.py      # Declared vs detected profile → escalation_hints
│       │   ├── s9_llm.py          # Claude/Ollama/Gemini → LLMAnnotation (6 fields per control)
│       │   ├── s10_assemble.py    # Build P1–P10 output packages
│       │   └── s11_audit.py       # Write stage record to audit_logs
│       │
│       └── worker/
│           ├── celery_app.py
│           └── tasks.py           # run_scan task: orchestrates S1–S11, persists all DB rows
│
└── frontend/
    ├── package.json               # Next.js 14, TanStack React Query v5, Tailwind CSS
    └── src/
        ├── lib/api.ts             # Typed API client (all backend endpoints)
        └── app/
            ├── layout.tsx              # Root layout + nav (History, New Review, Controls)
            ├── page.tsx                # History dashboard — all projects + scan runs
            ├── intake/page.tsx         # Project intake form (4 section cards)
            ├── scan/[scanId]/          # Pipeline progress tracker (S1–S11 timeline)
            ├── report/[scanId]/        # Ethics review report (grouped by pillar, filter tabs)
            ├── supplement/[scanId]/    # T3 Metadata Supplement form (grouped by pillar)
            ├── audit/[scanId]/         # Audit log viewer
            └── controls/page.tsx       # Control registry (sidebar + card grid, tier/pillar filters)
```

---

## Database tables

| Table | Purpose |
|-------|---------|
| `projects` | Project profiles (github_url, assurance_level, all 8 profile flags) |
| `scans` | Scan runs (status, commit_sha, workspace_hash, escalation_hints, cer_observability_summary) |
| `controls` | 84 registry controls (cer_observability, supplement_prompt, artefact_type_expected) |
| `control_results` | Per-control outcome + full LLM output (explanation, remediation, student_summary, what_is_present, what_is_missing, doc_classification) |
| `metadata_supplements` | T3 supplement entries (declared_path, existence_check_result, status_after_supplement) |
| `handoff_exports` | P7 (reviewer) and P8 (certifier) packages as JSONB |
| `audit_logs` | Append-only stage records (S1–S11) with payload and timing |
| `alembic_version` | Migration state |

Database: PostgreSQL hosted on **Neon** (production). Local dev uses a local PostgreSQL instance. The `entrypoint.sh` runs `alembic upgrade head` and `python -m scripts.seed_controls` on every container start — migrations and seed are idempotent.

---

## S5 plugin suite (32 plugins)

| Plugin | Controls covered |
|--------|-----------------|
| `governance_scanner` | GOV-01, GOV-05, GOV-06, GOV-07, GOV-09 |
| `ci_security_scanner` | GOV-01, GOV-07, SEC-03, SEC-05 |
| `docs_scanner` | GOV-01, GOV-02, GOV-10, RISK-01–03, PRIV-02, PRIV-03, PRIV-06, PRIV-08, TRAN-02–04, SAFE-01, SAFE-06, DOC-01, SOC-01 |
| `audit_governance_scanner` | GOV-09 |
| `risk_document_scanner` | RISK-01–06 |
| `privacy_scanner` | PRIV-01 |
| `pii_classifier` | PRIV-01 |
| `privacy_log_scanner` | PRIV-01 |
| `consent_scanner` | PRIV-03 |
| `access_control_scanner` | PRIV-05 |
| `retention_scanner` | PRIV-04 |
| `synthetic_data_scanner` | PRIV-09 |
| `disclosure_scanner` | PRIV-03, TRAN-01, TRAN-07, ACC-07 |
| `explainability_scanner` | — |
| `grounding_scanner` | TRAN-03 |
| `moderation_scanner` | TRAN-01 |
| `content_provenance_scanner` | TRAN-08 |
| `traceability_scanner` | TRAN-05, TRAN-06, DOC-04, DOC-05 |
| `robustness_test_scanner` | SAFE-01–03, SAFE-05 |
| `safe_failure_scanner` | — |
| `fallback_scanner` | HUMO-04, SAFE-04 |
| `threat_model_scanner` | — |
| `secrets_scanner` | SEC-01 |
| `input_validation_scanner` | SEC-02 |
| `prompt_injection_scanner` | SEC-02 |
| `dependency_scanner` | PRIV-06, SEC-03, SEC-06, DOC-05 |
| `sbom_scanner` | SEC-03 |
| `rate_limit_scanner` | SEC-04 |
| `pre_trained_model_scanner` | SEC-06 |
| `inference_privacy_scanner` | SEC-07 |
| `authz_scanner` | HUMO-02, HUMO-06, HUMO-07, SEC-01 |
| `oversight_code_scanner` | GOV-05, HUMO-01–04, HUMO-06, HUMO-07 |
| `fairness_artifact_scanner` | FAIR-01–03 |
| `fairness_metrics_scanner` | — |
| `discrimination_scanner` | — |
| `recourse_fairness_scanner` | HUMO-03, FAIR-04–07, ACC-05, ACC-06, ACC-08 |
| `accountability_scanner` | — |
| `audit_trail_scanner` | — |
| `audit_log_scanner` | — |
| `doc_completeness_scanner` | DOC-02–03, DOC-06–08 |
| `dependency_doc_scanner` | — |
| `version_manifest_scanner` | — |
| `ui_accessibility_scanner` | ACC-01, ACC-03, ACC-05, ACC-07 |
| `inclusion_scanner` | — |
| `wcag_scanner` | — |
| `data_provenance_scanner` | — |
| `drift_scanner` | — |
| `environmental_scanner` | — |
| `societal_impact_scanner` | SOC-02–03, SOC-06–08 |

---

## Key invariants

- **Registry version lock** — a version mismatch at S1 is a hard stop
- **Read-only plugins** — plugins read files as text/data only, never execute repository code
- **No git CLI** — repositories downloaded via GitHub API zip (`urllib.request`), avoiding TTY/credential issues in containerised environments
- **Deterministic scoring** — S7 is 100% rule-based; same input always produces the same output
- **LLM guardrails** — S9 runs at temperature 0; forbidden words: `certified`, `compliant`, `passed`, `failed`, `legally required`
- **T3 isolation** — T3 controls never enter the plugin runner; their outcome is always `not_evaluable` until a human submits a supplement declaration
- **Append-only audit** — every stage record is inserted, never updated or deleted
- **Idempotent boot** — `alembic upgrade head` + `seed_controls` run on every container start; safe to run multiple times
- **Coverage reported per tier** — T1/T2/T3 coverage stats are never aggregated; each tier is reported separately (I-13 compliance)

---

## Alignment

The CER control registry is aligned to:

- EU AI Act (2024)
- NIST AI Risk Management Framework (AI RMF 1.0)
- ISO/IEC 42001:2023

Alignment does not imply legal compliance. The CER is a pre-assurance tool only.

---

## License

Proprietary — Ethiksa (Pvt) Ltd. Distribution restricted. See `LICENSE`.
