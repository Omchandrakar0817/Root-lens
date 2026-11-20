"""SSRF-resistant HTTP client for public website monitoring.

Every outbound connection is limited to validated public HTTP(S) destinations.
DNS answers are checked before the socket is opened, and the TCP connection is
made to that exact address so a later DNS change cannot retarget the request.
"""

from __future__ import annotations

import ipaddress
import socket
import ssl
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from app.core.config import get_settings

ALLOWED_PORTS = {80, 443}
BLOCKED_HOSTS = {
    "localhost",
    "metadata.google.internal",
    "metadata.internal",
    "instance-data",
}
MAX_HEADER_BYTES = 64 * 1024


class UnsafeURLError(ValueError):
    pass


@dataclass
class FetchResult:
    ok: bool
    url: str
    final_url: str
    status_code: int | None
    elapsed_ms: float | None
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    error_type: str | None = None
    error_message: str | None = None
    redirect_count: int = 0
    dns_ok: bool = False
    tls_valid: bool | None = None
    cert_expires_at: str | None = None
    cert_issuer: str | None = None
    resolved_ip: str | None = None


def normalize_http_url(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        raise UnsafeURLError("URL is required")
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURLError("Only http and https URLs are allowed")
    if parsed.username or parsed.password:
        raise UnsafeURLError("URLs with credentials are not allowed")
    host = parsed.hostname
    if not host:
        raise UnsafeURLError("URL host is missing")
    lowered = host.strip().rstrip(".").lower()
    if lowered in BLOCKED_HOSTS or lowered.endswith(".localhost") or lowered.endswith(".local") or lowered.endswith(".internal"):
        raise UnsafeURLError("Blocked host name")
    try:
        literal = ipaddress.ip_address(lowered)
    except ValueError:
        literal = None
    if literal is not None:
        _reject_ip(literal)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port not in ALLOWED_PORTS:
        raise UnsafeURLError("Only ports 80 and 443 are allowed")
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    host_for_netloc = host
    if ":" in host and not host.startswith("["):
        host_for_netloc = f"[{host}]"
    netloc = host_for_netloc if (parsed.scheme == "https" and port == 443) or (parsed.scheme == "http" and port == 80) else f"{host_for_netloc}:{port}"
    return f"{parsed.scheme}://{netloc}{path}"


def _reject_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if (
        not ip.is_global
        or ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        raise UnsafeURLError(f"Blocked non-public address {ip}")


def validate_submission(url: str) -> str:
    """Normalize a user URL and reject private targets.

    DNS failure is allowed at registration time so a public hostname that is
    currently down can still be monitored. A successful DNS answer that points
    at a non-public address is rejected.
    """
    normalized = normalize_http_url(url)
    host = urlparse(normalized).hostname or ""
    try:
        assert_public_host(host)
    except UnsafeURLError as exc:
        if "DNS resolution failed" in str(exc):
            return normalized
        raise
    return normalized


def assert_public_host(hostname: str) -> list[str]:
    host = hostname.strip().rstrip(".").lower()
    if host in BLOCKED_HOSTS or host.endswith(".localhost") or host.endswith(".local"):
        raise UnsafeURLError("Blocked host name")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        _reject_ip(literal)
        return [str(literal)]
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"DNS resolution failed: {exc}") from exc
    addresses: list[str] = []
    for info in infos:
        ip_text = info[4][0]
        ip = ipaddress.ip_address(ip_text.split("%")[0])
        _reject_ip(ip)
        if ip_text not in addresses:
            addresses.append(ip_text)
    if not addresses:
        raise UnsafeURLError("DNS resolution returned no addresses")
    return addresses


def _read_response(sock: socket.socket, max_bytes: int) -> tuple[int, dict[str, str], bytes]:
    sock.settimeout(get_settings().scan_timeout_seconds)
    buffer = b""
    while b"\r\n\r\n" not in buffer:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buffer += chunk
        if len(buffer) > MAX_HEADER_BYTES:
            raise UnsafeURLError("Response headers are too large")
    if b"\r\n\r\n" not in buffer:
        raise TimeoutError("Incomplete HTTP response")
    header_blob, rest = buffer.split(b"\r\n\r\n", 1)
    lines = header_blob.decode("iso-8859-1", errors="replace").split("\r\n")
    parts = lines[0].split(" ", 2)
    if len(parts) < 2 or not parts[1].isdigit():
        raise UnsafeURLError("Invalid HTTP status line")
    status = int(parts[1])
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    body = rest
    if "content-length" in headers:
        try:
            length = min(int(headers["content-length"]), max_bytes)
        except ValueError:
            length = max_bytes
        while len(body) < length:
            chunk = sock.recv(min(8192, length - len(body)))
            if not chunk:
                break
            body += chunk
        body = body[:length]
    else:
        while len(body) < max_bytes:
            try:
                chunk = sock.recv(8192)
            except TimeoutError:
                break
            if not chunk:
                break
            body += chunk
        body = body[:max_bytes]
    return status, headers, body


def _request_once(url: str, method: str = "GET") -> tuple[int, dict[str, str], bytes, str, bool | None, str | None, str | None, float]:
    import time

    settings = get_settings()
    parsed = urlparse(url)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    addresses = assert_public_host(host)
    # Re-check immediately before connecting to reduce DNS rebinding window.
    confirmed = assert_public_host(host)
    ip = confirmed[0] if confirmed[0] in addresses else addresses[0]
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    started = time.perf_counter()
    sock = socket.create_connection((ip, port), timeout=settings.scan_timeout_seconds)
    tls_valid: bool | None = None
    cert_expires = None
    cert_issuer = None
    try:
        if parsed.scheme == "https":
            context = ssl.create_default_context()
            # On Windows, load the system (Windows) CA store so HTTPS works
            # without a separate certifi bundle.
            import sys as _sys
            if _sys.platform == "win32":
                import certifi as _certifi  # type: ignore[import]
                context.load_verify_locations(cafile=_certifi.where())
            try:
                sock = context.wrap_socket(sock, server_hostname=host)
                tls_valid = True
                cert = sock.getpeercert()
                if cert:
                    cert_expires = cert.get("notAfter")
                    issuer = cert.get("issuer") or []
                    parts = []
                    for item in issuer:
                        for key, value in item:
                            if key in {"commonName", "organizationName"}:
                                parts.append(value)
                    cert_issuer = ", ".join(parts) or None
            except ssl.SSLError as exc:
                tls_valid = False
                raise UnsafeURLError(f"TLS validation failed: {exc}") from exc
        host_header = host if port in {80, 443} else f"{host}:{port}"
        payload = (
            f"{method} {path} HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            "User-Agent: IncidentRCAMonitor/1.0\r\n"
            "Accept: text/html,application/json;q=0.9,*/*;q=0.8\r\n"
            "Connection: close\r\n\r\n"
        )
        sock.sendall(payload.encode("ascii"))
        status, headers, body = _read_response(sock, settings.max_response_bytes)
        elapsed = (time.perf_counter() - started) * 1000
        return status, headers, body, ip, tls_valid, cert_expires, cert_issuer, elapsed
    finally:
        try:
            sock.close()
        except OSError:
            pass


def safe_fetch(url: str, method: str = "GET") -> FetchResult:
    settings = get_settings()
    try:
        current = normalize_http_url(url)
    except UnsafeURLError as exc:
        return FetchResult(False, url, url, None, None, error_type="blocked_url", error_message=str(exc))
    redirects = 0
    while True:
        try:
            status, headers, body, ip, tls_valid, cert_expires, cert_issuer, elapsed = _request_once(current, method)
        except UnsafeURLError as exc:
            kind = "blocked_url" if "Blocked" in str(exc) or "not allowed" in str(exc) or "TLS" in str(exc) else "dns"
            if "DNS" in str(exc):
                kind = "dns"
            return FetchResult(False, url, current, None, None, error_type=kind, error_message=str(exc), redirect_count=redirects)
        except TimeoutError as exc:
            return FetchResult(False, url, current, None, None, error_type="timeout", error_message=str(exc), redirect_count=redirects, dns_ok=True)
        except OSError as exc:
            return FetchResult(False, url, current, None, None, error_type="connection", error_message=str(exc), redirect_count=redirects)
        result = FetchResult(
            ok=status < 500,
            url=url,
            final_url=current,
            status_code=status,
            elapsed_ms=round(elapsed, 2),
            headers=headers,
            body=body,
            redirect_count=redirects,
            dns_ok=True,
            tls_valid=tls_valid,
            cert_expires_at=cert_expires,
            cert_issuer=cert_issuer,
            resolved_ip=ip,
        )
        if status in {301, 302, 303, 307, 308} and "location" in headers and method == "GET":
            if redirects >= settings.max_redirects:
                result.ok = False
                result.error_type = "redirect_limit"
                result.error_message = "Too many redirects"
                return result
            nxt = urljoin(current, headers["location"])
            try:
                current = normalize_http_url(nxt)
            except UnsafeURLError as exc:
                result.ok = False
                result.error_type = "blocked_redirect"
                result.error_message = str(exc)
                return result
            redirects += 1
            continue
        if status >= 500:
            result.error_type = "http_5xx"
            result.error_message = f"HTTP {status}"
        elif status >= 400:
            result.error_type = "http_4xx"
            result.error_message = f"HTTP {status}"
            result.ok = True
        return result
