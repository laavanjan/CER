# ── Python runtime (backend only — frontend is served from Vercel) ────────────
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

# Copy supervisord configuration
COPY supervisord.conf /supervisord.conf

# Copy and set executable permission on the entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# HF Spaces Docker runtime requires port 7860
EXPOSE 7860

ENTRYPOINT ["/entrypoint.sh"]
