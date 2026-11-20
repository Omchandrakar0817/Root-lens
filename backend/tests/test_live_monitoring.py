"""Live HTTP monitoring tests — no database required.

These tests make real outbound HTTP requests to stable public test URLs.
They verify: safe_fetch, TLS, security scanner, SEO scanner, anomaly detection,
RCA engine, and Celery task routing with fakeredis.
"""
from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# SSRF / URL safety (pure logic — already in test_core_logic, kept brief here)
# ---------------------------------------------------------------------------
from app.services.safe_http import UnsafeURLError, normalize_http_url, validate_submission


def test_ssrf_private_ranges():
    blocked = [
        "http://10.0.0.1/",
        "http://172.16.0.1/",
        "http://192.168.1.1/",
        "http://127.0.0.1/",
        "http://::1/",
        "http://169.254.169.254/latest/meta-data",
        "http://metadata.google.internal/",
        "file:///etc/passwd",
        "ftp://example.com/",
        "http://example.com:22/",
        "http://user:pass@example.com/",
        "http://localhost/",
    ]
    for url in blocked:
        with pytest.raises(UnsafeURLError, match=""):
            normalize_http_url(url)


def test_ssrf_public_urls_accepted():
    assert normalize_http_url("https://example.com") == "https://example.com/"
    assert normalize_http_url("http://example.com") == "http://example.com/"
    assert normalize_http_url("example.com") == "https://example.com/"


# ---------------------------------------------------------------------------
# Real HTTP fetch — uses example.com (IANA stable test domain)
# ---------------------------------------------------------------------------
from app.services.safe_http import safe_fetch


def test_real_fetch_example_com():
    result = safe_fetch("https://example.com/")
    assert result.dns_ok is True
    assert result.status_code == 200
    assert result.elapsed_ms is not None and result.elapsed_ms > 0
    assert result.tls_valid is True
    assert result.body and len(result.body) > 100


def test_real_fetch_records_response_time():
    result = safe_fetch("https://example.com/")
    assert isinstance(result.elapsed_ms, float)
    assert result.elapsed_ms > 0
    assert result.elapsed_ms < 30_000  # under 30 s


def test_real_fetch_tls_cert_info():
    result = safe_fetch("https://example.com/")
    assert result.tls_valid is True
    assert result.cert_expires_at is not None
    assert result.cert_issuer is not None


def test_real_fetch_nonexistent_domain():
    result = safe_fetch("https://this-domain-does-not-exist-xyz123abc.com/")
    assert result.ok is False
    assert result.error_type in {"dns", "connection", "timeout"}


def test_real_fetch_http_404():
    result = safe_fetch("https://example.com/this-page-does-not-exist-404abc")
    # example.com returns 404 for unknown paths
    assert result.status_code is not None


def test_blocked_redirect_to_private():
    """Redirect that points at a private IP must be blocked."""
    # We can't easily trigger a real redirect to private — test the helper directly
    from urllib.parse import urlparse
    with pytest.raises(UnsafeURLError):
        normalize_http_url("http://10.0.0.1/redirect-target")


# ---------------------------------------------------------------------------
# Security scanner against real site
# ---------------------------------------------------------------------------
from app.services.scanners.security import analyze_security


def test_security_scanner_example_com():
    page = safe_fetch("https://example.com/")
    result = analyze_security(page, "https://example.com/")
    assert result["https_available"] is True
    assert result["cert_valid"] is True
    assert result["days_until_expiry"] is not None
    assert result["days_until_expiry"] > 0
    assert isinstance(result["findings"], list)
    assert isinstance(result["headers"], dict)


def test_security_scanner_produces_header_findings():
    page = safe_fetch("https://example.com/")
    result = analyze_security(page, "https://example.com/")
    # example.com doesn't set all security headers — findings should be non-empty
    codes = [f["code"] for f in result["findings"]]
    # At minimum CSP or HSTS will be missing
    assert len(codes) > 0


# ---------------------------------------------------------------------------
# SEO scanner against real site
# ---------------------------------------------------------------------------
from app.services.scanners.seo import analyze_html, check_robots_and_sitemap


def test_seo_scanner_example_com():
    page = safe_fetch("https://example.com/")
    result = analyze_html(page, "https://example.com/")
    assert result["title"] is not None
    assert isinstance(result["h1_count"], int)
    assert isinstance(result["findings"], list)


def test_robots_sitemap_check():
    result = check_robots_and_sitemap("https://example.com/")
    # example.com may or may not have robots.txt — just check structure
    assert "robots_txt_present" in result
    assert "sitemap_present" in result
    assert isinstance(result["findings"], list)


# ---------------------------------------------------------------------------
# Anomaly detection against synthetic series (pure logic, fast)
# ---------------------------------------------------------------------------
from app.services.detection.anomaly import evaluate_series, forecast_trend, statistical_check


def test_statistical_check_spike():
    values = [100, 105, 98, 102, 103, 99, 5000]
    result = statistical_check(values, "response_time_ms")
    assert result.is_anomaly is True
    assert result.model_trained is False
    assert result.score is not None


def test_statistical_check_normal():
    values = [100, 105, 98, 102, 103, 99, 101]
    result = statistical_check(values, "response_time_ms")
    assert result.is_anomaly is False


def test_forecast_needs_20_samples():
    assert forecast_trend([100] * 10, "response_time_ms") is None
    assert forecast_trend([100] * 20, "response_time_ms") is not None


def test_isolation_forest_scores_outlier():
    import os
    os.environ.setdefault("DATABASE_URL", "sqlite://")
    from app.core.config import get_settings
    get_settings.cache_clear()
    values = [100 + (i % 5) for i in range(29)] + [9999]
    result, blob = evaluate_series(values, "response_time_ms", None)
    assert result.model_trained is True
    assert result.is_anomaly is True
    assert blob is not None


# ---------------------------------------------------------------------------
# RCA engine — deterministic, no network
# ---------------------------------------------------------------------------
from app.services.rca.engine import analyze


def test_rca_availability():
    out = analyze({"title": "Down", "category": "availability", "evidence": {}},
                  {"error_type": "connection"}, None, None, None)
    assert len(out["hypotheses"]) >= 1
    assert out["recommended_actions"]


def test_rca_tls_confirmed():
    out = analyze({"title": "TLS", "category": "tls", "evidence": {}},
                  None,
                  {"cert_valid": False, "days_until_expiry": -5},
                  None, None)
    confirmed = [h for h in out["hypotheses"] if h["status"] == "confirmed"]
    assert confirmed


def test_rca_latency():
    out = analyze({"title": "Slow", "category": "latency", "evidence": {"response_time_ms": 5000}},
                  None, None,
                  {"lcp_ms": 6000, "lcp_source": "lab"},
                  None)
    assert any("latency" in h["title"].lower() or "content" in h["title"].lower()
               for h in out["hypotheses"])


def test_rca_resource_with_agent():
    out = analyze({"title": "CPU", "category": "resource", "evidence": {}},
                  None, None, None,
                  {"cpu_percent": 97, "memory_percent": 42})
    assert out["hypotheses"][0]["status"] == "confirmed"


# ---------------------------------------------------------------------------
# Celery task routing with fakeredis
# ---------------------------------------------------------------------------
import fakeredis
from unittest.mock import patch, MagicMock


def test_enqueue_scan_uses_redis_when_available():
    """enqueue_scan returns True when Redis is reachable (fakeredis)."""
    fake_server = fakeredis.FakeServer()
    fake_client = fakeredis.FakeRedis(server=fake_server)

    # redis is imported locally inside enqueue_scan — patch the redis module directly
    import redis as _redis_module
    with patch.object(_redis_module.Redis, "from_url", return_value=fake_client):
        with patch("app.workers.tasks.run_manual_scan.delay") as mock_delay:
            from app.workers.tasks import enqueue_scan
            result = enqueue_scan("some-website-id")
            assert result is True
            mock_delay.assert_called_once_with("some-website-id")


def test_enqueue_scan_falls_back_when_redis_unavailable():
    """enqueue_scan returns False gracefully when Redis is down."""
    import redis as _redis_module
    with patch.object(_redis_module.Redis, "from_url",
                      side_effect=Exception("connection refused")):
        from app.workers.tasks import enqueue_scan
        result = enqueue_scan("some-website-id")
        assert result is False


def test_celery_beat_schedule_configured():
    """Beat schedule must include the dispatch task at ≤60s interval."""
    from app.workers.celery_app import celery_app
    schedule = celery_app.conf.beat_schedule
    assert "dispatch-due-monitors" in schedule
    task_cfg = schedule["dispatch-due-monitors"]
    assert task_cfg["task"] == "app.workers.tasks.dispatch_due_monitors"
    assert task_cfg["schedule"] <= 60.0


def test_celery_app_settings():
    from app.workers.celery_app import celery_app
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.task_reject_on_worker_lost is True


# ---------------------------------------------------------------------------
# Scheduling logic (pure, no DB)
# ---------------------------------------------------------------------------
from app.services.detection.rules import lease_is_free, next_backoff, should_correlate
from datetime import UTC, datetime, timedelta


def test_lease_logic():
    now = datetime.now(UTC)
    assert lease_is_free(None, now) is True
    assert lease_is_free(now - timedelta(seconds=1), now) is True
    assert lease_is_free(now + timedelta(minutes=5), now) is False


def test_backoff_caps_at_1h():
    assert next_backoff(0) == 60
    assert next_backoff(1) == 120
    assert next_backoff(100) == 3600


def test_correlation_rule():
    assert should_correlate("open", "dns", "dns") is True
    assert should_correlate("resolved", "dns", "dns") is False
    assert should_correlate("open", "dns", "latency") is False


# ---------------------------------------------------------------------------
# Gemini fallback (no key — pure logic)
# ---------------------------------------------------------------------------
from app.services.ai.gemini import rule_based, explain


def test_rule_based_summary():
    out = rule_based({"title": "Test", "category": "latency",
                      "hypotheses": [{"title": "Slow origin",
                                      "status": "hypothesis",
                                      "confidence": "medium"}]})
    assert out.source == "rule_based"
    assert "Hypothesis" in " ".join(out.likely_causes)
    assert out.confidence_note


def test_explain_no_key_returns_rule_based(monkeypatch):
    monkeypatch.setattr(
        "app.services.ai.gemini.get_settings",
        lambda: type("S", (), {"gemini_api_key": "", "gemini_model": "gemini-2.0-flash"})()
    )
    out = explain({"title": "Down", "category": "availability", "hypotheses": []})
    assert out.source == "rule_based"
