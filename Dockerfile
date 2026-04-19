# ── Stage 1: Build the Next.js frontend ─────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /build/frontend

# Install dependencies first (layer-cached until package files change)
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy source and build a static export
COPY frontend/ .

# Disable telemetry in CI / Docker builds
ENV NEXT_TELEMETRY_DISABLED=1

# Enable static export mode (output:'export') for the production Docker image.
# This flag is NOT set in local development so dynamic UUID routes work normally.
ENV NEXT_EXPORT=true

# In production the frontend calls /api/... relative to the origin,
# so NEXT_PUBLIC_API_URL is intentionally left empty.
RUN npm run build
# output:'export' writes static files to /build/frontend/out


# ── Stage 2: Python runtime ──────────────────────────────────────────────────
FROM python:3.11-slim

# System dependencies: PostgreSQL client libs, git (S2 clone), supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    git \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source
COPY backend/ .

# Copy registry JSON files (used by the seed script on first boot)
COPY registry/ /registry

# Copy the built Next.js static export into the location FastAPI expects
COPY --from=frontend-builder /build/frontend/out /app/frontend_out

# Copy supervisord configuration
COPY supervisord.conf /supervisord.conf

# Copy and set executable permission on the entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# HF Spaces Docker runtime requires port 7860
EXPOSE 7860

ENTRYPOINT ["/entrypoint.sh"]
