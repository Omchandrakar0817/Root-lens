import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB as _PgJSONB
from sqlalchemy.dialects.postgresql import UUID as _PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.models.base import Base, TimestampMixin, UUIDMixin


class _JSONB(TypeDecorator):  # type: ignore[misc]
    """JSONB on PostgreSQL, JSON elsewhere (e.g. SQLite for tests)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_PgJSONB())
        return dialect.type_descriptor(JSON())


class _UUIDType(TypeDecorator):  # type: ignore[misc]
    """Native UUID on PostgreSQL, VARCHAR(36) elsewhere."""

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_PgUUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        import uuid as _uuid_mod
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        import uuid as _uuid_mod
        if dialect.name != "postgresql" and isinstance(value, str):
            try:
                return _uuid_mod.UUID(value)
            except ValueError:
                return value
        return value


def _UUID():  # noqa: N802
    return _UUIDType()


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    theme: Mapped[str] = mapped_column(String(20), nullable=False, default="system")

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    websites: Mapped[list["Website"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class RefreshToken(UUIDMixin, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(_UUID())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="refresh_tokens")

    __table_args__ = (Index("ix_refresh_tokens_user_id", "user_id"),)


class Website(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "websites"

    user_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    monitoring_state: Mapped[str] = mapped_column(String(20), nullable=False, default="paused")
    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    latest_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    latest_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="websites")
    config: Mapped["MonitoringConfig | None"] = relationship(back_populates="website", cascade="all, delete-orphan", uselist=False)
    schedule: Mapped["MonitoringSchedule | None"] = relationship(back_populates="website", cascade="all, delete-orphan", uselist=False)

    __table_args__ = (
        UniqueConstraint("user_id", "url", name="uq_websites_user_url"),
        Index("ix_websites_user_id", "user_id"),
    )


class MonitoringConfig(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "monitoring_configs"

    website_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("websites.id", ondelete="CASCADE"), unique=True, nullable=False)
    interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=900)
    pagespeed_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    security_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    seo_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    website: Mapped[Website] = relationship(back_populates="config")


class MonitoringSchedule(UUIDMixin, Base):
    __tablename__ = "monitoring_schedules"

    website_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("websites.id", ondelete="CASCADE"), unique=True, nullable=False)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(80))
    lease_token: Mapped[str | None] = mapped_column(String(64))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str | None] = mapped_column(String(40))
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    website: Mapped[Website] = relationship(back_populates="schedule")

    __table_args__ = (Index("ix_monitoring_schedules_due", "next_run_at", "locked_until"),)


class ScanJob(UUIDMixin, Base):
    __tablename__ = "scan_jobs"

    website_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("websites.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    trigger: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_scan_jobs_website_created", "website_id", "created_at"),
        Index("ix_scan_jobs_user_created", "user_id", "created_at"),
    )


class AvailabilityMeasurement(UUIDMixin, Base):
    __tablename__ = "availability_measurements"

    scan_job_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=False)
    website_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("websites.id", ondelete="CASCADE"), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_up: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confirmed_failure: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    response_time_ms: Mapped[float | None] = mapped_column(Float)
    error_type: Mapped[str | None] = mapped_column(String(40))
    error_message: Mapped[str | None] = mapped_column(Text)
    final_url: Mapped[str | None] = mapped_column(String(500))
    redirect_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dns_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tls_valid: Mapped[bool | None] = mapped_column(Boolean)
    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (Index("ix_availability_website_time", "website_id", "checked_at"),)


class PerformanceResult(UUIDMixin, Base):
    __tablename__ = "performance_results"

    scan_job_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=False)
    website_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("websites.id", ondelete="CASCADE"), nullable=False)
    strategy: Mapped[str] = mapped_column(String(20), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    performance_score: Mapped[float | None] = mapped_column(Float)
    accessibility_score: Mapped[float | None] = mapped_column(Float)
    seo_score: Mapped[float | None] = mapped_column(Float)
    best_practices_score: Mapped[float | None] = mapped_column(Float)
    lcp_ms: Mapped[float | None] = mapped_column(Float)
    cls: Mapped[float | None] = mapped_column(Float)
    inp_ms: Mapped[float | None] = mapped_column(Float)
    fcp_ms: Mapped[float | None] = mapped_column(Float)
    tbt_ms: Mapped[float | None] = mapped_column(Float)
    lcp_source: Mapped[str | None] = mapped_column(String(20))
    cls_source: Mapped[str | None] = mapped_column(String(20))
    inp_source: Mapped[str | None] = mapped_column(String(20))
    fcp_source: Mapped[str | None] = mapped_column(String(20))
    opportunities: Mapped[list] = mapped_column(_JSONB, nullable=False, default=list)
    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (Index("ix_performance_website_time", "website_id", "fetched_at"),)


class SecurityResult(UUIDMixin, Base):
    __tablename__ = "security_results"

    scan_job_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=False)
    website_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("websites.id", ondelete="CASCADE"), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    https_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    redirects_to_https: Mapped[bool | None] = mapped_column(Boolean)
    cert_valid: Mapped[bool | None] = mapped_column(Boolean)
    cert_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cert_issuer: Mapped[str | None] = mapped_column(String(255))
    days_until_expiry: Mapped[int | None] = mapped_column(Integer)
    headers: Mapped[dict] = mapped_column(_JSONB, nullable=False, default=dict)
    findings: Mapped[list] = mapped_column(_JSONB, nullable=False, default=list)
    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class SeoResult(UUIDMixin, Base):
    __tablename__ = "seo_results"

    scan_job_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=False)
    website_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("websites.id", ondelete="CASCADE"), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title: Mapped[str | None] = mapped_column(String(300))
    meta_description: Mapped[str | None] = mapped_column(Text)
    h1_count: Mapped[int | None] = mapped_column(Integer)
    canonical: Mapped[str | None] = mapped_column(String(500))
    robots_txt_present: Mapped[bool | None] = mapped_column(Boolean)
    sitemap_present: Mapped[bool | None] = mapped_column(Boolean)
    images_checked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    images_missing_alt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    forms_missing_labels: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    broken_links: Mapped[list] = mapped_column(_JSONB, nullable=False, default=list)
    findings: Mapped[list] = mapped_column(_JSONB, nullable=False, default=list)
    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Incident(UUIDMixin, Base):
    __tablename__ = "incidents"

    website_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("websites.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    public_id: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    fingerprint: Mapped[str] = mapped_column(String(120), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    symptoms: Mapped[list] = mapped_column(_JSONB, nullable=False, default=list)
    evidence: Mapped[dict] = mapped_column(_JSONB, nullable=False, default=dict)
    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scan_job_id: Mapped[uuid.UUID | None] = mapped_column(_UUID(), ForeignKey("scan_jobs.id", ondelete="SET NULL"))

    __table_args__ = (
        Index("ix_incidents_user_status", "user_id", "status"),
        Index("ix_incidents_fingerprint", "website_id", "fingerprint", "status"),
    )


class IncidentEvent(UUIDMixin, Base):
    __tablename__ = "incident_events"

    incident_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actor: Mapped[str] = mapped_column(String(80), nullable=False, default="system")

    __table_args__ = (Index("ix_incident_events_incident", "incident_id", "created_at"),)


class Anomaly(UUIDMixin, Base):
    __tablename__ = "anomalies"

    website_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("websites.id", ondelete="CASCADE"), nullable=False)
    scan_job_id: Mapped[uuid.UUID | None] = mapped_column(_UUID(), ForeignKey("scan_jobs.id", ondelete="SET NULL"))
    metric: Mapped[str] = mapped_column(String(40), nullable=False)
    record_type: Mapped[str] = mapped_column(String(20), nullable=False)
    method: Mapped[str] = mapped_column(String(40), nullable=False)
    model_trained: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    score: Mapped[float | None] = mapped_column(Float)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    value: Mapped[float | None] = mapped_column(Float)
    baseline: Mapped[float | None] = mapped_column(Float)
    evidence: Mapped[dict] = mapped_column(_JSONB, nullable=False, default=dict)
    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_anomalies_website_time", "website_id", "detected_at"),)


class MlModel(UUIDMixin, Base):
    __tablename__ = "ml_models"

    website_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("websites.id", ondelete="CASCADE"), nullable=False)
    metric: Mapped[str] = mapped_column(String(40), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    model_blob: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("website_id", "metric", name="uq_ml_models_website_metric"),)


class RcaAnalysis(UUIDMixin, Base):
    __tablename__ = "rca_analyses"

    incident_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    observed_problem: Mapped[str] = mapped_column(Text, nullable=False)
    hypotheses: Mapped[list] = mapped_column(_JSONB, nullable=False, default=list)
    verification_steps: Mapped[list] = mapped_column(_JSONB, nullable=False, default=list)
    recommended_actions: Mapped[list] = mapped_column(_JSONB, nullable=False, default=list)
    preventive_measures: Mapped[list] = mapped_column(_JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_rca_incident", "incident_id"),)


class AiRecommendation(UUIDMixin, Base):
    __tablename__ = "ai_recommendations"

    website_id: Mapped[uuid.UUID | None] = mapped_column(_UUID(), ForeignKey("websites.id", ondelete="CASCADE"))
    incident_id: Mapped[uuid.UUID | None] = mapped_column(_UUID(), ForeignKey("incidents.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    content: Mapped[dict] = mapped_column(_JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Report(UUIDMixin, Base):
    __tablename__ = "reports"

    user_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    website_id: Mapped[uuid.UUID | None] = mapped_column(_UUID(), ForeignKey("websites.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[dict] = mapped_column(_JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MonitoringAgent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "monitoring_agents"

    user_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    website_id: Mapped[uuid.UUID | None] = mapped_column(_UUID(), ForeignKey("websites.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AgentMetric(UUIDMixin, Base):
    __tablename__ = "agent_metrics"

    agent_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("monitoring_agents.id", ondelete="CASCADE"), nullable=False)
    website_id: Mapped[uuid.UUID | None] = mapped_column(_UUID(), ForeignKey("websites.id", ondelete="SET NULL"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cpu_percent: Mapped[float | None] = mapped_column(Float)
    memory_percent: Mapped[float | None] = mapped_column(Float)
    disk_percent: Mapped[float | None] = mapped_column(Float)
    network: Mapped[dict] = mapped_column(_JSONB, nullable=False, default=dict)
    processes: Mapped[list] = mapped_column(_JSONB, nullable=False, default=list)
    logs: Mapped[list] = mapped_column(_JSONB, nullable=False, default=list)

    __table_args__ = (Index("ix_agent_metrics_agent_time", "agent_id", "recorded_at"),)


class SimulatorRun(UUIDMixin, Base):
    __tablename__ = "simulator_runs"

    user_id: Mapped[uuid.UUID] = mapped_column(_UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    scenario: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(40), nullable=False, default="synthetic")
    incident_id: Mapped[uuid.UUID | None] = mapped_column(_UUID(), ForeignKey("incidents.id", ondelete="SET NULL"))
    result: Mapped[dict] = mapped_column(_JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
