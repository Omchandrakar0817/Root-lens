import json
import logging
from datetime import UTC, datetime, timedelta

import pytest

from app.services.ai import gemini
from app.services.ai.gemini import explain
from app.services.detection.anomaly import evaluate_series, forecast_trend
from app.services.detection.rules import MeasurementView, classify, confirm_failure, lease_is_free, next_backoff, should_correlate
from app.services.rca.engine import analyze
from app.services.safe_http import UnsafeURLError, normalize_http_url, validate_submission


def test_url_normalization_and_blocks():
    assert normalize_http_url("https://example.com") == "https://example.com/"
    with pytest.raises(UnsafeURLError):
        normalize_http_url("file:///etc/passwd")
    with pytest.raises(UnsafeURLError):
        normalize_http_url("http://127.0.0.1/")
    with pytest.raises(UnsafeURLError):
        normalize_http_url("http://169.254.169.254/latest/meta-data")
    with pytest.raises(UnsafeURLError):
        normalize_http_url("http://10.1.2.3/")
    with pytest.raises(UnsafeURLError):
        normalize_http_url("http://192.168.0.5/")
    with pytest.raises(UnsafeURLError):
        normalize_http_url("https://example.com:22/")
    with pytest.raises(UnsafeURLError):
        normalize_http_url("http://user:pass@example.com/")
    with pytest.raises(UnsafeURLError):
        validate_submission("http://localhost/admin")


def test_single_failure_does_not_open_downtime():
    current = MeasurementView(False, None, None, "connection", "timed out", True, None)
    assert confirm_failure(current, None) is False
    previous = MeasurementView(False, None, None, "connection", "timed out", True, None)
    assert confirm_failure(current, previous) is True
    detections = classify(current, previous, 200)
    assert any(item.category == "availability" and item.severity == "critical" for item in detections)


def test_dns_needs_two_failures_and_rca_confirms_it():
    one = MeasurementView(False, None, None, "dns", "dns failed", False, None)
    assert confirm_failure(one, None) is False
    assert confirm_failure(one, one) is True
    rca = analyze({"title": "DNS", "category": "dns", "evidence": {"error": "dns"}}, {"error_type": "dns"}, None, None, None)
    confirmed = [item for item in rca["hypotheses"] if item["status"] == "confirmed"]
    assert confirmed
    assert "DNS" in confirmed[0]["title"]


def test_http_500_is_hypothesis_not_internal_fact():
    incident = {"title": "errors", "category": "http_error", "evidence": {}}
    rca = analyze(incident, {"status": 500}, None, None, None)
    assert all(item["status"] == "hypothesis" for item in rca["hypotheses"])
    assert any("does not identify" in item["explanation"] or "public response" in item["explanation"] for item in rca["hypotheses"])
    assert "HTTP status 500" in rca["hypotheses"][0]["evidence"]

    unavailable = analyze(incident, {}, None, None, None)
    assert "HTTP status unavailable" in unavailable["hypotheses"][0]["evidence"]


def test_cold_start_is_not_called_a_trained_model():
    result, blob = evaluate_series([100, 110, 105, 108, 400], "response_time_ms", None)
    assert result.model_trained is False
    assert result.method == "statistical_zscore"
    assert blob is None
    forecast = forecast_trend([100, 110, 105], "response_time_ms")
    assert forecast is None


def test_isolation_forest_trains_after_threshold(monkeypatch):
    monkeypatch.setattr("app.services.detection.anomaly.get_settings", lambda: type("S", (), {"anomaly_min_samples": 30})())
    values = [100 + (i % 5) for i in range(29)] + [5000]
    result, blob = evaluate_series(values, "response_time_ms", None)
    assert result.model_trained is True
    assert result.method == "isolation_forest"
    assert blob is not None
    assert result.is_anomaly is True
    forecast = forecast_trend(values, "response_time_ms")
    assert forecast is not None
    assert forecast.record_type == "forecast"
    assert "not a confirmed future incident" in forecast.evidence["note"]


def test_correlation_and_backoff():
    assert should_correlate("open", "dns", "dns") is True
    assert should_correlate("resolved", "dns", "dns") is False
    assert next_backoff(0) == 60
    assert next_backoff(3) == 480
    now = datetime.now(UTC)
    assert lease_is_free(None, now) is True
    assert lease_is_free(now - timedelta(seconds=1), now) is True
    assert lease_is_free(now + timedelta(minutes=5), now) is False


def test_gemini_fallback_without_key(monkeypatch):
    monkeypatch.setattr("app.services.ai.gemini.get_settings", lambda: type("S", (), {"gemini_api_key": "", "gemini_model": "gemini-2.0-flash"})())
    insight = explain({"title": "Latency", "category": "latency", "hypotheses": []})
    assert insight.source == "rule_based"
    assert "local rules" in insight.summary


def test_gemini_parses_response_without_backend_source_field(monkeypatch):
    class Response:
        status_code = 200

        def json(self):
            content = {
                "summary": "Database connection failures likely caused the outage.",
                "likely_causes": ["Connection pool exhaustion"],
                "troubleshooting_steps": ["Inspect connection pool metrics."],
                "preventive_actions": ["Alert on pool saturation."],
                "confidence_note": "Hypothesis based on monitoring evidence.",
            }
            return {"candidates": [{"content": {"parts": [{"text": json.dumps(content)}]}}]}

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, **kwargs):
            assert "gemini-3.5-flash-lite:generateContent" in url
            assert "key=" not in url
            assert kwargs["headers"]["x-goog-api-key"] == "configured"
            return Response()

    monkeypatch.setattr(
        "app.services.ai.gemini.get_settings",
        lambda: type("S", (), {"gemini_api_key": "configured", "gemini_model": "gemini-3.5-flash-lite"})(),
    )
    monkeypatch.setattr("app.services.ai.gemini.httpx.Client", Client)

    insight = explain({"title": "Database errors", "category": "http_error", "simulated": False})

    assert insight.source == "gemini"
    assert insight.likely_causes == ["Connection pool exhaustion"]
    assert insight.troubleshooting_steps == ["Inspect connection pool metrics."]


def test_gemini_key_is_not_logged_or_returned_on_quota_error(monkeypatch, caplog):
    api_key = "test-key-that-must-not-leak"
    request_urls = []
    original_client = gemini.httpx.Client

    def handle_request(request):
        request_urls.append(str(request.url))
        assert request.headers["x-goog-api-key"] == api_key
        return gemini.httpx.Response(429, request=request)

    transport = gemini.httpx.MockTransport(handle_request)
    monkeypatch.setattr(
        "app.services.ai.gemini.get_settings",
        lambda: type("S", (), {"gemini_api_key": api_key, "gemini_model": "gemini-3.5-flash-lite"})(),
    )
    monkeypatch.setattr(
        gemini.httpx,
        "Client",
        lambda **kwargs: original_client(transport=transport, **kwargs),
    )

    with caplog.at_level(logging.INFO, logger="httpx"):
        insight = explain({"title": "HTTP errors", "category": "http_error"})

    assert insight.source == "rule_based"
    assert "HTTP 429" in insight.confidence_note
    assert api_key not in " ".join(request_urls)
    assert api_key not in caplog.text
    assert api_key not in insight.model_dump_json()


def test_simulated_explanation_never_calls_gemini(monkeypatch):
    monkeypatch.setattr("app.services.ai.gemini.get_settings", lambda: type("S", (), {"gemini_api_key": "configured", "gemini_model": "gemini-2.0-flash"})())
    monkeypatch.setattr("app.services.ai.gemini.httpx.Client.post", lambda *args, **kwargs: pytest.fail("Gemini must not be called for simulated evidence"))
    insight = explain({"title": "Synthetic downtime", "category": "availability", "simulated": True})
    assert insight.source == "rule_based"
