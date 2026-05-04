"""Celery application definition for AEGIS async task workers."""
from __future__ import annotations

from celery import Celery

from aegis.config import settings

celery_app = Celery(
    "aegis",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "aegis.tasks.codegen_tasks",
        "aegis.tasks.enforcement_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
