"""API-level integration tests using FastAPI's TestClient with SQLite.

DATABASE_URL is set to sqlite:// BEFORE any app module is imported so that
the SQLAlchemy engine (created at module level in database.py) uses SQLite.
"""
from __future__ import annotations

import os

# Must be first — before ANY app import — so get_settings picks it up.
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-at-least-32-chars-long")
os.environ.setdefault("JWT_REFRESH_SECRET", "test-refresh-secret-at-least-32-chars")
os.environ["DATABASE_URL"] = "sqlite://"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

# Clear the lru_cache on Settings so the overridden DATABASE_URL is used.
from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.core.database import get_db, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

# The engine in database.py is now SQLite because of the env override above.
# We just override get_db to use the same SessionLocal (which wraps the SQLite engine).


def _override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def reset_db():
    """Recreate tables before each test to guarantee a clean state."""
    from app.core.database import engine as _engine  # import here after cache_clear
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REGISTER_PAYLOAD = {"full_name": "Test User", "email": "test@example.com", "password": "supersecret"}


def _register(client: TestClient, payload: dict | None = None) -> dict:
    r = client.post("/api/v1/auth/register", json=payload or REGISTER_PAYLOAD)
    assert r.status_code == 201, r.text
    return r.json()


def _auth(session: dict) -> dict:
    return {"Authorization": f"Bearer {session['access_token']}"}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_register_creates_user(client):
    body = _register(client)
    assert body["user"]["email"] == "test@example.com"
    assert "access_token" in body
    assert "refresh_token" in body


def test_duplicate_registration_is_rejected(client):
    _register(client)
    r = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert r.status_code == 409


def test_login_valid_credentials(client):
    _register(client)
    r = client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "supersecret"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password(client):
    _register(client)
    r = client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "wrongpass"})
    assert r.status_code == 401


def test_refresh_token_rotation(client):
    session = _register(client)
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert r.status_code == 200
    new_session = r.json()
    # Refresh token must be rotated (new value)
    assert new_session["refresh_token"] != session["refresh_token"]
    # Old refresh token must now be invalid
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert r2.status_code == 401


def test_me_requires_auth(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_me_returns_profile(client):
    session = _register(client)
    r = client.get("/api/v1/auth/me", headers=_auth(session))
    assert r.status_code == 200
    assert r.json()["email"] == "test@example.com"


def test_update_profile(client):
    session = _register(client)
    r = client.patch("/api/v1/auth/me", json={"full_name": "Updated Name"}, headers=_auth(session))
    assert r.status_code == 200
    assert r.json()["full_name"] == "Updated Name"


def test_logout(client):
    session = _register(client)
    r = client.post("/api/v1/auth/logout", json={"refresh_token": session["refresh_token"]}, headers=_auth(session))
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Websites
# ---------------------------------------------------------------------------


def test_list_websites_empty(client):
    session = _register(client)
    r = client.get("/api/v1/websites", headers=_auth(session))
    assert r.status_code == 200
    assert r.json() == []


def test_create_website(client):
    session = _register(client)
    r = client.post("/api/v1/websites", json={"name": "Example", "url": "https://example.com"}, headers=_auth(session))
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Example"
    assert body["url"] == "https://example.com/"


def test_reject_private_url(client):
    session = _register(client)
    r = client.post("/api/v1/websites", json={"name": "Local", "url": "http://127.0.0.1/"}, headers=_auth(session))
    assert r.status_code == 400


def test_reject_duplicate_url(client):
    session = _register(client)
    client.post("/api/v1/websites", json={"name": "Example", "url": "https://example.com"}, headers=_auth(session))
    r = client.post("/api/v1/websites", json={"name": "Example 2", "url": "https://example.com"}, headers=_auth(session))
    assert r.status_code == 409


def test_delete_website(client):
    session = _register(client)
    created = client.post("/api/v1/websites", json={"name": "To delete", "url": "https://delete.example.com"}, headers=_auth(session)).json()
    r = client.delete(f"/api/v1/websites/{created['id']}", headers=_auth(session))
    assert r.status_code == 200
    listing = client.get("/api/v1/websites", headers=_auth(session)).json()
    assert all(item["id"] != created["id"] for item in listing)


def test_cannot_access_another_users_website(client):
    s1 = _register(client)
    s2 = _register(client, {"full_name": "User 2", "email": "user2@example.com", "password": "supersecret"})
    site = client.post("/api/v1/websites", json={"name": "Mine", "url": "https://mine.example.com"}, headers=_auth(s1)).json()
    r = client.get(f"/api/v1/websites/{site['id']}", headers=_auth(s2))
    assert r.status_code == 404


def test_website_monitoring_toggle(client):
    session = _register(client)
    site = client.post("/api/v1/websites", json={"name": "W", "url": "https://monitor.example.com"}, headers=_auth(session)).json()
    r = client.post(f"/api/v1/websites/{site['id']}/monitoring", json={"state": "active"}, headers=_auth(session))
    assert r.status_code == 200
    assert r.json()["detail"] == "Monitoring is active"


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------


def test_list_incidents_empty(client):
    session = _register(client)
    r = client.get("/api/v1/incidents", headers=_auth(session))
    assert r.status_code == 200
    assert r.json() == []


def test_incident_filters_accepted(client):
    session = _register(client)
    # Creating a synthetic incident via simulator first
    client.post("/api/v1/simulator/run", json={"scenario": "website_downtime"}, headers=_auth(session))
    r = client.get("/api/v1/incidents?status=open", headers=_auth(session))
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Dashboard and analytics
# ---------------------------------------------------------------------------


def test_dashboard_no_data(client):
    session = _register(client)
    r = client.get("/api/v1/dashboard", headers=_auth(session))
    assert r.status_code == 200
    body = r.json()
    assert body["total_websites"] == 0
    assert body["active_incidents"] == 0


def test_analytics_no_data(client):
    session = _register(client)
    r = client.get("/api/v1/analytics", headers=_auth(session))
    assert r.status_code == 200
    assert r.json()["anomalies"] == []


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------


def test_scenarios_listed(client):
    session = _register(client)
    r = client.get("/api/v1/simulator/scenarios", headers=_auth(session))
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 5
    ids = {item["id"] for item in items}
    assert "cpu_spike" in ids
    assert "website_downtime" in ids


def test_run_simulation_creates_incident(client):
    session = _register(client)
    r = client.post("/api/v1/simulator/run", json={"scenario": "website_downtime"}, headers=_auth(session))
    assert r.status_code == 200
    body = r.json()
    assert body["label"] == "synthetic"
    assert body["incident_id"] is not None


def test_run_cpu_spike_scenario(client):
    session = _register(client)
    r = client.post("/api/v1/simulator/run", json={"scenario": "cpu_spike"}, headers=_auth(session))
    assert r.status_code == 200
    assert r.json()["incident_id"] is not None


def test_run_unknown_scenario_rejected(client):
    session = _register(client)
    r = client.post("/api/v1/simulator/run", json={"scenario": "not_a_real_scenario"}, headers=_auth(session))
    assert r.status_code == 400


def test_simulation_incident_is_marked_synthetic(client):
    session = _register(client)
    result = client.post("/api/v1/simulator/run", json={"scenario": "api_latency"}, headers=_auth(session)).json()
    incident_id = result["incident_id"]
    r = client.get(f"/api/v1/incidents/{incident_id}", headers=_auth(session))
    assert r.status_code == 200
    assert r.json()["is_simulated"] is True


def test_simulation_incident_has_rca(client):
    session = _register(client)
    result = client.post("/api/v1/simulator/run", json={"scenario": "http_error_spike"}, headers=_auth(session)).json()
    incident_id = result["incident_id"]
    detail = client.get(f"/api/v1/incidents/{incident_id}", headers=_auth(session)).json()
    assert detail["rca"] is not None
    assert len(detail["rca"]["hypotheses"]) >= 1


def test_simulation_incident_has_ai_insight(client):
    session = _register(client)
    result = client.post("/api/v1/simulator/run", json={"scenario": "network_failure"}, headers=_auth(session)).json()
    incident_id = result["incident_id"]
    detail = client.get(f"/api/v1/incidents/{incident_id}", headers=_auth(session)).json()
    assert detail["ai"] is not None
    assert detail["ai"]["source"] in ("rule_based", "gemini")


def test_incident_acknowledge_and_resolve(client):
    session = _register(client)
    result = client.post("/api/v1/simulator/run", json={"scenario": "website_downtime"}, headers=_auth(session)).json()
    incident_id = result["incident_id"]
    r = client.post(f"/api/v1/incidents/{incident_id}/acknowledge", headers=_auth(session))
    assert r.status_code == 200
    assert r.json()["status"] == "acknowledged"
    r = client.post(f"/api/v1/incidents/{incident_id}/resolve", headers=_auth(session))
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"
    assert r.json()["resolved_at"] is not None


def test_incident_reopen(client):
    session = _register(client)
    result = client.post("/api/v1/simulator/run", json={"scenario": "website_downtime"}, headers=_auth(session)).json()
    incident_id = result["incident_id"]
    client.post(f"/api/v1/incidents/{incident_id}/resolve", headers=_auth(session))
    r = client.post(f"/api/v1/incidents/{incident_id}/reopen", headers=_auth(session))
    assert r.status_code == 200
    assert r.json()["status"] == "open"


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def test_create_report_no_websites(client):
    session = _register(client)
    r = client.post("/api/v1/reports", json={"title": "Test report"}, headers=_auth(session))
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Test report"
    assert body["content"]["sections"] == []


def test_list_reports(client):
    session = _register(client)
    client.post("/api/v1/reports", json={"title": "Rep 1"}, headers=_auth(session))
    r = client.get("/api/v1/reports", headers=_auth(session))
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_get_report(client):
    session = _register(client)
    created = client.post("/api/v1/reports", json={"title": "Detail report"}, headers=_auth(session)).json()
    r = client.get(f"/api/v1/reports/{created['id']}", headers=_auth(session))
    assert r.status_code == 200
    assert r.json()["title"] == "Detail report"


# ---------------------------------------------------------------------------
# Agent management
# ---------------------------------------------------------------------------


def test_create_and_list_agent(client):
    session = _register(client)
    r = client.post("/api/v1/agents", json={"name": "my-server"}, headers=_auth(session))
    assert r.status_code == 201
    body = r.json()
    assert "token" in body
    listing = client.get("/api/v1/agents", headers=_auth(session)).json()
    assert any(item["name"] == "my-server" for item in listing)


def test_revoke_agent(client):
    session = _register(client)
    created = client.post("/api/v1/agents", json={"name": "srv"}, headers=_auth(session)).json()
    r = client.post(f"/api/v1/agents/{created['id']}/revoke", headers=_auth(session))
    assert r.status_code == 200
    listing = client.get("/api/v1/agents", headers=_auth(session)).json()
    agent = next(item for item in listing if item["id"] == created["id"])
    assert agent["revoked"] is True


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_live(client):
    r = client.get("/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "live"
