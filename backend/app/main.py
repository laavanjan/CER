"""ethiksa-cer FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.api.v1 import controls, projects, reports, scans
from app.core.config import settings
from app.core.limiter import limiter

# ---------------------------------------------------------------------------
# Rate limiter (shared instance — imported by routers via app.core.limiter)
# ---------------------------------------------------------------------------

# Instantiate the FastAPI application with metadata
app = FastAPI(
    title="ethiksa-cer API",
    description="AIGAP · Code Ethics Reviewer — automated AI ethics pipeline",
    version="0.1.0",
)

app.state.limiter = limiter


async def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# Allow the Next.js frontend and any configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API key authentication middleware
# ---------------------------------------------------------------------------

_UNAUTHENTICATED_PATHS = {"/healthz", "/docs", "/openapi.json", "/redoc"}


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Require X-API-Key header when settings.api_key is configured.

    Paths listed in _UNAUTHENTICATED_PATHS are always allowed so that health
    checks and Swagger UI continue to work without a key.
    """

    async def dispatch(self, request: Request, call_next: object) -> Response:
        if settings.api_key is not None and request.url.path not in _UNAUTHENTICATED_PATHS:
            key = request.headers.get("X-API-Key")
            if key != settings.api_key:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or missing API key"},
                )
        return await call_next(request)  # type: ignore[arg-type]


app.add_middleware(ApiKeyMiddleware)
app.add_middleware(SlowAPIMiddleware)

# Mount versioned routers
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(scans.router, prefix="/api/v1/scans", tags=["scans"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(controls.router, prefix="/api/v1/controls", tags=["controls"])


@app.get("/healthz", tags=["health"])
def healthcheck() -> dict:
    """Liveness probe used by Docker / k8s."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Static frontend — served only when the Next.js export exists in the image.
# In local development this directory is absent and the dev server runs on
# its own port, so the block is intentionally skipped.
# ---------------------------------------------------------------------------

_FRONTEND_OUT = Path(__file__).parent.parent / "frontend_out"

if _FRONTEND_OUT.exists():
    # Serve Next.js static asset bundles from /_next/
    _next_dir = _FRONTEND_OUT / "_next"
    if _next_dir.exists():
        app.mount("/_next", StaticFiles(directory=str(_next_dir)), name="next-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        """Serve the Next.js static export with SPA fallback.

        Resolution order:
        1. Exact file match (e.g. favicon.ico, robots.txt)
        2. Page with trailing-slash index.html (e.g. /intake/ → intake/index.html)
        3. Root index.html — lets the Next.js client-side router take over for
           dynamic routes such as /scan/<id> and /report/<id>.
        """
        candidates = [
            _FRONTEND_OUT / full_path,
            _FRONTEND_OUT / full_path / "index.html",
            _FRONTEND_OUT / (full_path.rstrip("/") + ".html"),
        ]
        for candidate in candidates:
            if candidate.is_file():
                return FileResponse(str(candidate))
        # SPA fallback — serve root shell and let the client router handle it
        return FileResponse(str(_FRONTEND_OUT / "index.html"))
