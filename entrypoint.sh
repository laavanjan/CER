#!/bin/sh
# entrypoint.sh — run on container start before handing off to supervisord.
#
# Steps:
#   1. Apply any pending Alembic migrations.
#   2. Seed the controls table from the registry JSON (idempotent).
#   3. Start supervisord which manages uvicorn + celery.

set -e

cd /app

echo "==> Running database migrations..."
alembic upgrade head

echo "==> Seeding controls table (idempotent)..."
python -m scripts.seed_controls

echo "==> Starting services via supervisord..."
exec supervisord -c /supervisord.conf
