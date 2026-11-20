"""Evidence-based root cause hypotheses.

Every explanation is a hypothesis unless the evidence directly confirms a cause
such as a failed DNS lookup or an expired certificate. Internal server causes
are not asserted from a public URL alone.
"""

from __future__ import annotations


def _item(title: str, explanation: str, confidence: str, confirmed: bool, evidence: list[str]) -> dict:
    return {
        "title": title,
        "explanation": explanation,
        "confidence": confidence,
        "status": "confirmed" if confirmed else "hypothesis",
        "evidence": evidence,
    }


def analyze(incident: dict, availability: dict | None, security: dict | None, performance: dict | None, agent: dict | None) -> dict:
    category = incident.get("category")
    evidence = incident.get("evidence") or {}
    hypotheses: list[dict] = []
    observed = incident.get("title") or "A monitoring problem was detected."
    if category == "dns" or (availability and availability.get("error_type") == "dns"):
        hypotheses.append(
            _item(
                "DNS misconfiguration or resolver failure",
                "The hostname failed DNS resolution on consecutive checks. That supports a DNS problem more strongly than an application bug.",
                "high",
                True,
                ["Consecutive DNS resolution failures were recorded.", str(evidence)],
            )
        )
        hypotheses.append(
            _item(
                "Domain expiration or nameserver outage",
                "A registrar, nameserver, or delegation change can produce the same public symptom. Verify the domain and nameservers with the DNS provider.",
                "medium",
                False,
                ["No registrar data is available from the public URL scan."],
            )
        )
    elif category == "tls":
        confirmed = bool(security and (security.get("days_until_expiry") is not None and security.get("days_until_expiry") < 0 or security.get("cert_valid") is False))
        hypotheses.append(
            _item(
                "Certificate expiration or invalid certificate chain",
                "The TLS handshake or certificate dates show a certificate problem.",
                "high" if confirmed else "medium",
                confirmed,
                [str(security or evidence)],
            )
        )
    elif category == "http_error":
        status = (availability or {}).get("http_status")
        if status is None:
            status = (availability or {}).get("status")
        status_evidence = f"HTTP status {status}" if status is not None else "HTTP status unavailable"
        hypotheses.append(
            _item(
                "Application or upstream server error",
                "Repeated HTTP 5xx responses mean the server is reachable but returning an error. The public response does not identify the internal function that failed.",
                "medium",
                False,
                [status_evidence, "No application logs are available in URL-only mode."],
            )
        )
        if agent and (agent.get("memory_percent") or 0) >= 90:
            hypotheses.append(
                _item(
                    "Host memory pressure",
                    "The optional monitoring agent reported high memory use near the error window.",
                    "medium",
                    False,
                    [f"Agent memory percent: {agent.get('memory_percent')}"],
                )
            )
        elif agent and (agent.get("cpu_percent") or 0) >= 90:
            hypotheses.append(
                _item(
                    "Host CPU saturation",
                    "The optional monitoring agent reported high CPU use. This can contribute to errors, but it does not by itself prove the code path that failed.",
                    "medium",
                    False,
                    [f"Agent CPU percent: {agent.get('cpu_percent')}"],
                )
            )
        else:
            hypotheses.append(
                _item(
                    "Dependency failure inside the origin",
                    "A database, cache, or upstream API could cause 5xx responses. This remains unverified without origin logs or an authorized agent.",
                    "low",
                    False,
                    ["Internal dependency metrics were not supplied."],
                )
            )
    elif category == "latency":
        hypotheses.append(
            _item(
                "Origin response time regression",
                "The measured response time is far above this site's own baseline. Possible contributors include slow application work, origin overload, or network path delay.",
                "medium",
                False,
                [str(evidence)],
            )
        )
        if performance and performance.get("lcp_ms") and performance["lcp_ms"] > 4000:
            hypotheses.append(
                _item(
                    "Large content or render delay",
                    "PageSpeed reported a high Largest Contentful Paint. That supports a front-end loading problem in addition to origin latency.",
                    "medium",
                    False,
                    [f"LCP {performance.get('lcp_ms')} ms from {performance.get('lcp_source') or 'unknown'} data"],
                )
            )
    elif category == "availability":
        hypotheses.append(
            _item(
                "Origin unreachable or network path failure",
                "Consecutive connection failures show that monitoring could not complete a request. DNS succeeded if dns_ok is true, so the failure is after name resolution.",
                "medium",
                False,
                [str(availability or evidence)],
            )
        )
    elif category == "performance":
        hypotheses.append(
            _item(
                "Front-end performance regression",
                "The PageSpeed performance score dropped by at least 20 points. Review the listed opportunities before changing server capacity.",
                "medium",
                False,
                [str(performance or evidence)],
            )
        )
    elif category == "resource":
        hypotheses.append(
            _item(
                "Host resource exhaustion",
                "An authorized agent reported a sustained resource threshold breach. This evidence comes from the agent, not from the public URL.",
                "high",
                True,
                [str(agent or evidence)],
            )
        )
    else:
        hypotheses.append(
            _item(
                "Insufficient evidence",
                "The collected signals do not identify a cause. Keep monitoring and compare the next scans with this baseline.",
                "low",
                False,
                [str(evidence)],
            )
        )
    return {
        "observed_problem": observed,
        "hypotheses": hypotheses,
        "verification_steps": [
            "Repeat the check from another network to separate local path problems from origin problems.",
            "Compare the timestamp with deploys, DNS changes, and certificate renewals.",
            "If you operate the server, inspect its logs for the same timestamp. Do not infer those logs from the public URL.",
        ],
        "recommended_actions": _actions(category),
        "preventive_measures": [
            "Keep the monitoring interval long enough to avoid stressing the site.",
            "Alert on confirmed failures rather than a single transient error.",
            "Renew certificates automatically and watch the 30-day and 7-day windows.",
        ],
    }


def _actions(category: str) -> list[str]:
    mapping = {
        "dns": ["Check authoritative nameservers and the domain registration status.", "Restore the previous DNS records if a recent change failed."],
        "tls": ["Renew or reissue the certificate and confirm the chain is served.", "Verify the hostname on the certificate matches the site."],
        "http_error": ["Inspect origin application logs for the same timestamp.", "Check recent deploys and upstream dependencies."],
        "latency": ["Compare application traces for the slow window.", "Review PageSpeed opportunities if a score was collected."],
        "availability": ["Check origin reachability, firewall rules, and hosting status.", "Confirm the site is not blocking the monitor's user agent."],
        "performance": ["Address the highest-impact PageSpeed opportunities first.", "Re-run a lab test after the change."],
        "resource": ["Inspect the process using the most CPU or memory on the host.", "Increase capacity only after identifying the leaking or saturated process."],
    }
    return mapping.get(category, ["Collect another scan and compare it with the stored baseline."])
