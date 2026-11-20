import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import hash_token, new_token
from app.models import (
    AgentMetric,
    AiRecommendation,
    Anomaly,
    AvailabilityMeasurement,
    Incident,
    MonitoringAgent,
    Report,
    RcaAnalysis,
    ScanJob,
    SimulatorRun,
    User,
    Website,
)
from app.schemas.common import AgentCreate, AgentMetricIn, ReportRequest, SimulationRequest
from app.services.monitoring import run_scan
from app.services.simulator import SCENARIOS, scenario_catalog

router = APIRouter(tags=["platform"])


@router.get("/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    site_stmt = select(Website).where(Website.is_simulated.is_(False))
    if user.role != "admin":
        site_stmt = site_stmt.where(Website.user_id == user.id)
    sites = db.scalars(site_stmt).all()
    incident_stmt = select(Incident).where(Incident.status.in_(["open", "acknowledged"]), Incident.is_simulated.is_(False))
    if user.role != "admin":
        incident_stmt = incident_stmt.where(Incident.user_id == user.id)
    incidents = db.scalars(incident_stmt.order_by(Incident.detected_at.desc()).limit(8)).all()
    healthy = sum(1 for site in sites if site.latest_status == "healthy")
    issues = sum(1 for site in sites if site.latest_status in {"degraded", "down"})
    uptime_values = []
    series = []
    for site in sites:
        rows = db.scalars(
            select(AvailabilityMeasurement)
            .where(AvailabilityMeasurement.website_id == site.id, AvailabilityMeasurement.is_simulated.is_(False))
            .order_by(AvailabilityMeasurement.checked_at.desc())
            .limit(48)
        ).all()
        if rows:
            uptime_values.append(100 * sum(1 for row in rows if row.is_up) / len(rows))
            valid_points = [
                {"checked_at": row.checked_at, "response_time_ms": row.response_time_ms, "is_up": row.is_up}
                for row in reversed(rows)
                if row.response_time_ms is not None
            ]
            if valid_points:
                series.append(
                    {
                        "website": site.name,
                        "website_id": str(site.id),
                        "latest_response_time_ms": valid_points[-1]["response_time_ms"],
                        "points": valid_points,
                    }
                )
    return {
        "total_websites": len(sites),
        "healthy_websites": healthy,
        "websites_with_issues": issues,
        "unknown_websites": len(sites) - healthy - issues,
        "websites": [
            {
                "id": str(site.id),
                "name": site.name,
                "url": site.url,
                "latest_status": site.latest_status,
                "latest_checked_at": site.latest_checked_at,
            }
            for site in sites
        ],
        "active_incidents": len(incidents),
        "uptime_percent": round(sum(uptime_values) / len(uptime_values), 2) if uptime_values else None,
        "recent_incidents": [
            {
                "id": str(item.id),
                "public_id": item.public_id,
                "title": item.title,
                "severity": item.severity,
                "status": item.status,
                "is_simulated": item.is_simulated,
                "detected_at": item.detected_at,
            }
            for item in incidents
        ],
        "response_series": series,
        "message": None if sites else "Add a website to start monitoring. Charts stay empty until real scans exist.",
    }


@router.get("/insights")
def insights(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    stmt = select(AiRecommendation).order_by(AiRecommendation.created_at.desc()).limit(30)
    if user.role != "admin":
        stmt = stmt.where(AiRecommendation.user_id == user.id)
    rows = db.scalars(stmt).all()
    return [
        {
            "id": str(row.id),
            "source": row.source,
            "kind": row.kind,
            "content": row.content,
            "is_simulated": row.is_simulated,
            "created_at": row.created_at,
            "incident_id": str(row.incident_id) if row.incident_id else None,
            "website_id": str(row.website_id) if row.website_id else None,
        }
        for row in rows
    ]


@router.get("/analytics")
def analytics(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    site_stmt = select(Website).where(Website.is_simulated.is_(False))
    if user.role != "admin":
        site_stmt = site_stmt.where(Website.user_id == user.id)
    site_ids = [site.id for site in db.scalars(site_stmt).all()]
    if not site_ids:
        return {"anomalies": [], "forecasts": [], "message": "No measurements yet. Anomaly detection starts after scans are stored."}
    rows = db.scalars(select(Anomaly).where(Anomaly.website_id.in_(site_ids)).order_by(Anomaly.detected_at.desc()).limit(100)).all()
    return {
        "anomalies": [_anomaly(row) for row in rows if row.record_type == "anomaly"],
        "forecasts": [_anomaly(row) for row in rows if row.record_type == "forecast"],
        "message": "Forecasts appear only after at least 20 real response-time samples. Isolation Forest is marked trained only after the configured sample threshold.",
    }


def _anomaly(row: Anomaly) -> dict:
    return {
        "id": str(row.id),
        "website_id": str(row.website_id),
        "metric": row.metric,
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


@router.get("/simulator/scenarios")
def scenarios(user: User = Depends(get_current_user)) -> list[dict]:
    return scenario_catalog()


@router.post("/simulator/run")
def run_simulation(body: SimulationRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if body.scenario not in SCENARIOS:
        raise HTTPException(status_code=400, detail="Unknown scenario")
    website = Website(
        user_id=user.id,
        name=body.website_name or f"Synthetic {body.scenario}",
        url=f"https://simulation.invalid/{uuid.uuid4().hex}",
        hostname="simulation.invalid",
        monitoring_state="stopped",
        latest_status="simulated",
        is_simulated=True,
    )
    db.add(website)
    db.flush()
    job = run_scan(db, website, trigger="simulation", simulated=True, synthetic=SCENARIOS[body.scenario])
    incident = db.scalars(select(Incident).where(Incident.website_id == website.id).order_by(Incident.detected_at.desc())).first()
    run = SimulatorRun(
        user_id=user.id,
        scenario=body.scenario,
        status="completed",
        incident_id=incident.id if incident else None,
        result={"scan_id": str(job.id), "label": "synthetic", "note": "No live website was contacted."},
    )
    db.add(run)
    db.commit()
    return {"run_id": str(run.id), "website_id": str(website.id), "incident_id": str(incident.id) if incident else None, "label": "synthetic"}


@router.get("/simulator/runs")
def simulation_runs(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(SimulatorRun).where(SimulatorRun.user_id == user.id).order_by(SimulatorRun.created_at.desc()).limit(30)).all()
    return [
        {"id": str(row.id), "scenario": row.scenario, "status": row.status, "label": row.label, "incident_id": str(row.incident_id) if row.incident_id else None, "created_at": row.created_at, "result": row.result}
        for row in rows
    ]


@router.post("/reports")
def create_report(body: ReportRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    sites_stmt = select(Website).where(Website.is_simulated.is_(False))
    if body.website_id:
        sites_stmt = sites_stmt.where(Website.id == body.website_id)
    if user.role != "admin":
        sites_stmt = sites_stmt.where(Website.user_id == user.id)
    sites = db.scalars(sites_stmt).all()
    if body.website_id and not sites:
        raise HTTPException(status_code=404, detail="Website not found")
    sections = []
    for site in sites:
        points = db.scalars(
            select(AvailabilityMeasurement)
            .where(AvailabilityMeasurement.website_id == site.id, AvailabilityMeasurement.is_simulated.is_(False))
            .order_by(AvailabilityMeasurement.checked_at.desc())
            .limit(100)
        ).all()
        incidents = db.scalars(select(Incident).where(Incident.website_id == site.id).order_by(Incident.detected_at.desc()).limit(10)).all()
        scans = db.scalars(select(ScanJob).where(ScanJob.website_id == site.id).order_by(ScanJob.created_at.desc()).limit(20)).all()
        uptime = round(100 * sum(1 for point in points if point.is_up) / len(points), 2) if points else None
        rca_results = []
        ai_results = []
        for incident in incidents:
            rca = db.scalars(select(RcaAnalysis).where(RcaAnalysis.incident_id == incident.id).order_by(RcaAnalysis.created_at.desc())).first()
            ai = db.scalars(select(AiRecommendation).where(AiRecommendation.incident_id == incident.id).order_by(AiRecommendation.created_at.desc())).first()
            if rca:
                rca_results.append({"incident": incident.public_id, "observed_problem": rca.observed_problem, "hypotheses": rca.hypotheses, "recommended_actions": rca.recommended_actions, "preventive_measures": rca.preventive_measures})
            if ai:
                ai_results.append({"incident": incident.public_id, "source": ai.source, "content": ai.content})
        sections.append(
            {
                "website": site.name,
                "url": site.url,
                "status": site.latest_status,
                "latest_checked_at": site.latest_checked_at.isoformat() if site.latest_checked_at else None,
                "samples": len(points),
                "uptime_percent": uptime,
                "incidents": [{"public_id": item.public_id, "title": item.title, "severity": item.severity, "status": item.status, "symptoms": item.symptoms, "simulated": item.is_simulated} for item in incidents],
                "recent_scans": [{"status": scan.status, "trigger": scan.trigger, "created_at": scan.created_at.isoformat() if scan.created_at else None, "simulated": scan.is_simulated} for scan in scans],
                "rca": rca_results,
                "ai_insights": ai_results,
            }
        )
    report = Report(user_id=user.id, website_id=body.website_id, title=body.title or "Website health report", content={"generated_at": datetime.now(UTC).isoformat(), "sections": sections})
    db.add(report)
    db.commit()
    db.refresh(report)
    return {"id": str(report.id), "title": report.title, "created_at": report.created_at, "content": report.content}


@router.get("/reports")
def list_reports(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Report).where(Report.user_id == user.id).order_by(Report.created_at.desc()).limit(30)).all()
    return [{"id": str(row.id), "title": row.title, "created_at": row.created_at, "website_id": str(row.website_id) if row.website_id else None} for row in rows]


@router.get("/reports/{report_id}")
def get_report(report_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    row = db.get(Report, report_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"id": str(row.id), "title": row.title, "created_at": row.created_at, "content": row.content}


@router.post("/agents", status_code=201)
def create_agent(body: AgentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if body.website_id:
        site = db.get(Website, body.website_id)
        if site is None or (site.user_id != user.id and user.role != "admin"):
            raise HTTPException(status_code=404, detail="Website not found")
    token = new_token()
    agent = MonitoringAgent(user_id=user.id, website_id=body.website_id, name=body.name.strip(), token_hash=hash_token(token))
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return {"id": str(agent.id), "name": agent.name, "token": token, "note": "Store this token now. It is only shown once."}


@router.get("/agents")
def list_agents(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(MonitoringAgent).where(MonitoringAgent.user_id == user.id).order_by(MonitoringAgent.created_at.desc())).all()
    return [
        {"id": str(row.id), "name": row.name, "website_id": str(row.website_id) if row.website_id else None, "last_seen_at": row.last_seen_at, "revoked": row.revoked_at is not None}
        for row in rows
    ]


@router.post("/agents/{agent_id}/rotate")
def rotate_agent(agent_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    agent = db.get(MonitoringAgent, agent_id)
    if agent is None or agent.user_id != user.id:
        raise HTTPException(status_code=404, detail="Agent not found")
    token = new_token()
    agent.token_hash = hash_token(token)
    agent.revoked_at = None
    db.commit()
    return {"id": str(agent.id), "token": token}


@router.post("/agents/{agent_id}/revoke")
def revoke_agent(agent_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    agent = db.get(MonitoringAgent, agent_id)
    if agent is None or agent.user_id != user.id:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.revoked_at = datetime.now(UTC)
    db.commit()
    return {"detail": "Agent revoked"}


@router.post("/agents/ingest")
def ingest(body: AgentMetricIn, authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Agent token is required")
    token = authorization.split(" ", 1)[1].strip()
    agent = db.scalars(select(MonitoringAgent).where(MonitoringAgent.token_hash == hash_token(token))).first()
    if agent is None or agent.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Agent token is invalid")
    metric = AgentMetric(
        agent_id=agent.id,
        website_id=agent.website_id,
        recorded_at=body.recorded_at or datetime.now(UTC),
        cpu_percent=body.cpu_percent,
        memory_percent=body.memory_percent,
        disk_percent=body.disk_percent,
        network=body.network,
        processes=body.processes[:20],
        logs=[item[:500] for item in body.logs[:50]],
    )
    agent.last_seen_at = datetime.now(UTC)
    db.add(metric)
    db.commit()
    _maybe_resource_incident(db, agent, metric)
    return {"detail": "Metric stored"}


def _maybe_resource_incident(db: Session, agent: MonitoringAgent, metric: AgentMetric) -> None:
    if agent.website_id is None:
        return
    breached = []
    if (metric.cpu_percent or 0) >= 95:
        breached.append("cpu")
    if (metric.memory_percent or 0) >= 95:
        breached.append("memory")
    if (metric.disk_percent or 0) >= 95:
        breached.append("disk")
    if not breached:
        return
    website = db.get(Website, agent.website_id)
    if website is None:
        return
    from app.models import ScanJob
    from app.services.detection.rules import Detection
    from app.services.monitoring import _upsert_incident

    job = ScanJob(website_id=website.id, user_id=website.user_id, trigger="agent", status="succeeded", started_at=datetime.now(UTC), finished_at=datetime.now(UTC))
    db.add(job)
    db.flush()
    detection = Detection(
        category="resource",
        severity="high",
        title="Agent reported resource exhaustion",
        symptoms=[f"Agent {agent.name} reported high {', '.join(breached)} usage."],
        evidence={"cpu_percent": metric.cpu_percent, "memory_percent": metric.memory_percent, "disk_percent": metric.disk_percent},
        fingerprint="agent-resource",
    )
    _upsert_incident(db, website, job, detection, None, None, detection.evidence, simulated=False)
    db.commit()


@router.get("/health/deps")
def dependency_health() -> dict:
    redis_ok = False
    try:
        import redis

        client = redis.Redis.from_url(get_settings_safe(), socket_connect_timeout=1)
        redis_ok = bool(client.ping())
    except Exception:
        redis_ok = False
    return {"redis": redis_ok}


def get_settings_safe() -> str:
    from app.core.config import get_settings

    return get_settings().redis_url
