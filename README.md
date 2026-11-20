# 🔍 RootLens
### AI-Powered Website Monitoring, Incident Prediction & Root Cause Analysis

**Monitor smarter. Detect earlier. Understand failures. Resolve faster.**

![Next.js](https://img.shields.io/badge/Next.js-Frontend-000000?logo=nextdotjs)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?logo=postgresql)
![Redis](https://img.shields.io/badge/Redis-Task%20Broker-DC382D?logo=redis)
![Gemini](https://img.shields.io/badge/Google%20Gemini-AI%20Insights-4285F4)
![License](https://img.shields.io/badge/License-Not%20Specified-lightgrey)

---

## Overview

**RootLens** is a full-stack, AI-assisted website monitoring and incident management platform designed to help developers understand website health, investigate failures, and identify possible corrective actions.

Traditional uptime monitoring often answers one question: **Is the website available?**

RootLens aims to go further by connecting website monitoring with incident tracking, root cause analysis, AI-generated explanations, and historical performance forecasting.

The platform combines real HTTP monitoring, PostgreSQL-backed incident history, statistical anomaly detection, machine learning, and Google Gemini in a unified dashboard.

### The Problem

Website failures can be difficult to investigate because monitoring data, incident history, performance trends, and troubleshooting information may be scattered across different tools.

Small development teams and individual website owners may need a simpler way to understand:

- Whether a website is currently reachable.
- What error was observed during a failed scan.
- When an incident started and how it progressed.
- Which causes are plausible based on available evidence.
- What actions could help investigate or resolve the issue.
- Whether response-time trends suggest performance degradation.

### Our Approach

RootLens organizes these capabilities into a connected workflow:

**Website Monitoring → Incident Detection → Root Cause Analysis → AI Recommendations → Performance Analytics → Reports**

The platform is designed around observable evidence. It distinguishes confirmed measurements from AI-generated hypotheses and separates real monitoring data from synthetic simulations.

---

## Key Features

### 1. Website Monitoring

Monitor public websites using actual HTTP requests and store the results for historical analysis.

**Capabilities include:**

- Website availability and HTTP status checks.
- Response-time measurements in milliseconds.
- Connection failure and timeout reporting.
- SSL/TLS certificate information.
- Security-header inspection.
- SEO and accessibility-related signals from public HTML.
- Optional Google PageSpeed Insights integration.
- Manual scanning and scheduled background monitoring.
- Website-specific monitoring history.

**Why it matters:** Users can inspect website health without relying solely on a generic healthy/down indicator.

### 2. Intelligent Incident Management

RootLens tracks detected website failures and performance problems as incidents.

**Capabilities include:**

- Incident detection based on monitoring evidence.
- Severity classification.
- Incident timestamps and history.
- Open, acknowledged, and resolved states.
- Website-specific incident views.
- Links between incidents and their analysis results.

**Why it matters:** Monitoring observations become structured records that users can investigate and manage.

### 3. Root Cause Analysis (RCA)

The RCA module helps explain what the monitoring system observed and which underlying causes may be worth investigating.

**Analysis may include:**

- Confirmed HTTP or connection evidence.
- Possible failure causes.
- Confidence information when available.
- Recommended investigation steps.
- Links to related incidents and AI insights.

**Important:** Public URL monitoring cannot establish every internal server cause. RootLens treats unsupported internal explanations as hypotheses rather than confirmed facts.

### 4. Gemini-Powered AI Insights

RootLens integrates Google Gemini to provide understandable explanations and actionable recommendations for real incidents.

AI insights can help users understand:

- What problem was detected.
- What evidence supports the incident.
- Which causes may explain the symptoms.
- Which troubleshooting steps should be considered.
- What preventive actions could reduce recurrence.

The application also supports a rule-based fallback when the external AI service is unavailable.

**AI safety and reliability principles:**

- AI recommendations are not automatically treated as confirmed diagnoses.
- Synthetic incidents do not require Gemini requests.
- Existing analysis can be reused to avoid unnecessary API usage.
- API failures should not prevent access to stored monitoring evidence.

### 5. Machine Learning & Performance Forecasting

RootLens analyzes historical response-time measurements to identify unusual behavior and estimate performance trends.

**Analytics capabilities:**

- Historical response-time visualization.
- Statistical anomaly detection during cold start.
- Isolation Forest-based anomaly detection when sufficient training data is available.
- Linear response-time forecasting.
- Actual versus predicted response-time charts.
- Website-specific sample counts and model status.

**Forecasting requirement:** The existing forecasting workflow requires at least **20 valid real response-time samples per website**.

A forecast is a mathematical projection of observed trends, not a guarantee that an outage will occur.

### 6. Incident Simulation Lab

The simulator provides an isolated environment for demonstrating incident scenarios without affecting real websites.

**Example scenarios:**

- Synthetic CPU spikes.
- Synthetic memory growth.
- Synthetic database connection problems.
- Synthetic traffic surges.
- Synthetic API latency increases.
- Synthetic HTTP error spikes.
- Network and availability-related scenarios.

Simulation data is artificial and intended for testing, education, and demonstration.

**Real incidents and synthetic incidents must remain clearly distinguishable.**

### 7. Reports & Historical Insights

The reporting module summarizes information already stored by the monitoring platform.

Reports may include:

- Monitored websites and latest health observations.
- Response-time measurements.
- Scan history.
- Incident records.
- Root cause analysis.
- Available AI insight records.

Reports should represent actual stored data rather than inventing uptime percentages or missing measurements.

### 8. Unified Dashboard

RootLens provides a centralized interface for navigating between monitored websites, incidents, RCA results, AI insights, analytics, simulations, and reports.

The interface uses a responsive dark-themed dashboard designed to make monitoring information easier to understand.

---

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Next.js | Web application and routing |
| Language | TypeScript | Type-safe frontend development |
| Styling | Tailwind CSS | Responsive UI |
| Visualization | Recharts | Monitoring and forecasting charts |
| Backend | FastAPI | REST API and application logic |
| Backend language | Python | Monitoring, analysis, and integrations |
| ORM | SQLAlchemy | Database access |
| Validation | Pydantic | Request and data validation |
| Database | PostgreSQL / Supabase | Persistent application data |
| Background jobs | Celery | Scheduled and asynchronous processing |
| Message broker | Redis / Upstash | Task coordination |
| Machine learning | scikit-learn | Isolation Forest anomaly detection |
| Generative AI | Google Gemini | Incident explanations and recommendations |
| Performance API | Google PageSpeed Insights | Website performance assessment |

---

## System Architecture

```text
                    ROOTLENS PLATFORM

                     ┌───────────────┐
                     │     User      │
                     │ Web Dashboard │
                     └───────┬───────┘
                             │
                             ▼
                     ┌───────────────┐
                     │    Next.js    │
                     │   Frontend    │
                     └───────┬───────┘
                             │ REST API
                             ▼
                     ┌───────────────┐
                     │    FastAPI    │
                     │    Backend    │
                     └───────┬───────┘
                             │
             ┌───────────────┼───────────────┐
             ▼               ▼               ▼
      ┌────────────┐  ┌────────────┐  ┌────────────┐
      │ PostgreSQL │  │   Redis    │  │   Gemini   │
      │  Supabase  │  │  Upstash   │  │    API     │
      └────────────┘  └──────┬─────┘  └────────────┘
                             │
                             ▼
                      ┌────────────┐
                      │   Celery   │
                      │   Tasks    │
                      └──────┬─────┘
                             │
                             ▼
                      ┌────────────┐
                      │ Monitoring │
                      │  Services  │
                      └────────────┘

Additional services:
- ML anomaly detection and forecasting
- Google PageSpeed Insights
- Optional monitoring agent
- Report generation
```

### Architecture Notes

**Frontend:** Provides authentication screens, monitoring controls, charts, incident workflows, and reporting interfaces.

**Backend:** Coordinates monitoring requests, stores results, manages incidents, and exposes API endpoints.

**Database:** Stores user accounts, monitored websites, measurements, incidents, RCA information, and other application records.

**Celery and Redis:** Support background monitoring and scheduled tasks.

**Gemini:** Provides an optional AI explanation layer for incident investigation.

**ML services:** Analyze historical measurements and generate forecasts when the required conditions are met.

---

## Project Structure

```text
incident-rca/
│
├── agent/
│   ├── monitoring_agent.py
│   ├── requirements.txt
│   └── README.md
│
├── backend/
│   ├── app/
│   ├── alembic/
│   ├── tests/
│   ├── .env.example
│   ├── requirements.txt
│   ├── Dockerfile
│   └── alembic.ini
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── .env.example
│   ├── package.json
│   ├── package-lock.json
│   ├── Dockerfile
│   └── vercel.json
│
├── deploy/
│   ├── docker-compose.yml
│   ├── railway.json
│   └── render.yaml
│
├── docs/
│   ├── SETUP_SERVICES.md
│   └── ...
│
├── .env.example
├── .gitignore
└── README.md
```

---

## Getting Started

### Prerequisites

Install or configure the following:

- Python with pip.
- Node.js and npm.
- PostgreSQL database.
- Redis-compatible service.
- Google Gemini API key (optional).
- Google PageSpeed Insights API key (optional).

For managed services, RootLens can use Supabase PostgreSQL and Upstash Redis.

See [Service Setup](docs/SETUP_SERVICES.md) for additional instructions.

### Step 1 — Clone the Repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd incident-rca
```

Replace `<YOUR_REPOSITORY_URL>` with your actual GitHub repository URL after publishing.

### Step 2 — Configure Environment Variables

Create the backend environment file:

```powershell
Copy-Item backend/.env.example backend/.env
```

Create the frontend environment file:

```powershell
Copy-Item frontend/.env.example frontend/.env.local
```

Configure the required database, Redis, authentication, and API settings using the supplied templates.

Never commit real credentials to GitHub.

**Environment variable guidance:**

| Category | Configuration |
|---|---|
| Database | PostgreSQL connection credentials |
| Authentication | JWT secrets and related settings |
| Redis | Redis connection URL and credentials |
| Gemini | Optional AI API key and supported model |
| PageSpeed | Optional PageSpeed API key |
| Frontend | Public backend API URL |
| CORS | Allowed frontend origins |

Refer to the actual `.env.example` files for the precise variable names.

### Step 3 — Install Backend Dependencies

From the project root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 4 — Check Connections and Apply Migrations

```powershell
python check_connections.py
alembic upgrade head
```

Use migrations against the intended database only. Review migration changes before applying them to production.

### Step 5 — Start FastAPI

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

Backend:

http://localhost:8000

Interactive API documentation:

http://localhost:8000/docs

### Step 6 — Start Celery Worker

In a separate terminal, from the `backend` directory:

```powershell
python -m celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```

### Step 7 — Start Celery Beat

In another terminal, from the `backend` directory:

```powershell
python -m celery -A app.workers.celery_app beat --loglevel=info
```

Celery worker and scheduler processes are required for the corresponding background monitoring tasks.

### Step 8 — Start the Frontend

From the project root, open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the application:

http://localhost:3000

---

## Application Workflow

### Monitoring a Website

1. Register or log in.
2. Open the Websites page.
3. Add a public website URL.
4. Run a monitoring scan.
5. Review actual HTTP status, response time, and other available measurements.
6. Check whether an incident was detected.
7. Open the incident and inspect its RCA evidence.
8. Request AI-assisted recommendations when appropriate.
9. Review historical trends and reports.

### Understanding Forecasting

RootLens collects response-time measurements across scans.

When a website has sufficient valid real measurements, the forecasting module can estimate the direction of its response-time trend.

The dashboard distinguishes historical observations from calculated predictions.

**Example interpretation:**

- Positive slope: response times are trending upward.
- Negative slope: response times are trending downward.
- Near-zero slope: relatively stable linear trend.

These interpretations describe the fitted trend, not a guarantee of future behavior.

---

## Screenshots

Add screenshots from your running application to a folder such as `docs/screenshots/`.

Suggested screenshots:

| Screenshot | Description |
|---|---|
| Dashboard Overview | Website health and monitoring summary |
| Websites | Monitored website list and scan controls |
| Incident Management | Real incident details and status |
| Root Cause Analysis | Evidence and possible causes |
| AI Insights | Gemini-assisted explanations |
| ML Analytics | Response-time history and forecast graph |
| Simulation Lab | Synthetic incident scenarios |
| Reports | Generated monitoring reports |

Once screenshots are committed, embed them using Markdown:

```markdown
![RootLens Dashboard](docs/screenshots/dashboard.png)
```

Do not publish screenshots containing API keys, private account information, access tokens, or other sensitive data.

---

## Deployment

RootLens is structured for separate frontend, backend, database, and background-worker deployments.

### Suggested Hosting Architecture

| Service | Deployment Option |
|---|---|
| Next.js frontend | Vercel |
| FastAPI backend | Render or Railway |
| PostgreSQL | Supabase |
| Redis | Upstash |
| Celery worker | Long-running background service |
| Celery scheduler | Long-running background service |

### Production Checklist

- [ ] Set all production environment variables.
- [ ] Use a secure production JWT secret.
- [ ] Configure the correct frontend API URL.
- [ ] Configure allowed CORS origins.
- [ ] Verify PostgreSQL and Redis connectivity.
- [ ] Apply reviewed database migrations.
- [ ] Deploy the backend API.
- [ ] Deploy the frontend.
- [ ] Configure background workers and scheduling if required.
- [ ] Verify authentication and user-specific data access.
- [ ] Test real website scans and incident creation.
- [ ] Verify AI integration and API quota handling.
- [ ] Verify forecasting with sufficient historical samples.
- [ ] Verify report generation end-to-end.
- [ ] Confirm that synthetic data is excluded from real monitoring statistics.
- [ ] Verify that no secrets or local environment files are committed.

**Deployment note:** Configuration files are included for potential hosting platforms, but each deployment must be configured and verified independently.

---

## Security Considerations

RootLens is intended for authorized monitoring of public websites and connected systems.

### Public Monitoring Limitations

Public URL checks can observe:

- HTTP responses and failures.
- Request latency.
- Public headers.
- Publicly available page content.
- Available TLS certificate information.

They cannot directly observe:

- Internal CPU or memory usage.
- Private database performance.
- Server process state.
- Internal application logs.
- Private network behavior.

Such information requires authorized telemetry sources.

### AI Limitations

Gemini-generated recommendations are investigative guidance, not guaranteed diagnoses.

A timeout may indicate several possible causes, including network connectivity, server unavailability, or request handling problems. It should not be presented as a confirmed HTTP 500 response unless that status was actually observed.

### Operational Safety

- Use authorized targets.
- Respect monitoring intervals and rate limits.
- Do not perform intrusive vulnerability testing.
- Protect API keys and database credentials.
- Review production access permissions.
- Monitor third-party API quotas.

---

## Testing and Validation

The project includes backend tests and frontend type-checking support.

Example commands:

**Backend:**

```powershell
cd backend
python -m pytest
```

**Frontend:**

```powershell
cd frontend
npx tsc --noEmit
npm run build
```

Successful local checks do not automatically prove that all integrations work in production.

Live testing should include database connectivity, background tasks, API integrations, browser workflows, and report generation.

---

## Target Users

RootLens is designed with the following users in mind:

**Individual developers:** Monitor personal websites and investigate failures.

**Freelancers:** Track website health across client projects.

**Small development teams:** Centralize basic monitoring, incidents, and recommendations.

**Students and educators:** Explore incident detection, anomaly analysis, AI-assisted RCA, and safe simulation scenarios.

---

## Future Improvements

Potential future enhancements include:

- Additional notification channels.
- More configurable alert thresholds.
- Expanded monitoring integrations.
- Improved forecasting evaluation and model monitoring.
- More advanced incident correlation.
- Team collaboration and role-based workflows.
- Additional reporting and export options.
- Production observability and operational dashboards.

These are potential enhancements, not claims of currently implemented features.

---

## Project Scope

RootLens is an educational and practical implementation of AI-assisted website monitoring and incident analysis.

It demonstrates how monitoring evidence, incident workflows, statistical analysis, and generative AI can be connected in a single application.

It is not presented as a replacement for enterprise observability systems or as a guarantee of accurate incident prediction.

---

## Project Vision

**Detect → Explain → Predict → Resolve**

RootLens aims to help users move from discovering a website problem to understanding the evidence and choosing appropriate next steps.

**RootLens — Turning Monitoring Data into Actionable Insight.**