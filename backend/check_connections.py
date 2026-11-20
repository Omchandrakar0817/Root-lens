#!/usr/bin/env python3
"""
Check and verify all external service connections:
  - PostgreSQL (via DATABASE_URL)
  - Redis (via REDIS_URL)
  - Optional: Gemini, PageSpeed

Run from the backend directory:
  python check_connections.py

Exit code 0 = all required services reachable.
Exit code 1 = at least one required service unreachable.
"""
from __future__ import annotations

import sys
import os

os.environ.setdefault("APP_ENV", "development")


def _check_postgres() -> bool:
    try:
        from app.core.config import get_settings
        from app.core.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"  ✓ PostgreSQL connected: {version}")
        return True
    except Exception as exc:
        print(f"  ✗ PostgreSQL FAILED: {exc}")
        return False


def _check_redis() -> bool:
    try:
        from app.core.config import get_settings
        import redis
        url = get_settings().redis_url
        client = redis.Redis.from_url(url, socket_connect_timeout=3)
        pong = client.ping()
        print(f"  ✓ Redis connected: PING={pong}  url={url}")
        return True
    except Exception as exc:
        print(f"  ✗ Redis FAILED: {exc}")
        return False


def _check_tables() -> bool:
    try:
        from app.core.database import engine
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        expected = {
            "users", "websites", "incidents", "scan_jobs",
            "availability_measurements", "rca_analyses", "anomalies",
            "ml_models", "monitoring_schedules", "monitoring_configs",
        }
        missing = expected - set(tables)
        if missing:
            print(f"  ✗ Missing tables: {missing}")
            return False
        print(f"  ✓ All {len(tables)} tables present")
        return True
    except Exception as exc:
        print(f"  ✗ Table check FAILED: {exc}")
        return False


def _check_gemini() -> bool:
    try:
        from app.core.config import get_settings
        key = get_settings().gemini_api_key
        if not key:
            print("  ~ Gemini: not configured (optional — rule-based fallback active)")
            return True
        import httpx
        r = httpx.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
            timeout=10,
        )
        if r.status_code == 200:
            print("  ✓ Gemini API key valid")
        else:
            print(f"  ~ Gemini: HTTP {r.status_code} (key may be wrong)")
        return True
    except Exception as exc:
        print(f"  ~ Gemini: {exc} (optional)")
        return True


def main() -> int:
    print("\n=== Incident RCA — Connection Check ===\n")
    pg_ok = _check_postgres()
    redis_ok = _check_redis()
    tables_ok = _check_tables() if pg_ok else False
    _check_gemini()

    print()
    if pg_ok and redis_ok and tables_ok:
        print("✓ All required services are reachable. Ready to run.")
        return 0
    else:
        print("✗ One or more required services are not reachable.")
        if not pg_ok:
            print("  → Fix DATABASE_URL in backend/.env")
        if not redis_ok:
            print("  → Fix REDIS_URL in backend/.env")
        if not tables_ok and pg_ok:
            print("  → Run: cd backend && alembic upgrade head")
        return 1


if __name__ == "__main__":
    sys.exit(main())
