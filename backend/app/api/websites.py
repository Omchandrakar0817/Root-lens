import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, owned_website
from app.core.config import get_settings
from app.core.database import get_db
from app.models import (
    Anomaly,
    AvailabilityMeasurement,
    Incident,
    MonitoringConfig,
    MonitoringSchedule,
    PerformanceResult,
    ScanJob,
    SecurityResult,
    SeoResult,
    User,
    Website,
)
from app.schemas.common import MonitoringUpdate, WebsiteCreate, WebsiteOut, WebsiteUpdate
from app.services.monitoring import run_scan, scans_in_last_hour
from app.services.safe_http import UnsafeURLError, validate_submission
from app.workers.tasks import enqueue_scan

router = APIRouter(prefix="/websites", tags=["websites"])
settings = get_settings()


def _out(website: Website) -> WebsiteOut:
    data = WebsiteOut.model_validate(website)
    data.interval_seconds = website.config.interval_seconds if website.config else None
    return data


@router.get("")
def list_websites(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[WebsiteOut]:
    stmt = select(Website).options(selectinload(Website.config)).where(Website.is_simulated.is_(False)).order_by(Website.created_at.desc())
    if user.role != "admin":
        stmt = stmt.where(Website.user_id == user.id)
    return [_out(item) for item in db.scalars(stmt).all()]


@router.post("", status_code=201)
def create_website(body: WebsiteCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> WebsiteOut:
    count = db.scalar(select(func.count()).select_from(Website).where(Website.user_id == user.id)) or 0
    if count >= settings.max_websites_per_user and user.role != "admin":
        raise HTTPException(status_code=400, detail=f"Website limit is {settings.max_websites_per_user}")
    try:
        url = validate_submission(body.url)
    except UnsafeURLError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    hostname = url.split("//", 1)[1].split("/")[0]
    exists = db.scalars(select(Website).where(Website.user_id == user.id, Website.url == url)).first()
    if exists:
        raise HTTPException(status_code=409, detail="That URL is already monitored")
    website = Website(user_id=user.id, name=body.name.strip(), url=url, hostname=hostname, monitoring_state="paused")
    db.add(website)
    db.flush()
    db.add(MonitoringConfig(website_id=website.id, interval_seconds=max(settings.min_monitor_interval_seconds, 900)))
    db.add(MonitoringSchedule(website_id=website.id, next_run_at=datetime.now(UTC) + timedelta(days=3650)))
    db.commit()
    db.refresh(website)
    website = db.scalars(select(Website).options(selectinload(Website.config)).where(Website.id == website.id)).one()
    return _out(website)


@router.get("/{website_id}")
def get_website(website_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    website = owned_website(website_id, user, db)
    db.refresh(website, attribute_names=["config"])
    return _out(website).model_dump()


@router.patch("/{website_id}")
def update_website(website_id: uuid.UUID, body: WebsiteUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> WebsiteOut:
    website = owned_website(website_id, user, db)
    if body.name:
        website.name = body.name.strip()
    db.commit()
    website = db.scalars(select(Website).options(selectinload(Website.config)).where(Website.id == website.id)).one()
    return _out(website)


@router.delete("/{website_id}")
def delete_website(website_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    website = owned_website(website_id, user, db)
    if user.role != "admin" and website.user_id != user.id:
        raise HTTPException(status_code=403, detail="You cannot delete this website")
    db.delete(website)
    db.commit()
    return {"detail": "Website deleted"}


@router.post("/{website_id}/monitoring")
def update_monitoring(website_id: uuid.UUID, body: MonitoringUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    website = owned_website(website_id, user, db)
    website.monitoring_state = body.state
    config = website.config or MonitoringConfig(website_id=website.id, interval_seconds=900)
    if body.interval_seconds:
        if body.interval_seconds < settings.min_monitor_interval_seconds:
            raise HTTPException(status_code=400, detail="Interval is shorter than the minimum")
        config.interval_seconds = body.interval_seconds
    if body.pagespeed_enabled is not None:
        config.pagespeed_enabled = body.pagespeed_enabled
    if body.security_enabled is not None:
        config.security_enabled = body.security_enabled
    if body.seo_enabled is not None:
        config.seo_enabled = body.seo_enabled
    db.add(config)
    schedule = website.schedule or MonitoringSchedule(website_id=website.id, next_run_at=datetime.now(UTC))
    if body.state == "active":
        schedule.next_run_at = datetime.now(UTC)
    else:
        schedule.next_run_at = datetime.now(UTC) + timedelta(days=3650)
        schedule.locked_until = None
        schedule.lease_token = None
    db.add(schedule)
    db.commit()
    return {"detail": f"Monitoring is {body.state}", "interval_seconds": config.interval_seconds}


@router.post("/{website_id}/scans")
def manual_scan(website_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    website = owned_website(website_id, user, db)
    if scans_in_last_hour(db, user.id) >= settings.max_scans_per_hour:
        raise HTTPException(status_code=429, detail="Hourly scan limit reached")
    queued = enqueue_scan(str(website.id))
    if queued:
        return {"detail": "Scan queued", "execution": "queued"}
    job = run_scan(db, website, trigger="manual")
    return {"detail": "Scan finished", "execution": "inline", "scan_id": str(job.id), "status": job.status}


@router.get("/{website_id}/scans")
def scan_history(website_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    website = owned_website(website_id, user, db)
    rows = db.scalars(select(ScanJob).where(ScanJob.website_id == website.id).order_by(ScanJob.created_at.desc()).limit(50)).all()
    return [
        {
            "id": str(row.id),
            "trigger": row.trigger,
            "status": row.status,
            "is_simulated": row.is_simulated,
            "error_message": row.error_message,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/{website_id}/availability")
def availability(website_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    website = owned_website(website_id, user, db)
    rows = db.scalars(
        select(AvailabilityMeasurement)
        .where(AvailabilityMeasurement.website_id == website.id, AvailabilityMeasurement.is_simulated.is_(False))
        .order_by(AvailabilityMeasurement.checked_at.desc())
        .limit(200)
    ).all()
    if not rows:
        return {"points": [], "uptime_percent": None, "message": "No availability history yet."}
    up = sum(1 for row in rows if row.is_up)
    return {
        "uptime_percent": round(100 * up / len(rows), 2),
        "points": [
            {
                "checked_at": row.checked_at,
                "is_up": row.is_up,
                "confirmed_failure": row.confirmed_failure,
                "http_status": row.http_status,
                "response_time_ms": row.response_time_ms,
                "error_type": row.error_type,
                "error_message": row.error_message,
                "final_url": row.final_url,
                "redirect_count": row.redirect_count,
                "dns_ok": row.dns_ok,
                "tls_valid": row.tls_valid,
            }
            for row in rows
        ],
    }


@router.get("/{website_id}/security")
def security(website_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    website = owned_website(website_id, user, db)
    row = db.scalars(select(SecurityResult).where(SecurityResult.website_id == website.id, SecurityResult.is_simulated.is_(False)).order_by(SecurityResult.checked_at.desc())).first()
    if row is None:
        return {"message": "No security check yet."}
    return {
        "checked_at": row.checked_at,
        "https_available": row.https_available,
        "redirects_to_https": row.redirects_to_https,
        "cert_valid": row.cert_valid,
        "cert_expires_at": row.cert_expires_at,
        "cert_issuer": row.cert_issuer,
        "days_until_expiry": row.days_until_expiry,
        "headers": row.headers,
        "findings": row.findings,
    }


@router.get("/{website_id}/performance")
def performance(website_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    website = owned_website(website_id, user, db)
    rows = db.scalars(select(PerformanceResult).where(PerformanceResult.website_id == website.id).order_by(PerformanceResult.fetched_at.desc()).limit(10)).all()
    return [
        {
            "strategy": row.strategy,
            "fetched_at": row.fetched_at,
            "available": row.available,
            "error_message": row.error_message,
            "performance_score": row.performance_score,
            "accessibility_score": row.accessibility_score,
            "seo_score": row.seo_score,
            "best_practices_score": row.best_practices_score,
            "lcp_ms": row.lcp_ms,
            "cls": row.cls,
            "inp_ms": row.inp_ms,
            "fcp_ms": row.fcp_ms,
            "tbt_ms": row.tbt_ms,
            "lcp_source": row.lcp_source,
            "cls_source": row.cls_source,
            "inp_source": row.inp_source,
            "fcp_source": row.fcp_source,
            "opportunities": row.opportunities,
            "note": "Scores come from Google PageSpeed Insights when a key is configured. Missing metrics stay null.",
        }
        for row in rows
    ]


@router.get("/{website_id}/seo")
def seo(website_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    website = owned_website(website_id, user, db)
    row = db.scalars(select(SeoResult).where(SeoResult.website_id == website.id, SeoResult.is_simulated.is_(False)).order_by(SeoResult.checked_at.desc())).first()
    if row is None:
        return {"message": "No SEO check yet."}
    return {
        "checked_at": row.checked_at,
        "title": row.title,
        "meta_description": row.meta_description,
        "h1_count": row.h1_count,
        "canonical": row.canonical,
        "robots_txt_present": row.robots_txt_present,
        "sitemap_present": row.sitemap_present,
        "images_checked": row.images_checked,
        "images_missing_alt": row.images_missing_alt,
        "forms_missing_labels": row.forms_missing_labels,
        "broken_links": row.broken_links,
        "findings": row.findings,
    }


@router.get("/{website_id}/anomalies")
def anomalies(website_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    website = owned_website(website_id, user, db)
    rows = db.scalars(select(Anomaly).where(Anomaly.website_id == website.id).order_by(Anomaly.detected_at.desc()).limit(100)).all()
    return [
        {
            "id": str(row.id),
            "metric": row.metric,
            "record_type": row.record_type,
            "method": row.method,
            "model_trained": row.model_trained,
            "score": row.score,
            "is_anomaly": row.is_anomaly,
            "value": row.value,
            "baseline": row.baseline,
            "evidence": row.evidence,
            "is_simulated": row.is_simulated,
            "detected_at": row.detected_at,
        }
        for row in rows
    ]


@router.get("/{website_id}/incidents")
def website_incidents(website_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    website = owned_website(website_id, user, db)
    rows = db.scalars(select(Incident).where(Incident.website_id == website.id).order_by(Incident.detected_at.desc()).limit(50)).all()
    return [_incident_brief(row) for row in rows]


def _incident_brief(row: Incident) -> dict:
    return {
        "id": str(row.id),
        "public_id": row.public_id,
        "website_id": str(row.website_id),
        "title": row.title,
        "category": row.category,
        "severity": row.severity,
        "status": row.status,
        "detected_at": row.detected_at,
        "resolved_at": row.resolved_at,
        "is_simulated": row.is_simulated,
        "symptoms": row.symptoms,
    }
