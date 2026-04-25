"""Celery application factory."""

import sys

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "ethiksa_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    # solo pool on Windows avoids WinError 5/6 shared-memory crashes.
    # On Linux (production) the default prefork pool is used.
    **( {"worker_pool": "solo"} if sys.platform == "win32" else {} ),
)
