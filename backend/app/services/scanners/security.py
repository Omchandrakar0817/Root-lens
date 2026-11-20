from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

from app.services.safe_http import FetchResult, safe_fetch

REQUIRED_HEADERS = {
    "content-security-policy": "Content-Security-Policy is missing.",
    "strict-transport-security": "HTTP Strict Transport Security (HSTS) is missing.",
    "x-content-type-options": "X-Content-Type-Options is missing.",
    "referrer-policy": "Referrer-Policy is missing.",
}


def analyze_security(page: FetchResult, original_url: str) -> dict:
    findings: list[dict] = []
    parsed = urlparse(page.final_url or original_url)
    https_available = parsed.scheme == "https" and page.tls_valid is not False and page.dns_ok
    redirects_to_https = None
    if urlparse(original_url).scheme == "http":
        redirects_to_https = parsed.scheme == "https"
        if redirects_to_https is False:
            findings.append({"severity": "high", "code": "no_https_redirect", "message": "The HTTP URL did not redirect to HTTPS."})
    elif urlparse(original_url).scheme == "https":
        http_probe = safe_fetch("http://" + (urlparse(original_url).netloc) + (urlparse(original_url).path or "/"))
        final_scheme = urlparse(http_probe.final_url).scheme if http_probe.final_url else "http"
        redirects_to_https = final_scheme == "https" and http_probe.status_code in {301, 302, 303, 307, 308, 200}
        if final_scheme != "https":
            findings.append({"severity": "medium", "code": "no_https_redirect", "message": "A plain HTTP request did not end on HTTPS."})
            redirects_to_https = False
    if page.tls_valid is False:
        findings.append({"severity": "critical", "code": "invalid_cert", "message": page.error_message or "The TLS certificate could not be validated."})
        https_available = False
    expires_at = None
    days = None
    if page.cert_expires_at:
        try:
            expires_at = parsedate_to_datetime(page.cert_expires_at)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            days = (expires_at - datetime.now(UTC)).days
            if days < 0:
                findings.append({"severity": "critical", "code": "cert_expired", "message": "The TLS certificate is expired."})
            elif days <= 7:
                findings.append({"severity": "high", "code": "cert_expiring", "message": f"The TLS certificate expires in {days} day(s)."})
            elif days <= 30:
                findings.append({"severity": "medium", "code": "cert_expiring", "message": f"The TLS certificate expires in {days} day(s)."})
        except (TypeError, ValueError, OSError):
            expires_at = None
    observed = {key: page.headers.get(key) for key in REQUIRED_HEADERS}
    for key, message in REQUIRED_HEADERS.items():
        if not page.headers.get(key):
            findings.append({"severity": "low", "code": f"missing_{key}", "message": message})
    if not https_available and urlparse(original_url).scheme == "http":
        findings.append({"severity": "high", "code": "https_unavailable", "message": "HTTPS was not confirmed for this URL."})
    return {
        "https_available": https_available,
        "redirects_to_https": redirects_to_https,
        "cert_valid": page.tls_valid,
        "cert_expires_at": expires_at,
        "cert_issuer": page.cert_issuer,
        "days_until_expiry": days,
        "headers": observed,
        "findings": findings,
    }
