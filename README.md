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
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers
│   │   ├── pipeline/         # S1–S11 pipeline stages
│   │   │   ├── s1_intake.py
│   │   │   ├── s2_manifest.py
│   │   │   ├── s3_ai_detect.py
│   │   │   ├── s4_filter.py
│   │   │   ├── s5_plugins/   # 31 scanner plugins
│   │   │   ├── s6_tag.py
│   │   │   ├── s7_evidence.py
│   │   │   ├── s8_honesty.py
│   │   │   ├── s9_llm.py
│   │   │   ├── s10_assemble.py
│   │   │   └── s11_audit.py
│   │   ├── models/           # SQLAlchemy models
│   │   ├── registry/         # Canonical 78-control registry JSON
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   └── workers/          # Celery task definitions
│   ├── alembic/              # DB migrations
│   └── tests/
├── frontend/
│   ├── app/                  # Next.js App Router pages
│   │   ├── intake/           # Project intake form
│   │   ├── scan/             # Scan progress + live status
│   │   └── report/           # Findings + 6 output packages
│   └── components/
├── docker/
│   ├── docker-compose.yml
│   └── Dockerfile.*
├── .github/
│   └── workflows/
│       └── ci.yml
├── registry/
│   └── controls_v1.json      # Canonical control registry (versioned)
└── README.md
```

---

## Pipeline stages being built

Progress toward **S1 → S7** as the first milestone:

- [x] Repo scaffolded
- [ ] S1 — Project intake & version verification
- [ ] S2 — Repository reader & manifest builder
- [ ] S3 — AI type detection (gen_triggered / rel_triggered)
- [ ] S4 — Control filter & applicability engine
- [ ] S5 — Plugin runner & 31 scanner plugins
- [ ] S6 — GEN/REL overlay tagger
- [ ] S7 — Evidence mapper (RawFindings → PASS/PARTIAL/MISSING)

S8 → S11 to follow in the next milestone.

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
