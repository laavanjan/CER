# ethiksa-cer

> **AIGAP · Code Ethics Reviewer** — Automated pipeline that scans AI system repositories against 78 ethical controls across 11 pillars, producing structured findings, remediation guidance, and handoff packages for human reviewers.

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
| S1 | Accept the code | GitHub URL / ZIP ingested. Registry version verified. Hard stop on mismatch. |
| S2 | Read the repository | Full file manifest built. Secrets masked before storage. |
| S3 | Detect AI type | Import patterns scanned. `gen_triggered` and `rel_triggered` flags set. |
| S4 | Filter controls | 78 controls filtered by project profile. Inapplicable → `NOT_TRIGGERED`. T3 → supplement queue. |
| S5 | Run plugin suite | 31 scanner plugins run in parallel. Each produces a `RawFinding` JSON. Never executes repo code. |
| S6 | Tag GEN/REL findings | GEN and REL overlay findings tagged with anchor mappings from the registry. |
| S7 | Map evidence | `RawFindings` → `PASS / PARTIAL / MISSING` per control. 100% deterministic. No AI. |
| S8 | Honesty check | Declared profile vs detected signals. Conflicts → `escalation_hints[]`. |
| S9 | LLM explanations | Claude API (temp=0) writes plain-English explanations and remediation steps for every non-pass result. |
| S10 | Assemble outputs | 6 output packages assembled for 6 different audiences. Zero new decisions. |
| S11 | Audit log | Every decision, input, and output written to append-only WORM audit store. |

---

## The 78 controls across 11 pillars

| Pillar | Controls | Focus |
|--------|----------|-------|
| P1 — Governance & Accountability | 10 | Ownership, purpose, risk assessment |
| P2 — Transparency & Explainability | 8 | Explainability, audit trails, disclosure |
| P3 — Fairness & Non-Discrimination | 7 | Bias testing, demographic parity |
| P4 — Privacy & Data Protection | 8 | PII handling, consent, retention |
| P5 — Security & Robustness | 8 | Threat modelling, adversarial testing |
| P6 — Human Oversight & Control | 7 | Override mechanisms, monitoring |
| P7 — Safety | 6 | Safe failure, hazard identification |
| P8 — Environmental Impact | 3 | Compute efficiency, carbon tracking |
| P9 — Documentation | 8 | Model cards, version manifests, audit logs |
| P10 — Accessibility & Inclusion | 8 | WCAG, human-factors hazards |
| P11 — Data Quality | 9 | Provenance, labelling, drift detection |

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14 (App Router), Tailwind CSS, shadcn/ui, React Query |
| **Backend** | FastAPI (Python), Celery + Redis (async task queue), PyGitHub |
| **Scanners** | 31 Python plugin modules, plugin runner with parallel execution |
| **AI / LLM** | Anthropic Claude API (temp=0) at S9, LangChain prompt orchestration |
| **Storage** | PostgreSQL (findings), Redis (queue + cache), S3/MinIO (repos + ZIPs) |
| **Audit** | Append-only WORM log store (DOC-07 compliance) |
| **Infra** | Docker, GitHub Actions (CI/CD), Pytest, Alembic (DB migrations) |

---

## Project structure

```
ethiksa-cer/
│
├── registry/
│   └── controls_v1.json          # The canonical 78-control ethics registry (source of truth)
│
├── docker/
│   ├── docker-compose.yml        # Orchestrates postgres, redis, minio, api, worker
│   ├── Dockerfile.api            # Image for FastAPI service
│   └── Dockerfile.worker         # Image for Celery worker
│
├── .github/workflows/ci.yml      # GitHub Actions CI: lint, type-check, tests
│
├── backend/
│   ├── alembic.ini               # Alembic config pointing to migrations folder
│   ├── alembic/
│   │   ├── env.py                # DB connection setup for migrations
│   │   ├── script.py.mako        # Migration file template
│   │   └── versions/0001_initial.py  # Initial DB schema migration
│   ├── requirements.txt          # Python dependencies
│   ├── pyproject.toml            # Ruff/mypy/pytest config
│   │
│   └── app/
│       ├── main.py               # FastAPI app entry point, CORS, router mounting
│       ├── registry_loader.py    # Helper to load controls_v1.json from disk
│       │
│       ├── core/
│       │   ├── config.py         # Settings (DATABASE_URL, REDIS_URL, API keys via env vars)
│       │   └── database.py       # SQLAlchemy engine + session factory
│       │
│       ├── models/               # SQLAlchemy ORM models (DB table definitions)
│       │   ├── project.py        # Project table
│       │   ├── scan.py           # Scan table (status, timestamps, celery task ID)
│       │   ├── control_result.py # Per-control outcome + LLM explanation storage
│       │   └── audit_log.py      # WORM audit log entries
│       │
│       ├── schemas/              # Pydantic request/response schemas (API contracts)
│       │   ├── project.py
│       │   ├── scan.py
│       │   ├── control_result.py
│       │   └── audit_log.py
│       │
│       ├── api/v1/               # FastAPI routers
│       │   ├── projects.py       # CRUD endpoints for projects
│       │   ├── scans.py          # Start scan, poll status, list scans
│       │   └── reports.py        # Retrieve scan findings/packages
│       │
│       ├── pipeline/             # The 11-step ethics review pipeline
│       │   ├── models.py         # Pipeline data models (ProjectProfile, RawFinding, etc.)
│       │   ├── s1_intake.py      # Step 1: validate input + registry version
│       │   ├── s2_manifest.py    # Step 2: build file manifest
│       │   ├── s3_ai_detect.py   # Step 3: detect AI type (gen/rel)
│       │   ├── s4_filter.py      # Step 4: filter applicable controls
│       │   ├── s5_runner.py      # Step 5: parallel plugin execution
│       │   ├── s5_plugins/
│       │   │   ├── base.py           # BasePlugin ABC (shared utilities)
│       │   │   ├── privacy_scanner.py   # Checks for PIA/DPIA docs
│       │   │   ├── governance_scanner.py # Checks governance/accountability docs
│       │   │   └── docs_scanner.py      # Checks model cards, README, changelogs
│       │   ├── s6_tag.py         # Step 6: tag GEN/REL overlay findings
│       │   ├── s7_evidence.py    # Step 7: deterministic PASS/PARTIAL/MISSING mapping
│       │   ├── s8_honesty.py     # Step 8: declared vs detected profile check
│       │   ├── s9_llm.py         # Step 9: Claude API — explain + remediate + classify
│       │   ├── s10_assemble.py   # Step 10: assemble 6 output packages
│       │   └── s11_audit.py      # Step 11: write to WORM audit log
│       │
│       └── worker/
│           ├── celery_app.py     # Celery app instance configuration
│           └── tasks.py          # `run_scan` task — orchestrates S1–S11, updates DB status
│
├── frontend/
│   ├── package.json              # Node dependencies (Next.js, React Query, Tailwind, etc.)
│   ├── next.config.js            # Next.js config
│   ├── tailwind.config.js        # Tailwind CSS config
│   ├── tsconfig.json             # TypeScript config
│   └── src/app/
│       ├── layout.tsx            # Root layout (fonts, global nav)
│       ├── page.tsx              # Homepage / landing
│       ├── globals.css           # Global Tailwind styles
│       ├── providers.tsx         # React Query provider wrapper
│       ├── intake/page.tsx       # Project intake form
│       ├── scan/[scanId]/page.tsx    # Live scan stage progress tracker
│       └── report/[scanId]/page.tsx  # Final report — findings, remediation, packages
│
└── README.md                     # Full project documentation

```

---

## Pipeline stages — implementation status

**Milestone 1 (S1 → S7)** ✅ complete  
**Milestone 2 (S8 → S11)** ✅ complete  
**S5 plugin suite (31 plugins / 78 controls)** ✅ complete

- [x] Repo scaffolded
- [x] S1 — Project intake & version verification
- [x] S2 — Repository reader & manifest builder
- [x] S3 — AI type detection (gen_triggered / rel_triggered)
- [x] S4 — Control filter & applicability engine
- [x] S5 — Plugin runner & 31 scanner plugins (all pillars covered)
- [x] S6 — GEN/REL overlay tagger
- [x] S7 — Evidence mapper (RawFindings → PASS/PARTIAL/MISSING)
- [x] S8 — Honesty check (declared profile vs detected signals)
- [x] S9 — LLM explanations (Claude API, temp=0)
- [x] S10 — Output assembler (6 audience packages)
- [x] S11 — Audit log (append-only WORM store)

### S5 plugin suite (31 plugins)

| Plugin | Controls | Pillar |
|--------|----------|--------|
| `governance_scanner` | GOV-01, GOV-02 | P1 Governance |
| `risk_assessment_scanner` | GOV-03, GOV-04 | P1 Governance |
| `accountability_scanner` | GOV-05, GOV-06, GOV-07 | P1 Governance |
| `audit_governance_scanner` | GOV-08, GOV-09, GOV-10 | P1 Governance |
| `explainability_scanner` | TRN-01, TRN-02 | P2 Transparency |
| `disclosure_scanner` | TRN-03, TRN-04, TRN-05 | P2 Transparency |
| `audit_trail_scanner` | TRN-06, TRN-07, TRN-08 | P2 Transparency |
| `bias_scanner` | FAR-01, FAR-02 | P3 Fairness |
| `fairness_metrics_scanner` | FAR-03, FAR-04, FAR-05 | P3 Fairness |
| `discrimination_scanner` | FAR-06, FAR-07 | P3 Fairness |
| `privacy_scanner` | PRV-01 | P4 Privacy |
| `consent_scanner` | PRV-02, PRV-03 | P4 Privacy |
| `retention_scanner` | PRV-04, PRV-05 | P4 Privacy |
| `pii_code_scanner` | PRV-06, PRV-07, PRV-08 | P4 Privacy |
| `threat_model_scanner` | SEC-01, SEC-02 | P5 Security |
| `dependency_scanner` | SEC-03, SEC-04 | P5 Security |
| `access_control_scanner` | SEC-05, SEC-06, SEC-07, SEC-08 | P5 Security |
| `human_override_scanner` | OVR-01, OVR-02 | P6 Oversight |
| `escalation_scanner` | OVR-03, OVR-04 | P6 Oversight |
| `monitoring_scanner` | OVR-05, OVR-06, OVR-07 | P6 Oversight |
| `safe_failure_scanner` | SAF-01, SAF-02, SAF-03 | P7 Safety |
| `safety_testing_scanner` | SAF-04, SAF-05, SAF-06 | P7 Safety |
| `environmental_scanner` | ENV-01, ENV-02, ENV-03 | P8 Environmental |
| `docs_scanner` | DOC-01, DOC-02 | P9 Documentation |
| `version_manifest_scanner` | DOC-03, DOC-04 | P9 Documentation |
| `audit_log_scanner` | DOC-05, DOC-06 | P9 Documentation |
| `dependency_doc_scanner` | DOC-07, DOC-08 | P9 Documentation |
| `wcag_scanner` | ACC-01, ACC-02, ACC-03, ACC-04 | P10 Accessibility |
| `inclusion_scanner` | ACC-05, ACC-06, ACC-07 | P10 Accessibility |
| `data_provenance_scanner` | DQ-01, DQ-02, DQ-03 | P11 Data Quality |
| `drift_scanner` | DQ-04, DQ-05, DQ-06 | P11 Data Quality |

---

## Key rules the CER enforces

- **Registry version lock** — a version mismatch at S1 is a hard stop, not a warning
- **Read-only plugins** — plugins read files as text data only, never execute repo code
- **Deterministic scoring** — S7 is 100% rule-based; same input always produces same output
- **LLM guardrails** — S9 runs at temperature 0; forbidden words: `certified`, `compliant`, `passed`, `failed`, `legally required`
- **Append-only audit** — every scan decision is written to a WORM store; nothing is ever overwritten

---

## Control statuses

| Status | Meaning |
|--------|---------|
| `pass` | All required evidence found and verified |
| `partial` | Some evidence present; one or more components missing |
| `missing` | No evidence found for this control |
| `not_triggered` | Control does not apply to this project type |
| `not_evaluable` | T3 supplement not submitted; escalation required |

---

## Output packages

The CER produces 6 output packages at S10:

1. **Developer Report** — per-control findings, plain-English explanations, remediation steps
2. **Student Report** — same findings, simplified language, softer severity labels
3. **JSON Findings File** — machine-readable, all 78 statuses as structured objects
4. **T3 Supplement Package** — governance forms for human-decision controls
5. **ADR Handoff Package** — pre-formatted package for the human AI Design Reviewer
6. **Audit Record** — complete immutable scan record for the WORM store

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
