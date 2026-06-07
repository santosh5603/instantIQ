# TECH_STACK.md — Reelise
**Version:** 1.0.0
**Status:** MVP
**Last Updated:** 2025

---

## Table of Contents

1. [Stack Overview](#1-stack-overview)
2. [Frontend](#2-frontend)
3. [Backend](#3-backend)
4. [Automation Layer](#4-automation-layer)
5. [Database](#5-database)
6. [Queue System](#6-queue-system)
7. [Storage](#7-storage)
8. [Notion Integration](#8-notion-integration)
9. [Infrastructure & Deployment](#9-infrastructure--deployment)
10. [Containerization](#10-containerization)
11. [Monitoring & Logging](#11-monitoring--logging)
12. [Dependencies & Versions](#12-dependencies--versions)
13. [Environment Configuration](#13-environment-configuration)
14. [Alternatives Considered](#14-alternatives-considered)
15. [Stack Decision Rationale](#15-stack-decision-rationale)

---

## 1. Stack Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        REELISE STACK                        │
├─────────────────┬───────────────────────────────────────────┤
│ Layer           │ Technology                                 │
├─────────────────┼───────────────────────────────────────────┤
│ Frontend        │ Next.js 14 + TypeScript + TailwindCSS     │
│ UI Components   │ shadcn/ui                                  │
│ Backend API     │ FastAPI (Python 3.12)                      │
│ Automation      │ Playwright (Python)                        │
│ Database        │ Supabase PostgreSQL                        │
│ Queue           │ Redis (via Upstash or self-hosted)         │
│ Storage         │ Supabase Storage                           │
│ ORM             │ SQLAlchemy 2.0                             │
│ Validation      │ Pydantic v2                                │
│ Migrations      │ Alembic                                    │
│ Interface Layer │ Notion API                                 │
│ Containers      │ Docker + Docker Compose                    │
│ Frontend Deploy │ Vercel                                     │
│ Backend Deploy  │ Railway                                    │
│ Worker Deploy   │ Google Cloud VM (Ubuntu)                   │
└─────────────────┴───────────────────────────────────────────┘
```

---

## 2. Frontend

### Framework: Next.js 14 (App Router)
**Version:** `14.x`
**Why:** App Router enables React Server Components for fast initial loads. File-based routing simplifies dashboard page structure. API routes handle lightweight backend proxying. Strong ecosystem alignment with Vercel deployment.

**Key Patterns Used:**
- App Router (`/app` directory)
- React Server Components for static dashboard shells
- Client Components (`"use client"`) for interactive widgets
- Server Actions for lightweight mutations

### Language: TypeScript 5.x
**Why:** Type safety across API response shapes, component props, and Supabase query results. Catches reel status enum mismatches at compile time. Essential for maintainability in a system with complex state transitions.

### Styling: TailwindCSS 3.x
**Why:** Utility-first CSS eliminates context-switching. JIT compiler keeps bundle small. Perfect for a data-heavy dashboard with consistent spacing and color conventions.

**Configuration:**
```js
// tailwind.config.ts
theme: {
  extend: {
    colors: {
      brand: { /* custom palette */ },
      status: {
        pending: '#F59E0B',
        processing: '#3B82F6',
        completed: '#10B981',
        failed: '#EF4444',
      }
    },
    fontFamily: {
      sans: ['var(--font-geist-sans)'],
      mono: ['var(--font-geist-mono)'],
    }
  }
}
```

### UI Components: shadcn/ui
**Why:** Not a component library — it's a collection of copy-pasteable, fully customizable components built on Radix UI. Zero bundle overhead from unused components. Perfect for a custom dashboard aesthetic. Full TypeScript support.

**Components Used:**
- `Table` — reel history, resource list
- `Badge` — status indicators
- `Card` — dashboard metric tiles
- `Dialog` — reel detail modals
- `Command` — search interface
- `Select` — filter dropdowns
- `Skeleton` — loading states
- `Toast` — action feedback
- `Separator`, `ScrollArea`, `Tooltip`

### State Management
**Primary:** React Query (TanStack Query v5) for server state
**Secondary:** React `useState`/`useReducer` for local UI state
**No Zustand/Redux** — unnecessary for single-user dashboard

### HTTP Client: Axios
**Why:** Interceptor support for auth headers, request/response logging. Familiar API with good TypeScript types.

---

## 3. Backend

### Framework: FastAPI
**Version:** `0.111.x`
**Why:** Async-first Python framework. Automatic OpenAPI docs. Pydantic-native request/response validation. Excellent performance for I/O-bound workloads (queue operations, Supabase queries). Python ecosystem access for automation utilities.

**Key Features Used:**
- `APIRouter` for modular route organization
- Background tasks for lightweight async operations
- Lifespan events for startup/shutdown hooks
- Dependency injection for DB sessions, auth guards
- Exception handlers for standardized error responses

### Language: Python 3.12+
**Why:** Latest stable Python with performance improvements. Required for Playwright Python. Asyncio improvements in 3.12 benefit FastAPI worker management.

### ORM: SQLAlchemy 2.0
**Why:** Async support via `AsyncSession`. Declarative models with type annotations. Excellent Alembic migration integration. Proven production reliability.

**Pattern:**
```python
# Async session with dependency injection
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

### Validation: Pydantic v2
**Why:** v2 is 5–50x faster than v1. Used for request/response schemas, environment variable parsing, and CTA detection models. Native FastAPI integration.

### Migrations: Alembic
**Why:** Industry standard for SQLAlchemy migrations. Auto-generates migration scripts from model changes. Essential for production database evolution.

### HTTP Client: HTTPX
**Why:** Async-native HTTP client. Used for Notion API calls, Supabase REST calls, and inter-service communication. Drop-in replacement for requests with async support.

---

## 4. Automation Layer

### Browser Automation: Playwright (Python)
**Version:** `1.44.x`
**Why:** More reliable than Selenium for modern SPAs. Chromium-based with full JavaScript execution. Superior session persistence via `browser_context.storage_state()`. Better stealth capabilities than Selenium. Active development and excellent Python bindings.

**Key Features Used:**
- `BrowserContext` with persistent storage state for session management
- `Page.wait_for_selector()` for dynamic content
- Network interception for request monitoring
- Stealth configuration to minimize automation detection
- Screenshot on failure for debugging

**Session Management Strategy:**
```python
# Session saved after manual login
await context.storage_state(path="session/instagram_session.json")

# Session restored on worker start
context = await browser.new_context(
    storage_state="session/instagram_session.json"
)
```

**Anti-Detection Measures:**
- User agent rotation (consistent, not random)
- Randomized action delays (human-like)
- Disable automation flags in Chromium args
- Realistic viewport sizes
- No headless mode on production VM (use Xvfb display)

### Worker Architecture
- Each worker is a long-running Python process
- Workers pull jobs from Redis queue
- Workers use a single persistent browser context
- Browser opens only when job is processing
- Browser context closed after idle timeout (5 minutes)

---

## 5. Database

### Primary Database: Supabase PostgreSQL
**Version:** PostgreSQL 15 (Supabase managed)
**Why:** Managed PostgreSQL eliminates ops overhead. Built-in REST API via PostgREST. Row-level security for future multi-user expansion. Realtime subscriptions available for live dashboard updates. Generous free tier.

**Access Pattern:** SQLAlchemy async ORM for all backend operations. Supabase client SDK only for storage operations.

**Full-Text Search:**
```sql
-- Search index on reels and resources
CREATE INDEX reels_search_idx ON reels
USING GIN(to_tsvector('english', coalesce(caption,'') || ' ' || coalesce(creator_name,'')));

CREATE INDEX resources_search_idx ON dm_resources
USING GIN(to_tsvector('english', coalesce(resource_text,'') || ' ' || coalesce(resource_url,'')));
```

**Connection Pooling:** PgBouncer via Supabase connection pooler (`?pgbouncer=true` in DATABASE_URL)

### Schema Overview
```
reels                    → core reel records
dm_resources             → extracted DM content
creator_relationships    → follow tracking
process_logs             → pipeline step audit trail
```

---

## 6. Queue System

### Queue: Redis
**Deployment Option A:** Upstash Redis (serverless, free tier: 10,000 requests/day)
**Deployment Option B:** Self-hosted Redis on Google Cloud VM

**Why Redis:**
- Sub-millisecond latency for queue operations
- Simple list-based queue primitives (`LPUSH`, `BRPOP`)
- Persistence via RDB/AOF snapshots
- Lightweight — runs on same VM as automation worker

**Queue Names:**
```
reelise:reel_queue        → New reels pending CTA detection
reelise:comment_queue     → Reels ready for comment action
reelise:resource_queue    → Post-comment DM monitoring jobs
reelise:retry_queue       → Failed jobs awaiting retry
reelise:notion_sync_queue → Resources pending Notion sync
```

**Python Client:** `redis-py` with asyncio support (`redis.asyncio`)

**Job Payload Structure:**
```json
{
  "job_id": "uuid",
  "reel_id": "uuid",
  "job_type": "process_reel",
  "payload": {},
  "attempt": 1,
  "max_attempts": 3,
  "created_at": "ISO8601"
}
```

---

## 7. Storage

### File Storage: Supabase Storage
**Why:** Integrated with Supabase database. S3-compatible API. Free tier: 1GB. No additional service to manage.

**Buckets:**
```
reelise-resources/     → Downloaded PDFs, media files
reelise-sessions/      → Playwright session files (private)
reelise-screenshots/   → Debug screenshots from failures
```

**Access Pattern:**
- Public bucket for resources (direct URL in Notion)
- Private bucket for session files (backend only)

---

## 8. Notion Integration

### Notion API (Official)
**Version:** `2022-06-28` (latest stable)
**Client:** `notion-client` Python SDK

**Why Notion as Interface:**
- Rich database views (gallery, board, calendar)
- Existing user familiarity
- Zero frontend build required for knowledge browsing
- Excellent mobile app for resource access on the go
- Relation and rollup properties for knowledge linking

**Database Schema in Notion:**
```
Resources Database:
  - Name (title)
  - Category (select): AI, Career, Programming, Fitness, Communication, Other
  - Resource Type (select): Link, PDF, Text, Media
  - URL (url)
  - Creator (text)
  - Reel Caption (text)
  - Status (select): Unread, Reading, Done, Archived
  - Received At (date)
  - Source Reel (url)
  - File (files)
```

**Sync Strategy:**
- One-way sync: Supabase → Notion
- Notion is display layer only, not source of truth
- Sync triggered after `dm_resources` record created
- Idempotent: check for existing Notion page by `reel_id` before creating

---

## 9. Infrastructure & Deployment

### Frontend: Vercel
**Plan:** Hobby (free) or Pro ($20/month)
**Why:** Zero-config Next.js deployment. Automatic preview deployments. Edge network for global performance. Native environment variable management.

### Backend: Railway
**Plan:** Starter ($5/month)
**Why:** Simple Docker-based deployment. Automatic HTTPS. Environment variable UI. Built-in metrics. No server management required.

**Services on Railway:**
- `reelise-api` — FastAPI application
- `reelise-redis` — Redis instance (or use Upstash)

### Automation Worker: Google Cloud VM
**Machine Type:** `e2-micro` (free tier eligible, 2 vCPU, 1GB RAM)
**OS:** Ubuntu 22.04 LTS
**Why:** Always-on Linux environment required for Playwright. Persistent file system for session storage. Free tier coverage for low-traffic personal use.

**VM Setup:**
- Docker + Docker Compose
- Xvfb virtual display for non-headless Playwright
- Systemd service for auto-restart on crash
- UFW firewall (only allow outbound + SSH)

### Database: Supabase
**Plan:** Free tier (500MB DB, 1GB storage, 50MB file size limit)
**Region:** Choose closest to Google Cloud VM region

---

## 10. Containerization

### Docker
**Version:** `26.x`

**Images:**
```dockerfile
# Backend
FROM python:3.12-slim
# FastAPI + SQLAlchemy + all deps

# Automation Worker
FROM python:3.12-slim
# Playwright + Chromium + worker deps

# Frontend (local dev only — Vercel handles prod)
FROM node:20-alpine
```

### Docker Compose
**Purpose:** Local development orchestration

```yaml
services:
  api:          # FastAPI backend
  worker:       # Playwright automation worker
  redis:        # Redis queue
  frontend:     # Next.js (local dev)
```

**Production:** Docker Compose used on Google Cloud VM for worker + Redis (if self-hosted).

---

## 11. Monitoring & Logging

### Logging: Python `logging` module
**Format:** Structured JSON logs
**Levels:** DEBUG (dev), INFO (prod), WARNING, ERROR, CRITICAL
**Storage:** stdout → Railway/GCP log aggregation

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "timestamp": self.formatTime(record),
        })
```

### Health Endpoints
```
GET /health           → API status, DB connectivity, Redis connectivity
GET /health/worker    → Automation worker heartbeat
GET /health/queue     → Redis queue depths
```

### Process Logging (Database)
- Every automation step writes to `process_logs` table
- Queryable from dashboard
- Retention: 90 days

### Alerting (V1)
- No external alerting service in V1
- Failed jobs surface in dashboard logs
- Worker restart via systemd on crash

---

## 12. Dependencies & Versions

### Backend (`requirements.txt`)
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
playwright==1.44.0
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0           # async PostgreSQL driver
pydantic==2.7.0
pydantic-settings==2.2.1
redis[hiredis]==5.0.4
notion-client==2.2.1
supabase==2.4.3
python-dotenv==1.0.1
alembic==1.13.1
httpx==0.27.0
python-multipart==0.0.9
tenacity==8.3.0            # retry logic
structlog==24.1.0          # structured logging
```

### Frontend (`package.json`)
```json
{
  "dependencies": {
    "next": "14.2.3",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "typescript": "5.4.5",
    "@tanstack/react-query": "5.37.1",
    "axios": "1.7.2",
    "tailwindcss": "3.4.3",
    "class-variance-authority": "0.7.0",
    "clsx": "2.1.1",
    "tailwind-merge": "2.3.0",
    "lucide-react": "0.378.0",
    "date-fns": "3.6.0",
    "recharts": "2.12.7",
    "@radix-ui/react-*": "latest"
  }
}
```

---

## 13. Environment Configuration

### Backend `.env`
```env
# Application
APP_ENV=production
APP_SECRET_KEY=<random-64-char-string>
API_PORT=8000

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@db.supabase.co:5432/postgres
DATABASE_POOL_SIZE=5

# Redis
REDIS_URL=redis://localhost:6379/0

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=<key>
SUPABASE_SERVICE_KEY=<service-key>
SUPABASE_STORAGE_BUCKET=reelise-resources

# Instagram Collector Account
INSTAGRAM_USERNAME=<collector_account>
INSTAGRAM_PASSWORD=<collector_password>
INSTAGRAM_SESSION_PATH=/app/session/instagram_session.json

# Notion
NOTION_API_KEY=<integration-token>
NOTION_RESOURCES_DB_ID=<database-id>

# Worker Config
MAX_DAILY_FOLLOWS=10
FOLLOW_COOLDOWN_SECONDS=300
COMMENT_DELAY_MIN=10
COMMENT_DELAY_MAX=30
DM_POLL_INTERVAL=60
DM_MAX_WAIT_MINUTES=30
```

### Frontend `.env.local`
```env
NEXT_PUBLIC_API_URL=https://api.reelise.railway.app
NEXT_PUBLIC_APP_NAME=Reelise
```

---

## 14. Alternatives Considered

### Browser Automation

| Option | Considered | Decision |
|---|---|---|
| Selenium | Yes | Rejected — slower, worse session management |
| Puppeteer (Node) | Yes | Rejected — Python preferred for backend alignment |
| Playwright (Python) | ✅ Chosen | Best stealth, session persistence, async support |
| Instagram Private API | Yes | Rejected — higher detection risk, TOS violation |

### Database

| Option | Considered | Decision |
|---|---|---|
| PlanetScale (MySQL) | Yes | Rejected — no native FTS, MySQL dialect |
| Railway PostgreSQL | Yes | Rejected — no managed backups on free tier |
| Supabase PostgreSQL | ✅ Chosen | Managed, free tier, Storage included, FTS |
| SQLite | Yes | Rejected — no concurrent access, not production |

### Queue

| Option | Considered | Decision |
|---|---|---|
| Celery + Redis | Yes | Rejected — overkill for single-user MVP |
| BullMQ (Node) | Yes | Rejected — Python ecosystem mismatch |
| Redis Lists (custom) | ✅ Chosen | Simple, lightweight, sufficient for V1 |
| Amazon SQS | Yes | Rejected — cost, complexity |

### Interface Layer

| Option | Considered | Decision |
|---|---|---|
| Custom Next.js dashboard only | Yes | Partially used — minimal dashboard |
| Notion only | Yes | Rejected — no real-time status |
| Airtable | Yes | Rejected — API limitations |
| Notion + Custom Dashboard | ✅ Chosen | Notion for knowledge, custom for pipeline status |

### Backend Framework

| Option | Considered | Decision |
|---|---|---|
| Django | Yes | Rejected — too heavy for API-only service |
| Flask | Yes | Rejected — no native async, manual validation |
| FastAPI | ✅ Chosen | Async, Pydantic-native, auto-docs, lightweight |
| Express (Node) | Yes | Rejected — Python preferred for Playwright alignment |

---

## 15. Stack Decision Rationale

### Why This Stack Works for Reelise Specifically

**Python end-to-end (Backend + Automation):**
Playwright Python, FastAPI, SQLAlchemy, and Redis all in Python means one language, one dependency management system, shared utilities, and a single Docker image lineage. No context switching.

**Supabase as foundation:**
For a single-user personal tool, Supabase provides PostgreSQL + Storage + REST API + realtime in one free-tier service. Zero infrastructure management.

**Redis for queue (not Celery):**
Celery is powerful but heavyweight. For a personal tool processing 1–20 reels per day, simple Redis list operations are sufficient. Reduces complexity by ~60%.

**Notion as interface (not custom frontend):**
Building a rich knowledge management UI would take weeks. Notion provides gallery views, board views, search, mobile app, and relations out of the box. The custom frontend only needs to show pipeline status — which is simple.

**Vercel + Railway split:**
Next.js on Vercel is zero-config. FastAPI on Railway is near-zero-config. Both have free/cheap tiers. Google Cloud VM for automation because it needs a persistent, stateful environment with a display server — serverless won't work for Playwright.

---

*Document Version: 1.0.0 | Reelise MVP*
