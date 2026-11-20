import uuid

from app.core.database import SessionLocal
from app.models import Website
from app.services.scheduling import claim_due_schedules, execute_claimed
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.dispatch_due_monitors")
def dispatch_due_monitors() -> dict:
    db = SessionLocal()
    try:
        claimed = claim_due_schedules(db, worker_id=dispatch_due_monitors.request.id or "beat", limit=2)
        ids = [(str(row.id), row.lease_token) for row in claimed if row.lease_token]
    finally:
        db.close()
    for schedule_id, token in ids:
        run_scheduled_scan.delay(schedule_id, token)
    return {"claimed": len(ids)}


@celery_app.task(name="app.workers.tasks.run_scheduled_scan", bind=True, max_retries=0)
def run_scheduled_scan(self, schedule_id: str, lease_token: str) -> str:
    db = SessionLocal()
    try:
        return execute_claimed(db, uuid.UUID(schedule_id), lease_token)
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.run_manual_scan")
def run_manual_scan(website_id: str) -> str:
    from app.services.monitoring import run_scan

    db = SessionLocal()
    try:
        website = db.get(Website, uuid.UUID(website_id))
        if website is None:
            return "missing"
        job = run_scan(db, website, trigger="manual")
        return str(job.id)
    finally:
        db.close()


def enqueue_scan(website_id: str) -> bool:
    try:
        import redis

        from app.core.config import get_settings

        client = redis.Redis.from_url(get_settings().redis_url, socket_connect_timeout=0.5)
        client.ping()
        run_manual_scan.delay(website_id)
        return True
    except Exception:
        return False
