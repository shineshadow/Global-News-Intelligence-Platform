from dataclasses import asdict

from app.services.alert_service import deliver_alert_delivery
from workers.async_runner import run_async
from workers.celery_app import celery_app


@celery_app.task(
    name="alerts.deliver",
    acks_late=True,
)
def deliver_alert_delivery_task(delivery_id: int) -> dict:
    result = run_async(
        lambda: deliver_alert_delivery(
            delivery_id,
        )
    )
    return asdict(result)
