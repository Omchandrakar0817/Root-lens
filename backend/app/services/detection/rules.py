"""Incident classification from observed measurements.

A single transient failure does not open a downtime incident. The caller passes
the previous real measurement so confirmation can be enforced.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Detection:
    category: str
    severity: str
    title: str
    symptoms: list[str]
    evidence: dict
    fingerprint: str
    open_incident: bool = True


@dataclass
class MeasurementView:
    is_up: bool
    http_status: int | None
    response_time_ms: float | None
    error_type: str | None
    error_message: str | None
    dns_ok: bool
    tls_valid: bool | None
    confirmed_failure: bool = False


def confirm_failure(current: MeasurementView, previous: MeasurementView | None) -> bool:
    if current.is_up and (current.http_status or 0) < 500 and current.error_type not in {"dns", "timeout", "connection"}:
        return False
    hard = current.error_type in {"dns", "blocked_url"} or current.tls_valid is False
    if hard and current.error_type == "dns":
        return previous is not None and previous.error_type == "dns"
    if current.tls_valid is False:
        return True
    if previous is None:
        return False
    previous_bad = (not previous.is_up) or (previous.http_status or 0) >= 500 or previous.error_type in {"timeout", "connection", "http_5xx"}
    current_bad = (not current.is_up) or (current.http_status or 0) >= 500 or current.error_type in {"timeout", "connection", "http_5xx"}
    return previous_bad and current_bad


def classify(current: MeasurementView, previous: MeasurementView | None, baseline_ms: float | None, security_findings: list[dict] | None = None, performance_score: float | None = None, previous_score: float | None = None) -> list[Detection]:
    found: list[Detection] = []
    confirmed = confirm_failure(current, previous)
    current.confirmed_failure = confirmed
    if current.error_type == "dns" and confirmed:
        found.append(
            Detection(
                category="dns",
                severity="critical",
                title="DNS resolution is failing",
                symptoms=["The hostname did not resolve on consecutive checks."],
                evidence={"error": current.error_message, "confirmed": True},
                fingerprint="dns",
            )
        )
    elif not current.is_up and confirmed:
        found.append(
            Detection(
                category="availability",
                severity="critical",
                title="Website availability failure confirmed",
                symptoms=[current.error_message or "Consecutive connection failures."],
                evidence={"error_type": current.error_type, "status": current.http_status, "confirmed": True},
                fingerprint="availability",
            )
        )
    if current.http_status and current.http_status >= 500 and confirmed:
        found.append(
            Detection(
                category="http_error",
                severity="high",
                title=f"Repeated HTTP {current.http_status} responses",
                symptoms=["The site returned a server error on consecutive checks."],
                evidence={"status": current.http_status, "confirmed": True},
                fingerprint=f"http-{current.http_status // 100}xx",
            )
        )
    if (
        current.response_time_ms
        and baseline_ms
        and baseline_ms > 0
        and current.response_time_ms > max(2000, baseline_ms * 3)
        and current.is_up
    ):
        found.append(
            Detection(
                category="latency",
                severity="high",
                title="Response time is severely degraded",
                symptoms=[f"Latest response time is {current.response_time_ms:.0f} ms against a baseline of {baseline_ms:.0f} ms."],
                evidence={"response_time_ms": current.response_time_ms, "baseline_ms": baseline_ms},
                fingerprint="latency",
            )
        )
    for finding in security_findings or []:
        if finding.get("code") in {"cert_expired", "invalid_cert"}:
            found.append(
                Detection(
                    category="tls",
                    severity=finding.get("severity", "high"),
                    title="TLS certificate problem",
                    symptoms=[finding.get("message", "Certificate problem")],
                    evidence=finding,
                    fingerprint="tls",
                )
            )
        elif finding.get("code") == "cert_expiring" and finding.get("severity") in {"high", "critical"}:
            found.append(
                Detection(
                    category="tls",
                    severity=finding.get("severity", "high"),
                    title="TLS certificate is close to expiration",
                    symptoms=[finding.get("message", "Certificate expiring")],
                    evidence=finding,
                    fingerprint="tls-expiry",
                )
            )
    if performance_score is not None and previous_score is not None and previous_score - performance_score >= 20:
        found.append(
            Detection(
                category="performance",
                severity="medium",
                title="Performance score regression",
                symptoms=[f"Performance score moved from {previous_score:.0f} to {performance_score:.0f}."],
                evidence={"current": performance_score, "previous": previous_score, "source": "pagespeed"},
                fingerprint="performance-regression",
            )
        )
    return found


def should_correlate(existing_status: str, fingerprint: str, new_fingerprint: str) -> bool:
    return existing_status in {"open", "acknowledged"} and fingerprint == new_fingerprint


@dataclass
class LeaseDecision:
    claim: bool
    reason: str
    backoff_seconds: int = 0


def lease_is_free(locked_until, now) -> bool:
    return locked_until is None or locked_until <= now


def next_backoff(retry_count: int, base: int = 60) -> int:
    return min(base * (2 ** max(retry_count, 0)), 3600)
