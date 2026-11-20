from __future__ import annotations

import httpx

from app.core.config import get_settings

LAB_AUDITS = {
    "largest-contentful-paint": "lcp_ms",
    "cumulative-layout-shift": "cls",
    "first-contentful-paint": "fcp_ms",
    "total-blocking-time": "tbt_ms",
    "interaction-to-next-paint": "inp_ms",
}


def _score(value) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value) * 100, 1)
    except (TypeError, ValueError):
        return None


def analyze_pagespeed(url: str, strategy: str) -> dict:
    settings = get_settings()
    base = {
        "strategy": strategy,
        "available": False,
        "error_message": None,
        "performance_score": None,
        "accessibility_score": None,
        "seo_score": None,
        "best_practices_score": None,
        "lcp_ms": None,
        "cls": None,
        "inp_ms": None,
        "fcp_ms": None,
        "tbt_ms": None,
        "lcp_source": None,
        "cls_source": None,
        "inp_source": None,
        "fcp_source": None,
        "opportunities": [],
    }
    if not settings.pagespeed_api_key:
        base["error_message"] = "PageSpeed Insights is not configured. Set PAGESPEED_API_KEY to enable lab and field metrics."
        return base
    endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = [
        ("url", url),
        ("strategy", strategy),
        ("key", settings.pagespeed_api_key),
        ("category", "performance"),
        ("category", "accessibility"),
        ("category", "seo"),
        ("category", "best-practices"),
    ]
    try:
        with httpx.Client(timeout=40, trust_env=False) as client:
            response = client.get(endpoint, params=params)
        if response.status_code == 429:
            base["error_message"] = "PageSpeed Insights rate limit was reached. The rest of the scan was still saved."
            return base
        if response.status_code >= 400:
            base["error_message"] = f"PageSpeed Insights returned HTTP {response.status_code}."
            return base
        payload = response.json()
    except httpx.HTTPError as exc:
        base["error_message"] = f"PageSpeed Insights request failed: {exc.__class__.__name__}"
        return base
    lighthouse = payload.get("lighthouseResult") or {}
    categories = lighthouse.get("categories") or {}
    audits = lighthouse.get("audits") or {}
    base["available"] = True
    base["performance_score"] = _score((categories.get("performance") or {}).get("score"))
    base["accessibility_score"] = _score((categories.get("accessibility") or {}).get("score"))
    base["seo_score"] = _score((categories.get("seo") or {}).get("score"))
    base["best_practices_score"] = _score((categories.get("best-practices") or {}).get("score"))
    for audit_id, field in LAB_AUDITS.items():
        audit = audits.get(audit_id) or {}
        numeric = audit.get("numericValue")
        if numeric is not None:
            base[field] = round(float(numeric), 2)
            source_field = field.replace("_ms", "").replace("cls", "cls")
            source_key = {
                "lcp_ms": "lcp_source",
                "cls": "cls_source",
                "inp_ms": "inp_source",
                "fcp_ms": "fcp_source",
            }.get(field)
            if source_key:
                base[source_key] = "lab"
    loading = payload.get("loadingExperience", {}).get("metrics") or {}
    field_map = {
        "LARGEST_CONTENTFUL_PAINT_MS": ("lcp_ms", "lcp_source"),
        "CUMULATIVE_LAYOUT_SHIFT_SCORE": ("cls", "cls_source"),
        "INTERACTION_TO_NEXT_PAINT": ("inp_ms", "inp_source"),
        "FIRST_CONTENTFUL_PAINT_MS": ("fcp_ms", "fcp_source"),
    }
    for metric_name, (field, source_field) in field_map.items():
        metric = loading.get(metric_name)
        if metric and metric.get("percentile") is not None:
            value = float(metric["percentile"])
            if metric_name == "CUMULATIVE_LAYOUT_SHIFT_SCORE":
                value = value / 100
            base[field] = round(value, 2)
            base[source_field] = "field"
    opportunities = []
    for audit in audits.values():
        details = audit.get("details") or {}
        if details.get("type") == "opportunity":
            opportunities.append(
                {
                    "title": audit.get("title"),
                    "display": audit.get("displayValue"),
                    "score": audit.get("score"),
                }
            )
        if len(opportunities) >= 8:
            break
    base["opportunities"] = opportunities
    if base["inp_ms"] is None:
        base["inp_source"] = None
    if base["tbt_ms"] is not None:
        pass
    return base
