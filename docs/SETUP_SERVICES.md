# Setup Guide — External Services (PostgreSQL + Redis)

This project requires **PostgreSQL** and **Redis**. Neither runs on this machine yet.
Follow the fastest free path below.

---

## Option A — Supabase (PostgreSQL, free, 2 minutes)

1. Go to <https://supabase.com> → "Start your project" → sign in with GitHub.
2. Click **New Project** → pick a region close to you → set a database password → **Create project**.
3. Wait ~1 minute for provisioning.
4. Go to **Project Settings → Database → Connection String → URI (psycopg / Python)**.  
   It looks like:
   ```
   postgresql+psycopg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
5. Open `incident-rca/backend/.env` and set:
   ```
   DATABASE_URL=postgresql+psycopg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```

---

## Option B — Neon (PostgreSQL, free, 2 minutes)

1. Go to <https://neon.tech> → Sign up → **New Project**.
2. Copy the **Connection string** from the dashboard.  
   Change the driver prefix from `postgresql://` to `postgresql+psycopg://`.
3. Set `DATABASE_URL=...` in `backend/.env`.

---

## Option C — Local PostgreSQL (if you install it)

Download from <https://www.postgresql.org/download/windows/> (use the installer).  
After install, the default `.env` value works as-is:
```
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/incident_rca
```
Then create the DB:
```bat
psql -U postgres -c "CREATE DATABASE incident_rca;"
```

---

## Redis

### Option A — Upstash (managed Redis, free)

1. Go to <https://upstash.com> → Sign up → **Create Database** → choose region.
2. Copy the **Redis URL** (starts with `redis://default:...@...upstash.io:...`).
3. Set in `backend/.env`:
   ```
   REDIS_URL=redis://default:[token]@[host].upstash.io:[port]
   CELERY_BROKER_URL=redis://default:[token]@[host].upstash.io:[port]/0
   CELERY_RESULT_BACKEND=redis://default:[token]@[host].upstash.io:[port]/1
   ```

### Option B — Local Redis on Windows (Memurai)

1. Download **Memurai** (Redis-compatible for Windows):  
   <https://www.memurai.com/get-memurai>
2. Install and start. It runs on `localhost:6379` — no password needed.
3. The default `.env` value works:
   ```
   REDIS_URL=redis://localhost:6379/0
   ```

---

## After configuring both services

```bat
cd incident-rca\backend

# 1. Verify connections
python check_connections.py

# 2. If Postgres connected but tables missing, run migrations
alembic upgrade head

# 3. Create admin user (optional)
set ADMIN_EMAIL=admin@example.com
set ADMIN_PASSWORD=changeme123
python seed_admin.py

# 4. Start API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. Start Celery worker (new terminal)
celery -A app.workers.celery_app worker --loglevel=info

# 6. Start Celery beat (new terminal)
celery -A app.workers.celery_app beat --loglevel=info

# 7. Start frontend (new terminal)
cd ..\frontend
npm run dev
```

Then open <http://localhost:3000>.

---

## Verify everything is working

```bat
# In backend directory
python check_connections.py
```

Expected output:
```
=== Incident RCA — Connection Check ===

  ✓ PostgreSQL connected: PostgreSQL 16...
  ✓ Redis connected: PING=True
  ✓ All 20 tables present
  ~ Gemini: not configured (optional — rule-based fallback active)

✓ All required services are reachable. Ready to run.
```
