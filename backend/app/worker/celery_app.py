"""Celery application factory."""

import logging
import ssl
import sys

from celery import Celery

from app.core.config import settings

logger = logging.getLogger(__name__)


def _make_celery(url: str) -> Celery:
    """Create and configure a Celery app for the given Redis URL."""
    uses_tls = url.startswith("rediss://")
    ssl_opts = {"ssl_cert_reqs": ssl.CERT_NONE} if uses_tls else {}
    app = Celery(
        "ethiksa_worker",
        broker=url,
        backend=url,
        include=["app.worker.tasks"],
    )
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        broker_connection_retry_on_startup=True,
        broker_use_ssl=ssl_opts if ssl_opts else None,
        redis_backend_use_ssl=ssl_opts if ssl_opts else None,
        **( {"worker_pool": "solo"} if sys.platform == "win32" else {} ),
    )
    return app


# Primary Celery app — uses REDIS_URL (Upstash)
celery_app = _make_celery(settings.redis_url)

# Fallback Celery app — uses REDIS_FALLBACK_URL (Redis Cloud).
# Built lazily so a missing fallback URL doesn't crash startup.
_fallback_app: Celery | None = None


def get_fallback_app() -> Celery | None:
    """Return the fallback Celery app, or None if no fallback URL is configured."""
    global _fallback_app
    if not settings.redis_fallback_url:
        return None
    if _fallback_app is None:
        _fallback_app = _make_celery(settings.redis_fallback_url)
        logger.warning("Switching Celery broker to fallback Redis: %s", settings.redis_fallback_url)
    return _fallback_app
