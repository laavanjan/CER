"""Celery application factory."""

import ssl
import sys

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "ethiksa_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.worker.tasks"],
)

# Upstash and other TLS Redis instances use rediss:// — configure SSL accordingly
_uses_tls = settings.redis_url.startswith("rediss://")
_ssl_opts = {"ssl_cert_reqs": ssl.CERT_NONE} if _uses_tls else {}

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
