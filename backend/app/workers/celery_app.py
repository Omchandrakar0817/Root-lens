import ssl

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

_tls_options = {}
if settings.celery_broker_url.startswith("rediss://"):
    _tls_options["broker_use_ssl"] = {"ssl_cert_reqs": ssl.CERT_REQUIRED}
if settings.celery_result_backend.startswith("rediss://"):
    _tls_options["redis_backend_use_ssl"] = {"ssl_cert_reqs": ssl.CERT_REQUIRED}

celery_app = Celery(
    "incident_rca",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)
celery_app.conf.update(
    **_tls_options,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "dispatch-due-monitors": {
            "task": "app.workers.tasks.dispatch_due_monitors",
            "schedule": 30.0,
        }
    },
    timezone="UTC",
)
