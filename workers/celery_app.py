from celery import Celery

from app.config import settings


celery_app = Celery(
    "global_news_intelligence",
    broker=settings.celery_broker_url,
    include=[
        "workers.ingestion.tasks",
        "workers.scheduler.tasks",
    ],
)


celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],

    # We keep task outcomes in PostgreSQL ingestion_runs.
    task_ignore_result=True,

    # Use UTC everywhere internally.
    timezone="UTC",
    enable_utc=True,

    # Polling is designed to be idempotent, so acknowledge only
    # after execution finishes.
    task_acks_late=True,

    # Long-running ingestion tasks should not be heavily prefetched.
    worker_prefetch_multiplier=1,

    # Retry Redis connection when workers start before Redis.
    broker_connection_retry_on_startup=True,

    # Redis redelivers an unacknowledged task after this period.
    broker_transport_options={
        "visibility_timeout": 3600,
    },

    task_routes={
        "ingestion.poll_source_endpoint": {
            "queue": "ingestion",
        },
        "scheduler.dispatch_due_source_endpoints": {
            "queue": "scheduler",
        },
    },

    beat_schedule={
        "dispatch-due-source-endpoints": {
            "task": (
                "scheduler.dispatch_due_source_endpoints"
            ),
            "schedule": float(
                settings.celery_dispatch_interval_seconds
            ),
            "options": {
                "queue": "scheduler",
            },
        },
    },
)