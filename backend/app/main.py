"""ethiksa-cer FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import projects, reports, scans
from app.core.config import settings

# Instantiate the FastAPI application with metadata
app = FastAPI(
    title="ethiksa-cer API",
    description="AIGAP · Code Ethics Reviewer — automated AI ethics pipeline",
    version="0.1.0",
)

# Allow the Next.js frontend and any configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount versioned routers
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(scans.router, prefix="/api/v1/scans", tags=["scans"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])


@app.get("/healthz", tags=["health"])
def healthcheck() -> dict:
    """Liveness probe used by Docker / k8s."""
    return {"status": "ok"}
