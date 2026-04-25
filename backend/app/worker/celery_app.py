"""Celery application factory."""

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
    # Windows fix: prefork pool uses shared memory handles that Windows denies.
    # solo pool runs tasks in-process and avoids the WinError 5/6 crashes.
    worker_pool="solo",
)
