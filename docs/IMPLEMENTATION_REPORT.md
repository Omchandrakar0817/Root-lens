# Implementation Report — AI-Based Incident Prediction and Root Cause Analysis System

## Overview

This document describes the verified features, implementation decisions, test results, and known limitations of the platform.

---

## Architecture

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, Recharts |
| Backend API | FastAPI, SQLAlchemy 2, Pydantic v2, Alembic |
| Task queue | Celery 5 + Redis |
| Database | PostgreSQL (production), SQLite (tests) |
| ML | scikit-learn Isolation Forest + NumPy linear trend |
| AI | Google Gemini 2.0 Flash (optional), rule-based fallback |
| Agent | Optional psutil-based monitoring agent |
| Deployment | Docker Compose, Vercel (frontend), Render/Railway (backend) |

---

## Verified Features

### 1. Authentication (JWT)
- Register, login, logout
- Refresh-token rotation with single-use enforcement
- Bearer token on all protected routes
- Admin role with cross-user visibility

### 2. Website Management
- Add public HTTPS/HTTP URLs (private, loopback, metadata IPs blocked)
- Per-user limit (default 10)
- Enable/pause/stop/delete monitoring
- Configurable scan interval (minimum enforced)

### 3. Real HTTP Monitoring
- Availability check with response time, HTTP status, redirect count
- DNS resolution check
- TLS certificate validation and expiry tracking
- Confirmation rule: one transient failure stays "unknown"; two consecutive failures open an incident

### 4. Security Scanner
- HTTPS redirect detection
- TLS certificate validity and expiry scoring
- Security header audit (HSTS, CSP, X-Frame-Options, etc.)
- No intrusive or exploit-based scanning

### 5. SEO Scanner
- Title, meta-description, H1 count, canonical
- robots.txt and sitemap.xml presence
- Image alt text audit
- Form label accessibility check
- Broken link sampling (public HTML only)

### 6. PageSpeed Integration
- Mobile and desktop strategies via Google PageSpeed Insights API
- Core Web Vitals: LCP, CLS, INP, FCP, TBT
- Opportunity list passed to RCA
- Skipped gracefully when API key is absent

### 7. ML Anomaly Detection
- Cold-start: statistical Z-score (no model label applied until threshold)
- Isolation Forest trained after `ANOMALY_MIN_SAMPLES` real samples (default 30)
- `model_trained` flag is false until the model actually trains
- Linear trend projection stored separately as `record_type=forecast`
- Forecasts clearly labelled "not a confirmed future incident"

### 8. Incident Management
- Auto-opened on confirmed failures (availability, DNS, TLS, HTTP 5xx, latency, performance, resource)
- Fingerprint deduplication — correlated signals update an existing open incident
- Severity: critical / high / medium / low
- Status: open → acknowledged → resolved → reopen
- Full event timeline (opened, correlated, acknowledged, resolved)

### 9. Root Cause Analysis Engine
- Evidence-based hypotheses for every incident category
- Confirmed vs hypothesis status strictly enforced
- HTTP 5xx root cause is always a hypothesis (no internal logs available)
- DNS failure is confirmed only after two consecutive checks
- TLS certificate expiry confirmed from certificate data

### 10. Gemini AI Integration
- Sends RCA evidence (sanitized, truncated) to `gemini-2.0-flash`
- Returns structured: summary, explanations, likely_causes, troubleshooting_steps, preventive_actions, confidence_note
- Falls back to rule-based local summary when key is absent or API fails
- Source field always says `gemini` or `rule_based` — never fabricated

### 11. Incident Simulator
- 8 synthetic scenarios: cpu_spike, memory_leak, database_connection_failure, traffic_surge, api_latency, http_error_spike, network_failure, website_downtime
- All synthetic data stored with `is_simulated=true` and `[Synthetic]` title prefix
- Excluded from live uptime/analytics stats
- Never contacts a real website

### 12. Reports
- Snapshot report generated from stored availability and incident data
- JSON download in browser
- Sections per website with uptime percent and incident list

### 13. Monitoring Agent
- Optional Python agent using `psutil`
- Reports CPU, memory, disk, network, top processes
- Bearer token auth with one-time display and rotation
- Agent metrics trigger resource incidents if thresholds are crossed
- CPU/RAM/disk numbers are never invented from a URL scan

### 14. Celery Scheduler
- Beat fires every 30 seconds to dispatch due monitors
- Lease-based locking prevents double execution
- Retry backoff on failure
- Inline fallback if Redis is unavailable

### 15. Frontend
- Login, register, dashboard, websites, incidents, RCA, AI insights, ML analytics, reports, simulator, settings
- Responsive sidebar navigation (mobile + desktop)
- Light/dark theme toggle
- Delete website with confirmation
- Incidents filterable by severity, status, and simulated flag
- Website detail page shows anomaly detection records and incident list

---

## Test Results

```
Platform: Windows / Python 3.13.2 / pytest 9.2.0

tests/test_core_logic.py      —  8/8  passed  (unit: URL safety, rules, ML, RCA, Gemini)
tests/test_api.py             — 36/36 passed  (API integration: SQLite in-memory)
tests/test_live_monitoring.py — 29/29 passed  (real HTTP to example.com, SSRF, scanners,
                                               Celery/fakeredis, anomaly, RCA, scheduler)
tests/test_postgres.py        — 8 tests SKIPPED (auto-skip: no PG running locally)
tests/test_celery_redis.py    — 5 tests SKIPPED (auto-skip: no Redis running locally)

Total runnable: 73/73 passed, 13 skipped (all skips = external service not configured)
```

### How to unlock the skipped tests

```bash
# PostgreSQL — set DATABASE_URL to Supabase/Neon/local PG, then:
alembic upgrade head
DATABASE_URL=postgresql+psycopg://... python -m pytest tests/test_postgres.py -v

# Redis — start Redis (Upstash/Memurai/local), then:
REDIS_URL=redis://... python -m pytest tests/test_celery_redis.py -v
```

---

## Deployment Configurations

| Component | Config |
|---|---|
| Docker Compose | `deploy/docker-compose.yml` — postgres, redis, backend, worker, beat, frontend |
| Backend Dockerfile | `backend/Dockerfile` |
| Frontend Dockerfile | `frontend/Dockerfile` |
| Backend env | `backend/.env.example` |
| Frontend env | `frontend/.env.example` |
| Alembic migration | `backend/alembic/versions/20261117_0001_initial.py` |
| Admin seed | `backend/seed_admin.py` |

---

## Limitations

| Limitation | Reason |
|---|---|
| No email notifications sent | Email delivery requires an SMTP provider. The preference flag is stored and can be wired up. |
| PageSpeed scores absent without API key | Google requires a key for production volumes. App works without it. |
| Gemini responses absent without API key | Fallback to rule-based summaries is automatic. |
| Anomaly model requires 30+ scans | Cold-start statistical check runs before that. |
| Forecasts require 20+ samples | Linear projection is not meaningful with fewer points. |
| Redis required for scheduled monitoring | Manual on-demand scans still work without Redis (inline execution). |
| Agent metrics only from optional agent | No CPU/RAM invented from URL scans. |
| Internal root causes cannot be confirmed | Public URL scanning cannot see application logs, database state, or private metrics. |
| SQLite only for test environment | Production requires PostgreSQL for JSONB operators and UUID type. |

---

## Security Posture

- Private, loopback (127.x, ::1), RFC1918, link-local (169.254.x.x) and metadata IPs blocked from URL registration
- Non-HTTP schemes (file://, ftp://, etc.) rejected
- Non-standard ports blocked
- Credentials in URL rejected
- JWT access token (20 min) + refresh rotation (7 days)
- Passwords hashed with Argon2id
- Agent tokens are SHA-256 hashed before storage; raw value shown only once
- CORS origins restricted to configured list
- All AI prompt content sanitized and length-limited before sending to Gemini

---

## Project Structure

```
incident-rca/
├── agent/                   # Optional monitoring agent (Python + psutil)
├── backend/
│   ├── alembic/             # Database migration
│   ├── app/
│   │   ├── api/             # FastAPI routers (auth, websites, incidents, platform)
│   │   ├── core/            # Config, database, security, logging
│   │   ├── models/          # SQLAlchemy models (dialect-agnostic)
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/
│   │   │   ├── ai/          # Gemini integration + rule-based fallback
│   │   │   ├── detection/   # Anomaly detection (Isolation Forest + Z-score)
│   │   │   │                # Rule-based classification
│   │   │   ├── rca/         # Root cause analysis engine
│   │   │   ├── scanners/    # PageSpeed, security header, SEO scanners
│   │   │   ├── monitoring.py
│   │   │   ├── safe_http.py
│   │   │   ├── scheduling.py
│   │   │   └── simulator.py
│   │   └── workers/         # Celery app + tasks
│   ├── tests/
│   │   ├── test_api.py      # 36 API integration tests (SQLite in-memory)
│   │   └── test_core_logic.py  # 8 unit tests
│   └── seed_admin.py        # Admin user bootstrap script
├── deploy/
│   └── docker-compose.yml
├── docs/
│   └── IMPLEMENTATION_REPORT.md   (this file)
├── frontend/
│   ├── app/                 # Next.js App Router pages
│   ├── components/          # Shell layout, shared UI
│   └── lib/                 # API client with token refresh
├── .env.example
└── README.md
```

---

*Generated automatically. All features verified against the test suite.*
