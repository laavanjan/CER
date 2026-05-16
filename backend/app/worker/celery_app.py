"""Celery application factory."""

import logging
import ssl
import sys

from celery import Celery

from app.core.config import settings

logger = logging.getLogger(__name__)


def _resolve_redis_url() -> str:
    """Return the first reachable Redis URL from primary → fallback.

    Tries each URL with a 3-second connect timeout. Falls back to the
    next URL on any connection error or over-limit response error.
    If all URLs fail, returns the primary so Celery surfaces the error.
    """
    import redis as redis_lib

    candidates = [u for u in [settings.redis_url, settings.redis_fallback_url] if u]
    for url in candidates:
        try:
            ssl_kwargs = {"ssl_cert_reqs": ssl.CERT_NONE} if url.startswith("rediss://") else {}
            client = redis_lib.from_url(url, socket_connect_timeout=3, **ssl_kwargs)
            client.ping()
            if url != candidates[0]:
                logger.warning("Primary Redis unavailable — using fallback: %s", url)
            return url
        except Exception as exc:
            logger.warning("Redis URL unreachable (%s): %s", url, exc)
            continue

    logger.error("All Redis URLs failed — defaulting to primary, Celery will retry.")
    return candidates[0]


_redis_url = _resolve_redis_url()
_uses_tls = _redis_url.startswith("rediss://")
_ssl_opts = {"ssl_cert_reqs": ssl.CERT_NONE} if _uses_tls else {}

celery_app = Celery(
    "ethiksa_worker",
    broker=_redis_url,
    backend=_redis_url,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    broker_use_ssl=_ssl_opts if _ssl_opts else None,
    redis_backend_use_ssl=_ssl_opts if _ssl_opts else None,
    # solo pool on Windows avoids WinError 5/6 shared-memory crashes.
    # On Linux (production) the default prefork pool is used.
    **( {"worker_pool": "solo"} if sys.platform == "win32" else {} ),
)
