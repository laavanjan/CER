# ethiksa-cer

> **AIGAP · Code Ethics Reviewer** — Automated pipeline that scans AI system repositories against ethical controls, producing structured findings, remediation guidance, and handoff packages for human reviewers.

For full architecture, pipeline details, control registry, and output package documentation see [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## Prerequisites

Make sure the following are installed before you begin:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for PostgreSQL, Redis, MinIO)
- Python 3.11+
- Node.js 20+
- npm 10+

---

## 1. Clone the repository

```bash
git clone https://github.com/Ethiksa/ethiksa-cer.git
cd ethiksa-cer
```

---

## 2. Configure environment variables

### Backend — create `backend/.env`

```env
# Database (use localhost when running backend locally, not inside Docker)
DATABASE_URL=postgresql://ethiksa:ethiksa@localhost:5432/ethiksa

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO (S3-compatible storage)
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=ethiksa-cer

# Anthropic — required for S9 LLM annotations
# Get your key at https://console.anthropic.com
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx

# Registry
REGISTRY_PATH=../registry/controls_v1.json
REGISTRY_VERSION=v1

# CORS
CORS_ORIGINS=["http://localhost:3000"]
```

> If `ANTHROPIC_API_KEY` is left empty the pipeline still runs — S9 will produce stub annotations instead of real LLM explanations.

---

## 3. Start infrastructure with Docker

This starts PostgreSQL, Redis, and MinIO only. The API and worker run locally so you get hot-reload.

```bash
cd docker
docker compose up postgres redis minio -d
```

Wait ~10 seconds, then verify all three are healthy:

```bash
docker compose ps
```

| Service | Port | Credentials |
|---------|------|-------------|
| PostgreSQL | `localhost:5432` | `ethiksa / ethiksa` |
| Redis | `localhost:6379` | — |
| MinIO | `localhost:9000` (API) · `localhost:9001` (console) | `minioadmin / minioadmin` |

---

## 4. Set up the Python backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv

# Windows (Git Bash)
source .venv/Scripts/activate
# Windows (PowerShell)
# .venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Seed controls from the registry JSON into the database (run once after migrations)
# Windows — provide the full path to the registry file:
python -c "from scripts.seed_controls import seed; seed(r'../registry/controls_v2.json')"
# macOS / Linux:
# python -m scripts.seed_controls
```

> The seed script is **idempotent** — safe to run multiple times. Existing records are skipped.
> You should see: `Seed complete: 78 inserted, 0 skipped.`

---

## 5. Start the FastAPI server

```bash
# Inside backend/ with .venv active
uvicorn app.main:app --reload --port 8000
```

Verify at `http://localhost:8000/healthz` — should return `{"status":"ok"}`.

Interactive API docs available at `http://localhost:8000/docs`.

---

## 6. Start the Celery worker

Open a **second terminal**, activate the same venv:

```bash
cd backend
source .venv/Scripts/activate   # or platform equivalent

# macOS / Linux
celery -A app.worker.celery_app worker --loglevel=info --concurrency=4

# Windows — prefork is broken on Windows; use solo pool instead
celery -A app.worker.celery_app worker --loglevel=info --pool=solo
```

> **Windows note:** The default `prefork` pool uses shared memory semaphores that Windows
> restricts, causing `PermissionError: [WinError 5] Access is denied`. The `--pool=solo`
> flag runs tasks in the same process (single-threaded) and works correctly on Windows.
>
> **If Ctrl+C hangs or spams errors on Windows**, the worker is stuck in a broken prefork
> state. Force-kill it from a new terminal:
> ```powershell
> taskkill /F /IM python.exe
> ```
> Then restart with `--pool=solo`.

You should see `[tasks] . run_scan` listed as a registered task.

---

## 7. Start the frontend

Open a **third terminal**:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

---

## All services at a glance

| Terminal | Directory | Command |
|----------|-----------|---------|
| 1 — Infrastructure | `docker/` | `docker compose up postgres redis minio -d` |
| 2 — API | `backend/` | `uvicorn app.main:app --reload --port 8000` |
| 3 — Worker | `backend/` | `celery -A app.worker.celery_app worker --loglevel=info` |
| 4 — Frontend | `frontend/` | `npm run dev` |

| URL | What |
|-----|------|
| `http://localhost:3000` | Frontend UI |
| `http://localhost:8000/docs` | Swagger API docs |
| `http://localhost:8000/healthz` | API health check |
| `http://localhost:9001` | MinIO storage console |

---

## Running everything in Docker (alternative)

If you want to run the full stack — including the API and worker — inside Docker:

```bash
cd docker

# Add your Anthropic key to the environment first
export ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx

docker compose up --build
```

The `api` container automatically runs `alembic upgrade head` before starting.
The frontend is not included in Docker Compose — run it separately with `npm run dev`.

---

## Hugging Face Spaces Deployment

ethiksa-cer ships a root-level `Dockerfile` that builds the Next.js frontend as a
static export and bundles it with the FastAPI backend + Celery worker into a single
container. Everything is served from **port 7860** as required by HF Spaces Docker
runtime.

### Prerequisites

You will need managed external services before deploying:

| Service | Recommended providers |
|---------|----------------------|
| PostgreSQL | Neon, Supabase, Render, Railway |
| Redis | Upstash, Redis Cloud |
| S3-compatible storage | AWS S3, Cloudflare R2, Backblaze B2 |

### Required Space secrets

Set these in **Settings → Variables and secrets** of your HF Space:

| Secret name | Description | Required |
|-------------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string, e.g. `postgresql://user:pass@host:5432/dbname` | ✅ |
| `REDIS_URL` | Redis connection string, e.g. `redis://user:pass@host:6379/0` | ✅ |
| `S3_ENDPOINT_URL` | S3-compatible endpoint URL, e.g. `https://s3.amazonaws.com` | ✅ |
| `S3_ACCESS_KEY` | S3 access key / key ID | ✅ |
| `S3_SECRET_KEY` | S3 secret key | ✅ |
| `S3_BUCKET` | Bucket name (default: `ethiksa-cer`) | optional |
| `ANTHROPIC_API_KEY` | Anthropic API key for LLM annotations in S9 | optional |
| `CORS_ORIGINS` | Comma-separated allowed origins (default: `["http://localhost:3000"]`) | optional |

> If `ANTHROPIC_API_KEY` is omitted, the pipeline still runs — S9 produces stub
> annotations instead of real LLM explanations.

### Deployment steps

1. Create a new **Docker** Space on [huggingface.co/new-space](https://huggingface.co/new-space).
2. Set the SDK to **Docker**.
3. Push this repository (or a fork) as the Space source — HF Spaces will use
   the root-level `Dockerfile` automatically.
4. Add all required secrets listed above under **Settings → Variables and secrets**.
5. The Space will build and start. On first boot the entrypoint:
   - runs `alembic upgrade head` to apply database migrations,
   - runs `python -m scripts.seed_controls` to populate the controls table from
     the bundled `registry/controls_v2.json` (idempotent — safe to re-run).
6. Once the Space is **Running**, the UI is available at the Space URL and the
   API docs at `<space-url>/docs`.

### Local build verification

```bash
# Build the image locally (requires Docker)
docker build -t ethiksa-cer:hf .

# Run with external services already running
docker run --rm -p 7860:7860 \
  -e DATABASE_URL=postgresql://ethiksa:ethiksa@localhost:5432/ethiksa \
  -e REDIS_URL=redis://localhost:6379/0 \
  -e S3_ENDPOINT_URL=http://localhost:9000 \
  -e S3_ACCESS_KEY=minioadmin \
  -e S3_SECRET_KEY=minioadmin \
  ethiksa-cer:hf
```

Open `http://localhost:7860` to verify the frontend is served and
`http://localhost:7860/healthz` for the API health check.

---

## Stopping / resetting

```bash
# Stop Docker services
cd docker
docker compose down

# Wipe all data (database + MinIO volumes)
docker compose down -v
```

---

## Running tests

```bash
cd backend
source .venv/Scripts/activate
pytest tests/ -v
```

---

## License

Proprietary — Ethiksa (Pvt) Ltd. Distribution restricted. See `LICENSE`.
