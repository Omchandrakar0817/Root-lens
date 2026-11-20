import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import AiRecommendation, Incident, IncidentEvent, RcaAnalysis, User
from app.services.ai.gemini import explain

router = APIRouter(prefix="/incidents", tags=["incidents"])


def _load(db: Session, incident_id: uuid.UUID, user: User) -> Incident:
    row = db.get(Incident, incident_id)
    if row is None or (row.user_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Incident not found")
    return row


def _detail(db: Session, row: Incident) -> dict:
    events = db.scalars(select(IncidentEvent).where(IncidentEvent.incident_id == row.id).order_by(IncidentEvent.created_at.asc())).all()
    rca = db.scalars(select(RcaAnalysis).where(RcaAnalysis.incident_id == row.id).order_by(RcaAnalysis.created_at.desc())).first()
    ai = db.scalars(select(AiRecommendation).where(AiRecommendation.incident_id == row.id).order_by(AiRecommendation.created_at.desc())).first()
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
        "evidence": row.evidence,
        "scan_job_id": str(row.scan_job_id) if row.scan_job_id else None,
        "timeline": [{"event_type": event.event_type, "message": event.message, "created_at": event.created_at, "actor": event.actor} for event in events],
        "rca": None
        if rca is None
        else {
            "observed_problem": rca.observed_problem,
            "hypotheses": rca.hypotheses,
            "verification_steps": rca.verification_steps,
            "recommended_actions": rca.recommended_actions,
            "preventive_measures": rca.preventive_measures,
            "created_at": rca.created_at,
        },
        "ai": None if ai is None else {"source": ai.source, "content": ai.content, "created_at": ai.created_at},
    }


@router.get("")
def list_incidents(severity: str | None = None, status: str | None = None, simulated: bool | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    stmt = select(Incident).order_by(Incident.detected_at.desc()).limit(100)
    if user.role != "admin":
        stmt = stmt.where(Incident.user_id == user.id)
    if severity:
        stmt = stmt.where(Incident.severity == severity)
    if status:
        stmt = stmt.where(Incident.status == status)
    if simulated is not None:
        stmt = stmt.where(Incident.is_simulated.is_(simulated))
    rows = db.scalars(stmt).all()
    return [
        {
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
        for row in rows
    ]


@router.get("/{incident_id}")
def get_incident(incident_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return _detail(db, _load(db, incident_id, user))


def _set_status(db: Session, row: Incident, status_value: str, message: str) -> dict:
    row.status = status_value
    if status_value == "resolved":
        row.resolved_at = datetime.now(UTC)
    if status_value == "open":
        row.resolved_at = None
    db.add(IncidentEvent(incident_id=row.id, event_type=status_value, message=message, actor="user"))
    db.commit()
    return _detail(db, row)


@router.post("/{incident_id}/acknowledge")
def acknowledge(incident_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return _set_status(db, _load(db, incident_id, user), "acknowledged", "Incident acknowledged.")


@router.post("/{incident_id}/resolve")
def resolve(incident_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return _set_status(db, _load(db, incident_id, user), "resolved", "Incident resolved by the user.")


@router.post("/{incident_id}/reopen")
def reopen(incident_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return _set_status(db, _load(db, incident_id, user), "open", "Incident reopened.")


@router.post("/{incident_id}/ai")
def refresh_ai(incident_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    row = _load(db, incident_id, user)
    rca = db.scalars(select(RcaAnalysis).where(RcaAnalysis.incident_id == row.id).order_by(RcaAnalysis.created_at.desc())).first()
    evidence = {
        "title": row.title,
        "category": row.category,
        "symptoms": row.symptoms,
        "evidence": row.evidence,
        "hypotheses": rca.hypotheses if rca else [],
        "verification_steps": rca.verification_steps if rca else [],
        "preventive_measures": rca.preventive_measures if rca else [],
        "simulated": row.is_simulated,
    }
    insight = explain(evidence)
    saved = AiRecommendation(
        website_id=row.website_id,
        incident_id=row.id,
        user_id=row.user_id,
        source=insight.source,
        kind="incident",
        content=insight.model_dump(),
        is_simulated=row.is_simulated,
    )
    db.add(saved)
    db.commit()
    return {"source": insight.source, "content": insight.model_dump()}
