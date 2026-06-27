"""Celery 应用配置"""
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "metadata_completion",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.jobs.metadata_sync", "app.jobs.es_sync"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    worker_pool="solo",
    task_track_started=True,
    # task_acks_late=True with gevent pool: all tasks share a single OS
    # process via greenlets. If the process crashes, all unacknowledged tasks
    # are re-delivered. Ensure every task registered here is idempotent.
    task_acks_late=True,
    task_soft_time_limit=300,
    task_time_limit=600,
    worker_prefetch_multiplier=1,
    broker_connection_timeout=5,
)
