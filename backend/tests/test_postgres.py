"""
PostgreSQL integration tests.

These tests run ONLY when DATABASE_URL points at a real PostgreSQL server.
They are automatically skipped when using the default SQLite test URL or when
Postgres is not reachable.

Run with real Postgres:
    DATABASE_URL=postgresql+psycopg://... python -m pytest tests/test_postgres.py -v
"""
from __future__ import annotations

import os
import uuid
import pytest
from datetime import UTC, datetime, timedelta

# ── Skip if not targeting a real Postgres ──────────────────────────────────
_DB_URL = os.environ.get("DATABASE_URL", "")
_IS_PG = _DB_URL.startswith("postgresql")

pytestmark = pytest.mark.skipif(
    not _IS_PG,
    reason="Set DATABASE_URL=postgresql+psycopg://... to run PostgreSQL integration tests",
)


@pytest.fixture(scope="module")
def pg_engine():
    """Create a test-scoped engine that uses a fresh schema."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool

    engine = create_engine(_DB_URL, poolclass=NullPool)
    # Verify connectivity first
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL not reachable: {exc}")

    # Create all tables
    from app.models import Base
    Base.metadata.create_all(bind=engine)
    yield engine
    # Drop test data but keep schema (non-destructive)


@pytest.fixture()
def pg_session(pg_engine):
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    db = Session()
    yield db
    db.rollback()
    db.close()


# ── Tests ──────────────────────────────────────────────────────────────────

def test_pg_connectivity(pg_engine):
    from sqlalchemy import text, inspect
    with pg_engine.connect() as conn:
        version = conn.execute(text("SELECT version()")).scalar()
    assert "PostgreSQL" in version


def test_all_tables_created(pg_engine):
    from sqlalchemy import inspect
    inspector = inspect(pg_engine)
    tables = set(inspector.get_table_names())
    required = {
        "users", "refresh_tokens", "websites", "monitoring_configs",
        "monitoring_schedules", "scan_jobs", "availability_measurements",
        "performance_results", "security_results", "seo_results",
        "incidents", "incident_events", "anomalies", "ml_models",
        "rca_analyses", "ai_recommendations", "reports",
        "monitoring_agents", "agent_metrics", "simulator_runs",
    }
    missing = required - tables
    assert not missing, f"Missing tables: {missing}"


def test_user_create_and_retrieve(pg_session):
    from app.models import User
    from app.core.security import hash_password
    unique_email = f"pgtest_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=unique_email,
        password_hash=hash_password("testpass123"),
        full_name="PG Test User",
        role="user",
    )
    pg_session.add(user)
    pg_session.commit()

    fetched = pg_session.get(User, user.id)
    assert fetched is not None
    assert fetched.email == unique_email
    assert fetched.role == "user"


def test_website_create_with_config(pg_session):
    from app.models import User, Website, MonitoringConfig, MonitoringSchedule
    from app.core.security import hash_password
    user = User(
        email=f"ws_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("pass"),
        full_name="WS User",
        role="user",
    )
    pg_session.add(user)
    pg_session.flush()

    website = Website(
        user_id=user.id,
        name="Test Site",
        url="https://example.com/",
        hostname="example.com",
        monitoring_state="paused",
    )
    pg_session.add(website)
    pg_session.flush()

    config = MonitoringConfig(website_id=website.id, interval_seconds=900)
    pg_session.add(config)
    schedule = MonitoringSchedule(
        website_id=website.id,
        next_run_at=datetime.now(UTC) + timedelta(days=365),
    )
    pg_session.add(schedule)
    pg_session.commit()

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    ws = pg_session.scalars(
        select(Website).options(selectinload(Website.config)).where(Website.id == website.id)
    ).one()
    assert ws.config.interval_seconds == 900


def test_incident_and_rca_persistence(pg_session):
    from app.models import User, Website, ScanJob, Incident, RcaAnalysis
    from app.core.security import hash_password

    user = User(
        email=f"inc_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("pass"),
        full_name="Inc User",
        role="user",
    )
    pg_session.add(user)
    pg_session.flush()

    website = Website(
        user_id=user.id, name="Inc Site",
        url="https://inctest.example.com/",
        hostname="inctest.example.com",
        monitoring_state="paused",
    )
    pg_session.add(website)
    pg_session.flush()

    job = ScanJob(
        website_id=website.id, user_id=user.id,
        trigger="manual", status="succeeded",
        started_at=datetime.now(UTC), finished_at=datetime.now(UTC),
    )
    pg_session.add(job)
    pg_session.flush()

    incident = Incident(
        website_id=website.id, user_id=user.id,
        public_id=f"INC-{uuid.uuid4().hex[:8].upper()}",
        title="Test availability failure",
        category="availability", severity="critical",
        status="open",
        fingerprint="availability",
        detected_at=datetime.now(UTC),
        symptoms=["Site not reachable"],
        evidence={"error_type": "connection"},
        scan_job_id=job.id,
    )
    pg_session.add(incident)
    pg_session.flush()

    rca = RcaAnalysis(
        incident_id=incident.id,
        observed_problem="Connection failed on consecutive checks",
        hypotheses=[{"title": "Network issue", "confidence": "medium", "status": "hypothesis"}],
        verification_steps=["Check from another network"],
        recommended_actions=["Review firewall"],
        preventive_measures=["Automate cert renewal"],
    )
    pg_session.add(rca)
    pg_session.commit()

    from sqlalchemy import select
    fetched_rca = pg_session.scalars(
        select(RcaAnalysis).where(RcaAnalysis.incident_id == incident.id)
    ).first()
    assert fetched_rca is not None
    assert fetched_rca.hypotheses[0]["title"] == "Network issue"


def test_data_isolation_between_users(pg_session):
    """User A cannot see User B's websites via the ownership check."""
    from app.models import User, Website
    from app.core.security import hash_password
    from sqlalchemy import select

    user_a = User(
        email=f"a_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("pass"), full_name="A", role="user",
    )
    user_b = User(
        email=f"b_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("pass"), full_name="B", role="user",
    )
    pg_session.add_all([user_a, user_b])
    pg_session.flush()

    site_a = Website(
        user_id=user_a.id, name="A's site",
        url=f"https://{uuid.uuid4().hex[:8]}.example.com/",
        hostname="a.example.com", monitoring_state="paused",
    )
    pg_session.add(site_a)
    pg_session.commit()

    # B should see zero websites
    rows = pg_session.scalars(
        select(Website).where(Website.user_id == user_b.id)
    ).all()
    assert len(rows) == 0

    # A should see exactly their website
    rows_a = pg_session.scalars(
        select(Website).where(Website.user_id == user_a.id)
    ).all()
    assert len(rows_a) == 1
    assert rows_a[0].id == site_a.id


def test_jsonb_columns_store_and_query(pg_session):
    """JSONB columns work correctly on real PostgreSQL."""
    from app.models import User, Website, ScanJob, Incident
    from app.core.security import hash_password
    from sqlalchemy import select

    user = User(
        email=f"json_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("pass"), full_name="JSON User", role="user",
    )
    pg_session.add(user)
    pg_session.flush()

    website = Website(
        user_id=user.id, name="JSON Site",
        url=f"https://json{uuid.uuid4().hex[:8]}.example.com/",
        hostname="json.example.com", monitoring_state="paused",
    )
    pg_session.add(website)
    pg_session.flush()

    job = ScanJob(
        website_id=website.id, user_id=user.id,
        trigger="manual", status="succeeded",
        started_at=datetime.now(UTC), finished_at=datetime.now(UTC),
    )
    pg_session.add(job)
    pg_session.flush()

    evidence_payload = {
        "error_type": "dns",
        "confirmed": True,
        "nested": {"value": 42, "list": [1, 2, 3]},
    }
    incident = Incident(
        website_id=website.id, user_id=user.id,
        public_id=f"INC-{uuid.uuid4().hex[:8].upper()}",
        title="DNS failure",
        category="dns", severity="critical",
        status="open", fingerprint="dns",
        detected_at=datetime.now(UTC),
        symptoms=["DNS failed on consecutive checks"],
        evidence=evidence_payload,
        scan_job_id=job.id,
    )
    pg_session.add(incident)
    pg_session.commit()

    fetched = pg_session.get(Incident, incident.id)
    assert fetched.evidence["error_type"] == "dns"
    assert fetched.evidence["nested"]["value"] == 42
    assert fetched.symptoms[0].startswith("DNS")


def test_indexes_exist(pg_engine):
    """Spot-check that key performance indexes were created."""
    from sqlalchemy import inspect, text
    with pg_engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT indexname FROM pg_indexes WHERE tablename IN "
            "('availability_measurements','incidents','anomalies','monitoring_schedules')"
        )).fetchall()
    index_names = {row[0] for row in rows}
    assert any("availability" in n for n in index_names), f"Missing availability index: {index_names}"
    assert any("incidents" in n or "incident" in n for n in index_names), f"Missing incident index: {index_names}"
