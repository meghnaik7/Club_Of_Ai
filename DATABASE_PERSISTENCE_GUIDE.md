# Production Database & Data Persistence Guide for ClubOps AI

This guide explains how data persistence works in ClubOps AI, why PostgreSQL is mandatory for production, and how to deploy with guaranteed persistence across restarts and redeployments.

---

## 1. Why SQLite vs PostgreSQL Matters in Production

| Feature | SQLite (`clubops.db`) | PostgreSQL (Production) |
| :--- | :--- | :--- |
| **Storage Location** | Local container disk file | Dedicated persistent database / Volume |
| **Data Persistence** | ❌ **Lost on restart/redeploy** in Docker, Render, Railway, AWS, or GCP | ✅ **Permanently stored & retained** across restarts |
| **Concurrent Access** | ❌ Locks file during writes (`database is locked` error) | ✅ Multi-worker ACID transactions & row-level locking |
| **Connection Pooling** | ❌ Disabled (`NullPool`) | ✅ High-throughput pool (`pool_size=10`, `max_overflow=20`) |
| **Vector Search (RAG)** | ❌ Not natively supported | ✅ Native `pgvector` vector similarity indexing |

> [!CAUTION]
> If you deploy a container to Render, Railway, AWS ECS, or Fly.io with `DATABASE_URL=sqlite:///./clubops.db`, the container's ephemeral disk is deleted on every deploy or restart. **All users, events, tasks, AI proposals, and feedback will be lost.** 
> Always use **PostgreSQL** in production!

---

## 2. Option A: Production with Docker Compose (VPS / Server)

If you are hosting on an Ubuntu VPS (DigitalOcean, Hetzner, AWS EC2, Linode) or local server with Docker installed:

1. Copy `.env.production` to `.env`:
   ```bash
   cp .env.production .env
   ```
2. Make sure `DATABASE_URL` points to the PostgreSQL container or use the defaults:
   ```env
   DATABASE_URL=postgresql://postgres:your_password@localhost:5433/clubops_ai
   POSTGRES_PORT=5433
   ```
3. Start the entire persistent production stack:
   ```bash
   docker compose up -d
   ```
   This automatically starts:
   - **`clubops_postgres`**: PostgreSQL 15 + `pgvector` with **persistent named volume** `clubops_postgres_data:/var/lib/postgresql/data`.
   - **`clubops_backend`**: FastAPI backend on port `8000`.
   - **`clubops_frontend`**: React + Nginx on port `80`.

4. Check container health:
   ```bash
   docker compose ps
   ```

Data stored in `clubops_postgres_data` will **never be deleted** when you restart containers or run `docker compose down && docker compose up -d`.

---

## 3. Option B: Free Managed Cloud PostgreSQL (Supabase / Neon / Render)

If you are deploying your backend on cloud platforms like **Render**, **Railway**, **Vercel**, **Fly.io**, or **AWS**:

### Recommended Free Providers:
1. **[Supabase](https://supabase.com/)** (Free Tier):
   - Includes PostgreSQL 15 with `pgvector` pre-installed.
   - Go to **Project Settings** → **Database** → **Connection String** → **URI (Transaction Pooler)**:
     ```env
     DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require
     ```
2. **[Neon.tech](https://neon.tech/)** (Free Tier):
   - Serverless PostgreSQL with auto-suspend and instant scaling.
   - Copy the connection string:
     ```env
     DATABASE_URL=postgresql://[user]:[password]@[endpoint].neon.tech/neondb?sslmode=require
     ```
3. **[Render PostgreSQL](https://render.com/)**:
   - Attach a Render PostgreSQL database to your Web Service.
   - Set environment variable `DATABASE_URL` in the Render dashboard.

---

## 4. Production Environment Settings (`.env.production`)

Set the following variables in your production environment:

```env
# Enforces production mode (disables silent SQLite fallback)
ENVIRONMENT=production
ALLOW_SQLITE_FALLBACK=false

# Your persistent PostgreSQL connection string
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<dbname>?sslmode=require

# Connection Pool Settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=300
DB_POOL_TIMEOUT=30.0

# Security Key
SECRET_KEY=replace-with-a-secure-random-64-char-string
ACCESS_TOKEN_EXPIRE_MINUTES=60

# AI Models & Observability
OPENROUTER_API_KEY=sk-or-v1-...
PRIMARY_LLM_PROVIDER=openrouter
PRIMARY_LLM_MODEL=openai/gpt-4o-mini
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_PROJECT=ClubOps-AI
```

---

## 5. Automatic Schema Initialization on Startup

When the application boots in production:
1. `init_db()` is automatically executed during the FastAPI startup event.
2. It sends a `SELECT 1` ping to ensure PostgreSQL is online.
3. It creates all tables:
   - `users`, `teams`, `clubs`, `permissions`
   - `events`, `tasks`, `volunteers`, `announcements`
   - `ai_proposals`, `ai_proposal_changes`, `ai_feedback`
   - `audit_logs`, `documents`, `document_chunks`, `past_lessons`
4. It auto-migrates missing columns and seeds default permissions.

---

## 6. Verifying Persistence

Run the verification tool to confirm your database is production-ready:

```bash
python scripts/test_postgres_connection.py
```

The script will:
- [x] Test the connection to PostgreSQL.
- [x] Verify all 14+ core tables and indexes exist.
- [x] Perform a live **Write → Commit → Separate Session Read** test to prove data persists across connections.
- [x] Verify `pgvector` extension readiness for RAG embeddings.

---

## 7. Backups and Disaster Recovery

### Creating a Database Backup:
```bash
pg_dump -d "$DATABASE_URL" -F c -b -v -f clubops_backup_$(date +%Y%m%d).dump
```

### Restoring from Backup:
```bash
pg_restore -d "$DATABASE_URL" -v clubops_backup_YYYYMMDD.dump
```
