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


def _resolve_broker_url() -> str:
    """Ping each Redis URL in order and return the first reachable one.

    Called at worker startup so the worker connects to whichever broker
    is alive right now — not just whichever was alive when the image was built.
    """
    import redis as redis_lib

    candidates = [u for u in [settings.redis_url, settings.redis_fallback_url] if u]
    for url in candidates:
        try:
            ssl_kwargs = {"ssl_cert_reqs": ssl.CERT_NONE} if url.startswith("rediss://") else {}
            client = redis_lib.from_url(url, socket_connect_timeout=3, **ssl_kwargs)
            client.ping()
            if url != candidates[0]:
                logger.warning("Primary Redis unavailable at startup — worker using fallback: %s", url)
            return url
        except Exception as exc:
            logger.warning("Redis URL unreachable at startup (%s): %s", url, exc)
            continue

    logger.error("All Redis URLs failed at startup — worker defaulting to primary.")
    return candidates[0]


# Primary Celery app — resolves broker at startup (primary → fallback)
celery_app = _make_celery(_resolve_broker_url())

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
