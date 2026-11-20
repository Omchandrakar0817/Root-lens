from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    AgentMetric,
    AiRecommendation,
    Anomaly,
    AvailabilityMeasurement,
    Incident,
    IncidentEvent,
    MlModel,
    MonitoringAgent,
    PerformanceResult,
    RcaAnalysis,
    ScanJob,
    SecurityResult,
    SeoResult,
    Website,
)
from app.services.ai.gemini import explain
from app.services.detection.anomaly import evaluate_series, forecast_trend
from app.services.detection.rules import MeasurementView, classify
from app.services.rca.engine import analyze as analyze_rca
from app.services.safe_http import safe_fetch
from app.services.scanners.pagespeed import analyze_pagespeed
from app.services.scanners.security import analyze_security
from app.services.scanners.seo import analyze_html, check_robots_and_sitemap

settings = get_settings()


def _now() -> datetime:
    return datetime.now(UTC)


def _public_id() -> str:
    return "INC-" + uuid.uuid4().hex[:8].upper()


def scans_in_last_hour(db: Session, user_id: uuid.UUID) -> int:
    cutoff = _now() - timedelta(hours=1)
    rows = db.scalars(
        select(ScanJob).where(ScanJob.user_id == user_id, ScanJob.created_at >= cutoff, ScanJob.is_simulated.is_(False))
    ).all()
    return len(rows)


def run_scan(db: Session, website: Website, trigger: str, simulated: bool = False, synthetic: dict | None = None) -> ScanJob:
    job = ScanJob(
        website_id=website.id,
        user_id=website.user_id,
        trigger=trigger,
        status="running",
        is_simulated=simulated,
        started_at=_now(),
    )
    db.add(job)
    db.flush()
    try:
        if synthetic:
            _apply_synthetic(db, website, job, synthetic)
        else:
            _apply_live(db, website, job)
        job.status = "succeeded"
        job.finished_at = _now()
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.error_message = exc.__class__.__name__
        job.finished_at = _now()
        db.commit()
        raise
    db.commit()
    db.refresh(job)
    return job


def _previous_real(db: Session, website_id: uuid.UUID) -> AvailabilityMeasurement | None:
    return db.scalars(
        select(AvailabilityMeasurement)
        .where(AvailabilityMeasurement.website_id == website_id, AvailabilityMeasurement.is_simulated.is_(False))
        .order_by(AvailabilityMeasurement.checked_at.desc())
        .limit(1)
    ).first()


def _baseline_ms(db: Session, website_id: uuid.UUID) -> float | None:
    rows = db.scalars(
        select(AvailabilityMeasurement)
        .where(
            AvailabilityMeasurement.website_id == website_id,
            AvailabilityMeasurement.is_simulated.is_(False),
            AvailabilityMeasurement.response_time_ms.is_not(None),
        )
        .order_by(AvailabilityMeasurement.checked_at.desc())
        .limit(50)
    ).all()
    values = [row.response_time_ms for row in rows if row.response_time_ms is not None]
    if not values:
        return None
    return sum(values) / len(values)


def _apply_live(db: Session, website: Website, job: ScanJob) -> None:
    page = safe_fetch(website.url)
    config = website.config
    previous = _previous_real(db, website.id)
    view = MeasurementView(
        is_up=bool(page.status_code and page.status_code < 500 and page.error_type not in {"dns", "timeout", "connection", "blocked_url"}),
        http_status=page.status_code,
        response_time_ms=page.elapsed_ms,
        error_type=page.error_type,
        error_message=page.error_message,
        dns_ok=page.dns_ok,
        tls_valid=page.tls_valid,
    )
    previous_view = None
    if previous:
        previous_view = MeasurementView(
            is_up=previous.is_up,
            http_status=previous.http_status,
            response_time_ms=previous.response_time_ms,
            error_type=previous.error_type,
            error_message=previous.error_message,
            dns_ok=previous.dns_ok,
            tls_valid=previous.tls_valid,
        )
    from app.services.detection.rules import confirm_failure

    confirmed = confirm_failure(view, previous_view)
    measurement = AvailabilityMeasurement(
        scan_job_id=job.id,
        website_id=website.id,
        checked_at=_now(),
        is_up=view.is_up,
        confirmed_failure=confirmed,
        http_status=page.status_code,
        response_time_ms=page.elapsed_ms,
        error_type=page.error_type,
        error_message=page.error_message,
        final_url=page.final_url,
        redirect_count=page.redirect_count,
        dns_ok=page.dns_ok,
        tls_valid=page.tls_valid,
        is_simulated=False,
    )
    db.add(measurement)
    security = None
    seo = None
    performance = None
    if config is None or config.security_enabled:
        security_data = analyze_security(page, website.url)
        security = SecurityResult(
            scan_job_id=job.id,
            website_id=website.id,
            checked_at=_now(),
            https_available=security_data["https_available"],
            redirects_to_https=security_data["redirects_to_https"],
            cert_valid=security_data["cert_valid"],
            cert_expires_at=security_data["cert_expires_at"],
            cert_issuer=security_data["cert_issuer"],
            days_until_expiry=security_data["days_until_expiry"],
            headers=security_data["headers"],
            findings=security_data["findings"],
        )
        db.add(security)
    if (config is None or config.seo_enabled) and page.body:
        html = analyze_html(page, website.url)
        extra = check_robots_and_sitemap(page.final_url or website.url)
        html["findings"].extend(extra["findings"])
        seo = SeoResult(
            scan_job_id=job.id,
            website_id=website.id,
            checked_at=_now(),
            title=html["title"],
            meta_description=html["meta_description"],
            h1_count=html["h1_count"],
            canonical=html["canonical"],
            robots_txt_present=extra["robots_txt_present"],
            sitemap_present=extra["sitemap_present"],
            images_checked=html["images_checked"],
            images_missing_alt=html["images_missing_alt"],
            forms_missing_labels=html["forms_missing_labels"],
            broken_links=html["broken_links"],
            findings=html["findings"],
        )
        db.add(seo)
    if config is None or config.pagespeed_enabled:
        recent = db.scalars(
            select(PerformanceResult)
            .where(PerformanceResult.website_id == website.id, PerformanceResult.available.is_(True))
            .order_by(PerformanceResult.fetched_at.desc())
            .limit(1)
        ).first()
        if recent and recent.fetched_at > _now() - timedelta(hours=6):
            performance = recent
        else:
            for strategy in ("mobile", "desktop"):
                data = analyze_pagespeed(website.url, strategy)
                row = PerformanceResult(
                    scan_job_id=job.id,
                    website_id=website.id,
                    strategy=strategy,
                    fetched_at=_now(),
                    available=data["available"],
                    error_message=data["error_message"],
                    performance_score=data["performance_score"],
                    accessibility_score=data["accessibility_score"],
                    seo_score=data["seo_score"],
                    best_practices_score=data["best_practices_score"],
                    lcp_ms=data["lcp_ms"],
                    cls=data["cls"],
                    inp_ms=data["inp_ms"],
                    fcp_ms=data["fcp_ms"],
                    tbt_ms=data["tbt_ms"],
                    lcp_source=data["lcp_source"],
                    cls_source=data["cls_source"],
                    inp_source=data["inp_source"],
                    fcp_source=data["fcp_source"],
                    opportunities=data["opportunities"],
                )
                db.add(row)
                if strategy == "mobile":
                    performance = row
    previous_score = None
    if performance and performance.performance_score is not None:
        older = db.scalars(
            select(PerformanceResult)
            .where(
                PerformanceResult.website_id == website.id,
                PerformanceResult.strategy == "mobile",
                PerformanceResult.id != performance.id,
                PerformanceResult.performance_score.is_not(None),
            )
            .order_by(PerformanceResult.fetched_at.desc())
            .limit(1)
        ).first()
        if older:
            previous_score = older.performance_score
    detections = classify(
        view,
        previous_view,
        _baseline_ms(db, website.id),
        security.findings if security else [],
        performance.performance_score if performance else None,
        previous_score,
    )
    _store_anomalies(db, website, job, simulated=False)
    agent = _latest_agent_metric(db, website)
    for detection in detections:
        _upsert_incident(db, website, job, detection, security, performance, agent, simulated=False)
    if view.is_up and not any(item.category == "availability" for item in detections):
        _resolve_recovered(db, website, "availability")
    website.latest_status = "down" if confirmed and not view.is_up else ("degraded" if detections else ("healthy" if view.is_up else "unknown"))
    if not confirmed and not view.is_up:
        website.latest_status = "unknown"
    website.latest_checked_at = _now()


def _apply_synthetic(db: Session, website: Website, job: ScanJob, synthetic: dict) -> None:
    measurement = AvailabilityMeasurement(
        scan_job_id=job.id,
        website_id=website.id,
        checked_at=_now(),
        is_up=synthetic.get("is_up", True),
        confirmed_failure=True,
        http_status=synthetic.get("http_status"),
        response_time_ms=synthetic.get("response_time_ms"),
        error_type=synthetic.get("error_type"),
        error_message=synthetic.get("error_message"),
        final_url=website.url,
        redirect_count=0,
        dns_ok=synthetic.get("dns_ok", True),
        tls_valid=synthetic.get("tls_valid", True),
        is_simulated=True,
    )
    db.add(measurement)
    view = MeasurementView(
        is_up=measurement.is_up,
        http_status=measurement.http_status,
        response_time_ms=measurement.response_time_ms,
        error_type=measurement.error_type,
        error_message=measurement.error_message,
        dns_ok=measurement.dns_ok,
        tls_valid=measurement.tls_valid,
        confirmed_failure=True,
    )
    agent = synthetic.get("agent")
    detections = classify(view, view, synthetic.get("baseline_ms"), synthetic.get("security_findings") or [], None, None)
    if synthetic.get("category") == "resource":
        from app.services.detection.rules import Detection

        detections.append(
            Detection(
                category="resource",
                severity="high",
                title=synthetic.get("title", "Synthetic resource exhaustion"),
                symptoms=synthetic.get("symptoms") or ["Synthetic agent metrics crossed a resource threshold."],
                evidence=agent or {},
                fingerprint="resource-sim",
            )
        )
    for detection in detections:
        _upsert_incident(db, website, job, detection, None, None, agent, simulated=True)
    values = synthetic.get("series") or []
    if values:
        result, _blob = evaluate_series(values, synthetic.get("metric", "response_time_ms"), None)
        result.evidence["synthetic"] = True
        db.add(
            Anomaly(
                website_id=website.id,
                scan_job_id=job.id,
                metric=result.metric,
                record_type=result.record_type,
                method=result.method,
                model_trained=result.model_trained,
                score=result.score,
                is_anomaly=result.is_anomaly,
                value=result.value,
                baseline=result.baseline,
                evidence=result.evidence,
                is_simulated=True,
                detected_at=_now(),
            )
        )
    website.latest_status = "simulated"
    website.latest_checked_at = _now()


def _store_anomalies(db: Session, website: Website, job: ScanJob, simulated: bool) -> None:
    rows = db.scalars(
        select(AvailabilityMeasurement)
        .where(AvailabilityMeasurement.website_id == website.id, AvailabilityMeasurement.is_simulated.is_(False))
        .order_by(AvailabilityMeasurement.checked_at.asc())
        .limit(500)
    ).all()
    values = [row.response_time_ms for row in rows if row.response_time_ms is not None]
    if not values:
        return
    existing = db.scalars(select(MlModel).where(MlModel.website_id == website.id, MlModel.metric == "response_time_ms")).first()
    result, new_blob = evaluate_series(values, "response_time_ms", existing.model_blob if existing else None)
    if new_blob is not None:
        if existing:
            existing.model_blob = new_blob
            existing.sample_count = len(values)
            existing.trained_at = _now()
        else:
            db.add(MlModel(website_id=website.id, metric="response_time_ms", sample_count=len(values), model_blob=new_blob, trained_at=_now()))
    db.add(
        Anomaly(
            website_id=website.id,
            scan_job_id=job.id,
            metric=result.metric,
            record_type=result.record_type,
            method=result.method,
            model_trained=result.model_trained,
            score=result.score,
            is_anomaly=result.is_anomaly,
            value=result.value,
            baseline=result.baseline,
            evidence=result.evidence,
            is_simulated=simulated,
            detected_at=_now(),
        )
    )
    forecast = forecast_trend(values, "response_time_ms")
    if forecast:
        db.add(
            Anomaly(
                website_id=website.id,
                scan_job_id=job.id,
                metric=forecast.metric,
                record_type=forecast.record_type,
                method=forecast.method,
                model_trained=False,
                score=forecast.score,
                is_anomaly=False,
                value=forecast.value,
                baseline=forecast.baseline,
                evidence=forecast.evidence,
                is_simulated=simulated,
                detected_at=_now(),
            )
        )


def _latest_agent_metric(db: Session, website: Website) -> dict | None:
    agent = db.scalars(
        select(MonitoringAgent).where(
            MonitoringAgent.user_id == website.user_id,
            MonitoringAgent.revoked_at.is_(None),
            (MonitoringAgent.website_id == website.id) | (MonitoringAgent.website_id.is_(None)),
        )
    ).first()
    if agent is None:
        return None
    metric = db.scalars(select(AgentMetric).where(AgentMetric.agent_id == agent.id).order_by(AgentMetric.recorded_at.desc())).first()
    if metric is None:
        return None
    return {"cpu_percent": metric.cpu_percent, "memory_percent": metric.memory_percent, "disk_percent": metric.disk_percent}


def _upsert_incident(db: Session, website: Website, job: ScanJob, detection, security, performance, agent, simulated: bool) -> Incident:
    existing = db.scalars(
        select(Incident).where(
            Incident.website_id == website.id,
            Incident.fingerprint == detection.fingerprint,
            Incident.status.in_(["open", "acknowledged"]),
            Incident.is_simulated.is_(simulated),
        )
    ).first()
    if existing:
        db.add(IncidentEvent(incident_id=existing.id, event_type="correlated", message="A related signal was correlated into the open incident.", actor="detector"))
        existing.evidence = {**existing.evidence, "latest": detection.evidence}
        return existing
    incident = Incident(
        website_id=website.id,
        user_id=website.user_id,
        public_id=_public_id(),
        title=("[Synthetic] " if simulated else "") + detection.title,
        category=detection.category,
        severity=detection.severity,
        status="open",
        fingerprint=detection.fingerprint,
        detected_at=_now(),
        symptoms=detection.symptoms,
        evidence=detection.evidence,
        is_simulated=simulated,
        scan_job_id=job.id,
    )
    db.add(incident)
    db.flush()
    db.add(IncidentEvent(incident_id=incident.id, event_type="opened", message=detection.title, actor="detector"))
    security_payload = None
    if security is not None:
        security_payload = {"cert_valid": security.cert_valid, "days_until_expiry": security.days_until_expiry, "findings": security.findings}
    performance_payload = None
    if performance is not None and getattr(performance, "performance_score", None) is not None:
        performance_payload = {
            "performance_score": performance.performance_score,
            "lcp_ms": performance.lcp_ms,
            "lcp_source": performance.lcp_source,
        }
    rca = analyze_rca(
        {"title": incident.title, "category": incident.category, "evidence": incident.evidence},
        detection.evidence,
        security_payload,
        performance_payload,
        agent,
    )
    db.add(
        RcaAnalysis(
            incident_id=incident.id,
            observed_problem=rca["observed_problem"],
            hypotheses=rca["hypotheses"],
            verification_steps=rca["verification_steps"],
            recommended_actions=rca["recommended_actions"],
            preventive_measures=rca["preventive_measures"],
        )
    )
    insight = explain({**rca, "category": incident.category, "title": incident.title, "simulated": simulated})
    db.add(
        AiRecommendation(
            website_id=website.id,
            incident_id=incident.id,
            user_id=website.user_id,
            source=insight.source,
            kind="incident",
            content=insight.model_dump(),
            is_simulated=simulated,
        )
    )
    return incident


def _resolve_recovered(db: Session, website: Website, category: str) -> None:
    open_rows = db.scalars(
        select(Incident).where(
            Incident.website_id == website.id,
            Incident.category == category,
            Incident.status.in_(["open", "acknowledged"]),
            Incident.is_simulated.is_(False),
        )
    ).all()
    for incident in open_rows:
        incident.status = "resolved"
        incident.resolved_at = _now()
        db.add(IncidentEvent(incident_id=incident.id, event_type="resolved", message="A later check no longer confirmed this failure.", actor="detector"))
