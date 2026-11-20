from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import MonitoringSchedule, ScanJob, Website
from app.services.detection.rules import lease_is_free, next_backoff
from app.services.monitoring import run_scan


def claim_due_schedules(db: Session, worker_id: str, limit: int = 2) -> list[MonitoringSchedule]:
    now = datetime.now(UTC)
    rows = db.scalars(
        select(MonitoringSchedule)
        .where(
            MonitoringSchedule.next_run_at <= now,
            or_(MonitoringSchedule.locked_until.is_(None), MonitoringSchedule.locked_until <= now),
        )
        .order_by(MonitoringSchedule.next_run_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    ).all()
    claimed = []
    for row in rows:
        if not lease_is_free(row.locked_until, now):
            continue
        row.locked_until = now + timedelta(seconds=120)
        row.locked_by = worker_id
        row.lease_token = uuid.uuid4().hex
        claimed.append(row)
    db.commit()
    return claimed


def finish_schedule(db: Session, schedule_id: uuid.UUID, lease_token: str, status: str, interval: int) -> None:
    row = db.get(MonitoringSchedule, schedule_id)
    if row is None or row.lease_token != lease_token:
        return
    now = datetime.now(UTC)
    row.last_run_at = now
    row.last_status = status
    row.locked_until = None
    row.locked_by = None
    row.lease_token = None
    if status == "succeeded":
        row.consecutive_failures = 0
        row.retry_count = 0
        row.next_run_at = now + timedelta(seconds=interval)
    else:
        row.consecutive_failures += 1
        row.retry_count += 1
        row.next_run_at = now + timedelta(seconds=next_backoff(row.retry_count))
    db.commit()


def execute_claimed(db: Session, schedule_id: uuid.UUID, lease_token: str) -> str:
    schedule = db.get(MonitoringSchedule, schedule_id)
    if schedule is None or schedule.lease_token != lease_token:
        return "skipped"
    website = db.get(Website, schedule.website_id)
    if website is None or website.monitoring_state != "active":
        finish_schedule(db, schedule_id, lease_token, "skipped", 900)
        return "skipped"
    running = db.scalars(
        select(ScanJob).where(ScanJob.website_id == website.id, ScanJob.status.in_(["queued", "running"]), ScanJob.is_simulated.is_(False))
    ).first()
    if running is not None:
        finish_schedule(db, schedule_id, lease_token, "duplicate", website.config.interval_seconds if website.config else 900)
        return "duplicate"
    try:
        run_scan(db, website, trigger="scheduled")
        finish_schedule(db, schedule_id, lease_token, "succeeded", website.config.interval_seconds if website.config else 900)
        return "succeeded"
    except Exception:  # noqa: BLE001
        finish_schedule(db, schedule_id, lease_token, "failed", website.config.interval_seconds if website.config else 900)
        return "failed"
