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
```

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

celery -A app.worker.celery_app worker --loglevel=info --concurrency=4
```

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
