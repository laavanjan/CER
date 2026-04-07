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
    # Retry on connection errors during startup
    broker_connection_retry_on_startup=True,
)
