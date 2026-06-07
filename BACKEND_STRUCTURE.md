# BACKEND_STRUCTURE.md — Reelise
**Version:** 1.0.0
**Status:** MVP
**Last Updated:** 2025

---

## Table of Contents

1. [Folder Architecture](#1-folder-architecture)
2. [FastAPI Application Structure](#2-fastapi-application-structure)
3. [API Endpoint Reference](#3-api-endpoint-reference)
4. [Database Schema](#4-database-schema)
5. [SQLAlchemy Models](#5-sqlalchemy-models)
6. [Pydantic Schemas](#6-pydantic-schemas)
7. [Queue System Design](#7-queue-system-design)
8. [Worker Architecture](#8-worker-architecture)
9. [Playwright Session Management](#9-playwright-session-management)
10. [CTA Detection Engine](#10-cta-detection-engine)
11. [Retry System](#11-retry-system)
12. [Logging Strategy](#12-logging-strategy)
13. [Error Handling](#13-error-handling)
14. [Notion Sync Service](#14-notion-sync-service)
15. [Environment Variables](#15-environment-variables)
16. [Deployment Architecture](#16-deployment-architecture)

---

## 1. Folder Architecture

```
reelise/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    ← FastAPI app, lifespan, middleware
│   │   ├── config.py                  ← Pydantic Settings, env loading
│   │   ├── database.py                ← SQLAlchemy async engine + session
│   │   ├── dependencies.py            ← FastAPI dependency injection
│   │   │
│   │   ├── models/                    ← SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── base.py                ← Base declarative class
│   │   │   ├── reel.py
│   │   │   ├── dm_resource.py
│   │   │   ├── creator_relationship.py
│   │   │   └── process_log.py
│   │   │
│   │   ├── schemas/                   ← Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── reel.py
│   │   │   ├── resource.py
│   │   │   ├── creator.py
│   │   │   ├── log.py
│   │   │   ├── analytics.py
│   │   │   └── common.py              ← Shared types (pagination, APIResponse)
│   │   │
│   │   ├── routers/                   ← FastAPI route handlers
│   │   │   ├── __init__.py
│   │   │   ├── reels.py
│   │   │   ├── resources.py
│   │   │   ├── creators.py
│   │   │   ├── logs.py
│   │   │   ├── search.py
│   │   │   ├── analytics.py
│   │   │   └── health.py
│   │   │
│   │   ├── services/                  ← Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── reel_service.py
│   │   │   ├── resource_service.py
│   │   │   ├── creator_service.py
│   │   │   ├── log_service.py
│   │   │   ├── search_service.py
│   │   │   ├── analytics_service.py
│   │   │   └── notion_service.py
│   │   │
│   │   └── queue/                     ← Redis queue interface
│   │       ├── __init__.py
│   │       ├── client.py              ← Redis connection
│   │       ├── producer.py            ← Push jobs to queue
│   │       └── consumer.py            ← Pull jobs from queue
│   │
│   ├── alembic/
│   │   ├── alembic.ini
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   │
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env
│
├── automation/
│   ├── __init__.py
│   ├── config.py                      ← Automation-specific settings
│   │
│   ├── playwright/
│   │   └── instagram/
│   │       ├── __init__.py
│   │       ├── session.py             ← Session load/save/validate
│   │       ├── dm_listener.py         ← Inbox monitoring
│   │       ├── reel_extractor.py      ← Open reel, extract caption
│   │       ├── follow_agent.py        ← Follow creator action
│   │       ├── comment_agent.py       ← Post comment action
│   │       └── dm_monitor.py          ← Monitor DMs after comment
│   │
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── base_worker.py             ← Abstract base worker
│   │   ├── dm_listener_worker.py      ← Main DM polling worker
│   │   ├── reel_worker.py             ← Reel processing worker
│   │   └── notion_sync_worker.py      ← Notion sync worker
│   │
│   ├── resource_processor/
│   │   ├── __init__.py
│   │   ├── extractor.py               ← Parse DM content
│   │   ├── downloader.py              ← Download files
│   │   └── storage.py                 ← Upload to Supabase Storage
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── cta_detector.py            ← CTA pattern matching
│   │   ├── delays.py                  ← Human-like timing utilities
│   │   ├── logger.py                  ← Structured logger
│   │   └── http_client.py             ← Shared HTTPX client
│   │
│   ├── scripts/
│   │   ├── manual_login.py            ← One-time login script
│   │   └── test_session.py            ← Validate saved session
│   │
│   ├── session/                       ← Git-ignored, persisted volume
│   │   └── .gitkeep
│   │
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env
│
└── docker-compose.yml                 ← Local dev orchestration
```

---

## 2. FastAPI Application Structure

### `main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import reels, resources, creators, logs, search, analytics, health
from app.database import init_db
from app.queue.client import get_redis_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    redis = await get_redis_client()
    app.state.redis = redis
    yield
    # Shutdown
    await redis.aclose()

app = FastAPI(
    title="Reelise API",
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://reelise.vercel.app", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router, tags=["health"])
app.include_router(reels.router, prefix="/api/v1/reels", tags=["reels"])
app.include_router(resources.router, prefix="/api/v1/resources", tags=["resources"])
app.include_router(creators.router, prefix="/api/v1/creators", tags=["creators"])
app.include_router(logs.router, prefix="/api/v1/logs", tags=["logs"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
```

### `config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_ENV: str = "development"
    APP_SECRET_KEY: str
    API_PORT: int = 8000

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_STORAGE_BUCKET: str = "reelise-resources"

    # Notion
    NOTION_API_KEY: str
    NOTION_RESOURCES_DB_ID: str

    # Instagram Worker Config
    INSTAGRAM_USERNAME: str
    INSTAGRAM_PASSWORD: str
    INSTAGRAM_SESSION_PATH: str = "/app/session/instagram_session.json"
    MAX_DAILY_FOLLOWS: int = 10
    FOLLOW_COOLDOWN_SECONDS: int = 300
    COMMENT_DELAY_MIN: int = 10
    COMMENT_DELAY_MAX: int = 30
    DM_POLL_INTERVAL_MIN: int = 45
    DM_POLL_INTERVAL_MAX: int = 90
    DM_MAX_WAIT_MINUTES: int = 30

settings = Settings()
```

---

## 3. API Endpoint Reference

### Health

```
GET  /health                 → System health (DB, Redis, worker heartbeat)
GET  /health/queue           → Redis queue depths
GET  /health/worker          → Automation worker status
```

### Reels

```
GET  /api/v1/reels                   → List reels (paginated, filterable)
GET  /api/v1/reels/{id}              → Single reel detail
GET  /api/v1/reels/{id}/logs         → Process logs for a reel
GET  /api/v1/reels/{id}/resources    → Resources linked to a reel
POST /api/v1/reels/{id}/retry        → Manually retry failed reel
```

#### Query Parameters (GET /reels)
```
status       → filter by status enum
creator_name → filter by creator
requires_cta → boolean filter
page         → pagination (default: 1)
per_page     → items per page (default: 20, max: 100)
sort         → created_at_desc | created_at_asc | status
```

### Resources

```
GET  /api/v1/resources               → List resources (paginated)
GET  /api/v1/resources/{id}          → Single resource detail
PATCH /api/v1/resources/{id}         → Update resource (status, category)
```

#### Query Parameters (GET /resources)
```
resource_type → link | pdf | text | media
category      → AI | Career | Programming | Fitness | Communication | Other
creator_name  → filter by creator
page / per_page
sort          → received_at_desc | received_at_asc
```

### Creators

```
GET  /api/v1/creators                → List creator relationships
GET  /api/v1/creators/{name}         → Single creator detail
```

### Logs

```
GET  /api/v1/logs                    → All process logs (paginated)
GET  /api/v1/logs?reel_id={id}       → Logs for specific reel
GET  /api/v1/logs?status=error       → Error logs only
```

### Search

```
GET  /api/v1/search?q={query}        → Full-text search across reels + resources
GET  /api/v1/search?q={q}&type=reels → Search reels only
GET  /api/v1/search?q={q}&type=resources → Search resources only
```

### Analytics

```
GET  /api/v1/analytics/summary       → Aggregate metrics (total counts, rates)
GET  /api/v1/analytics/timeline      → Processing volume over time
GET  /api/v1/analytics/categories    → Resource breakdown by category
GET  /api/v1/analytics/creators      → Top creators by resource count
```

### Standard Response Envelope

```python
# All list endpoints return:
{
  "data": [...],
  "meta": {
    "total": 47,
    "page": 1,
    "per_page": 20,
    "total_pages": 3
  }
}

# All single-item endpoints return:
{
  "data": { ... }
}

# All error responses return:
{
  "detail": "Human-readable error message",
  "code": "MACHINE_READABLE_CODE",
  "timestamp": "2025-01-01T00:00:00Z"
}
```

---

## 4. Database Schema

### SQL DDL

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For full-text search

-- ─────────────────────────────────────────
-- TABLE: reels
-- ─────────────────────────────────────────
CREATE TABLE reels (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reel_url          TEXT NOT NULL UNIQUE,
    creator_name      TEXT,
    caption           TEXT,
    requires_comment  BOOLEAN DEFAULT FALSE,
    requires_follow   BOOLEAN DEFAULT FALSE,
    requires_dm       BOOLEAN DEFAULT FALSE,
    comment_keyword   TEXT,
    dm_keyword        TEXT,
    cta_confidence    FLOAT,
    commented         BOOLEAN DEFAULT FALSE,
    comment_posted_at TIMESTAMPTZ,
    followed          BOOLEAN DEFAULT FALSE,
    followed_at       TIMESTAMPTZ,
    status            TEXT NOT NULL DEFAULT 'pending',
    -- Status enum: pending, extracting_caption, cta_detected, no_cta,
    --              awaiting_follow, following, awaiting_comment,
    --              commenting, commented, waiting_dm, dm_received,
    --              extracting_resource, completed, failed, dm_timeout, retrying
    error_message     TEXT,
    retry_count       INT DEFAULT 0,
    notion_synced     BOOLEAN DEFAULT FALSE,
    notion_page_id    TEXT,
    dm_message_id     TEXT,  -- Instagram DM message ID (dedup)
    processed_at      TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_reels_status       ON reels (status);
CREATE INDEX idx_reels_creator      ON reels (creator_name);
CREATE INDEX idx_reels_created_at   ON reels (created_at DESC);
CREATE INDEX idx_reels_dm_msg_id    ON reels (dm_message_id);

-- Full-text search index
CREATE INDEX idx_reels_fts ON reels
    USING GIN (to_tsvector('english',
        COALESCE(caption, '') || ' ' ||
        COALESCE(creator_name, '') || ' ' ||
        COALESCE(comment_keyword, '')
    ));

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER reels_updated_at
    BEFORE UPDATE ON reels
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ─────────────────────────────────────────
-- TABLE: dm_resources
-- ─────────────────────────────────────────
CREATE TABLE dm_resources (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reel_id         UUID NOT NULL REFERENCES reels(id) ON DELETE CASCADE,
    resource_type   TEXT NOT NULL,
    -- Type enum: link | pdf | text | media | unknown
    resource_url    TEXT,
    resource_text   TEXT,
    attachment_path TEXT,  -- Supabase Storage path
    file_name       TEXT,
    file_size_bytes INT,
    category        TEXT DEFAULT 'Other',
    -- Category enum: AI | Career | Programming | Fitness | Communication | Other
    notion_page_id  TEXT,
    notion_synced   BOOLEAN DEFAULT FALSE,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_resources_reel_id     ON dm_resources (reel_id);
CREATE INDEX idx_resources_type        ON dm_resources (resource_type);
CREATE INDEX idx_resources_category    ON dm_resources (category);
CREATE INDEX idx_resources_received_at ON dm_resources (received_at DESC);

-- Full-text search index
CREATE INDEX idx_resources_fts ON dm_resources
    USING GIN (to_tsvector('english',
        COALESCE(resource_text, '') || ' ' ||
        COALESCE(resource_url, '')
    ));


-- ─────────────────────────────────────────
-- TABLE: creator_relationships
-- ─────────────────────────────────────────
CREATE TABLE creator_relationships (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    creator_name     TEXT NOT NULL UNIQUE,
    followed         BOOLEAN DEFAULT FALSE,
    followed_at      TIMESTAMPTZ,
    unfollowed_at    TIMESTAMPTZ,
    blocked          BOOLEAN DEFAULT FALSE,
    purpose          TEXT,  -- reel_id that triggered the follow
    last_interaction TIMESTAMPTZ,
    total_reels      INT DEFAULT 0,
    total_resources  INT DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_creators_name    ON creator_relationships (creator_name);
CREATE INDEX idx_creators_followed ON creator_relationships (followed);

CREATE TRIGGER creators_updated_at
    BEFORE UPDATE ON creator_relationships
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ─────────────────────────────────────────
-- TABLE: process_logs
-- ─────────────────────────────────────────
CREATE TABLE process_logs (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reel_id       UUID REFERENCES reels(id) ON DELETE SET NULL,
    step_name     TEXT NOT NULL,
    -- Step enum: REEL_DETECTED, CAPTION_EXTRACTED, CTA_DETECTED, NO_CTA_FOUND,
    --            FOLLOW_SKIPPED, FOLLOW_INITIATED, CREATOR_FOLLOWED, FOLLOW_FAILED,
    --            COMMENT_INITIATED, COMMENTED, COMMENT_FAILED, DM_MONITORING_STARTED,
    --            DM_RECEIVED, DM_TIMEOUT, RESOURCE_EXTRACTED, RESOURCE_DOWNLOAD_FAILED,
    --            NOTION_SYNCED, NOTION_SYNC_FAILED, SESSION_EXPIRED, SESSION_RESTORED,
    --            RATE_LIMITED, RETRY_INITIATED, PIPELINE_COMPLETED, PIPELINE_FAILED
    status        TEXT NOT NULL,  -- success | error | warning | info
    message       TEXT,
    error_message TEXT,
    metadata      JSONB,          -- Additional context (keyword, creator, etc.)
    timestamp     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_logs_reel_id   ON process_logs (reel_id);
CREATE INDEX idx_logs_step_name ON process_logs (step_name);
CREATE INDEX idx_logs_status    ON process_logs (status);
CREATE INDEX idx_logs_timestamp ON process_logs (timestamp DESC);
```

---

## 5. SQLAlchemy Models

### `models/reel.py`

```python
from sqlalchemy import Column, String, Boolean, Float, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMPTZ
from sqlalchemy.orm import relationship
from app.models.base import Base
import uuid

class Reel(Base):
    __tablename__ = "reels"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reel_url          = Column(Text, nullable=False, unique=True)
    creator_name      = Column(String(255))
    caption           = Column(Text)
    requires_comment  = Column(Boolean, default=False)
    requires_follow   = Column(Boolean, default=False)
    requires_dm       = Column(Boolean, default=False)
    comment_keyword   = Column(String(100))
    dm_keyword        = Column(String(100))
    cta_confidence    = Column(Float)
    commented         = Column(Boolean, default=False)
    comment_posted_at = Column(TIMESTAMPTZ)
    followed          = Column(Boolean, default=False)
    followed_at       = Column(TIMESTAMPTZ)
    status            = Column(String(50), nullable=False, default="pending")
    error_message     = Column(Text)
    retry_count       = Column(Integer, default=0)
    notion_synced     = Column(Boolean, default=False)
    notion_page_id    = Column(String(100))
    dm_message_id     = Column(String(100))
    processed_at      = Column(TIMESTAMPTZ)
    created_at        = Column(TIMESTAMPTZ, server_default="NOW()")
    updated_at        = Column(TIMESTAMPTZ, server_default="NOW()")

    # Relationships
    resources = relationship("DMResource", back_populates="reel", cascade="all, delete")
    logs      = relationship("ProcessLog", back_populates="reel")
```

---

## 6. Pydantic Schemas

### `schemas/reel.py`

```python
from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime
from uuid import UUID
from enum import Enum

class ReelStatus(str, Enum):
    PENDING             = "pending"
    EXTRACTING_CAPTION  = "extracting_caption"
    CTA_DETECTED        = "cta_detected"
    NO_CTA              = "no_cta"
    AWAITING_FOLLOW     = "awaiting_follow"
    FOLLOWING           = "following"
    AWAITING_COMMENT    = "awaiting_comment"
    COMMENTING          = "commenting"
    COMMENTED           = "commented"
    WAITING_DM          = "waiting_dm"
    DM_RECEIVED         = "dm_received"
    EXTRACTING_RESOURCE = "extracting_resource"
    COMPLETED           = "completed"
    FAILED              = "failed"
    DM_TIMEOUT          = "dm_timeout"
    RETRYING            = "retrying"

class ReelBase(BaseModel):
    reel_url: str
    creator_name: Optional[str] = None

class ReelResponse(BaseModel):
    id: UUID
    reel_url: str
    creator_name: Optional[str]
    caption: Optional[str]
    requires_comment: bool
    requires_follow: bool
    comment_keyword: Optional[str]
    cta_confidence: Optional[float]
    commented: bool
    followed: bool
    status: ReelStatus
    error_message: Optional[str]
    retry_count: int
    notion_synced: bool
    processed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class ReelListResponse(BaseModel):
    data: list[ReelResponse]
    meta: dict
```

---

## 7. Queue System Design

### `queue/client.py`

```python
import redis.asyncio as aioredis
from app.config import settings

_redis_client = None

async def get_redis_client() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client
```

### Queue Names (Constants)

```python
class QueueNames:
    REEL         = "reelise:reel_queue"
    COMMENT      = "reelise:comment_queue"
    RESOURCE     = "reelise:resource_queue"
    NOTION_SYNC  = "reelise:notion_sync_queue"
    RETRY        = "reelise:retry_queue"
    DEAD_LETTER  = "reelise:dead_letter_queue"
```

### `queue/producer.py`

```python
import json
import uuid
from datetime import datetime
from app.queue.client import get_redis_client
from app.queue.constants import QueueNames

async def push_reel_job(reel_id: str, reel_url: str) -> str:
    redis = await get_redis_client()
    job = {
        "job_id": str(uuid.uuid4()),
        "reel_id": reel_id,
        "job_type": "process_reel",
        "payload": {"reel_url": reel_url},
        "attempt": 1,
        "max_attempts": 3,
        "created_at": datetime.utcnow().isoformat(),
    }
    await redis.lpush(QueueNames.REEL, json.dumps(job))
    return job["job_id"]

async def push_notion_sync_job(reel_id: str, resource_id: str) -> str:
    redis = await get_redis_client()
    job = {
        "job_id": str(uuid.uuid4()),
        "reel_id": reel_id,
        "resource_id": resource_id,
        "job_type": "notion_sync",
        "attempt": 1,
        "max_attempts": 3,
        "created_at": datetime.utcnow().isoformat(),
    }
    await redis.lpush(QueueNames.NOTION_SYNC, json.dumps(job))
    return job["job_id"]

async def get_queue_depths() -> dict:
    redis = await get_redis_client()
    return {
        "reel_queue":        await redis.llen(QueueNames.REEL),
        "comment_queue":     await redis.llen(QueueNames.COMMENT),
        "resource_queue":    await redis.llen(QueueNames.RESOURCE),
        "notion_sync_queue": await redis.llen(QueueNames.NOTION_SYNC),
        "retry_queue":       await redis.llen(QueueNames.RETRY),
        "dead_letter_queue": await redis.llen(QueueNames.DEAD_LETTER),
    }
```

### `queue/consumer.py`

```python
import json
import asyncio
from app.queue.client import get_redis_client

async def pop_job(queue_name: str, timeout: int = 30) -> dict | None:
    redis = await get_redis_client()
    # Blocking pop with timeout — prevents busy waiting
    result = await redis.brpop(queue_name, timeout=timeout)
    if result is None:
        return None
    _, raw = result
    return json.loads(raw)

async def push_to_dead_letter(job: dict, error: str) -> None:
    redis = await get_redis_client()
    job["dead_letter_reason"] = error
    job["dead_letter_at"] = datetime.utcnow().isoformat()
    await redis.lpush(QueueNames.DEAD_LETTER, json.dumps(job))
```

---

## 8. Worker Architecture

### `workers/base_worker.py`

```python
import asyncio
import logging
from abc import ABC, abstractmethod
from app.queue.consumer import pop_job

logger = logging.getLogger(__name__)

class BaseWorker(ABC):
    queue_name: str
    worker_name: str

    def __init__(self):
        self.running = False
        self.current_job = None

    async def start(self):
        self.running = True
        logger.info(f"[{self.worker_name}] Started")
        while self.running:
            try:
                job = await pop_job(self.queue_name)
                if job:
                    self.current_job = job
                    await self.process_job(job)
                    self.current_job = None
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{self.worker_name}] Unhandled error: {e}", exc_info=True)
                await asyncio.sleep(5)  # Brief pause before next attempt

    async def stop(self):
        self.running = False
        logger.info(f"[{self.worker_name}] Stopped")

    @abstractmethod
    async def process_job(self, job: dict) -> None:
        pass
```

### Worker Entry Points

```python
# automation/workers/dm_listener_worker.py
# Runs as: python -m workers.dm_listener_worker

# automation/workers/reel_worker.py
# Runs as: python -m workers.reel_worker

# automation/workers/notion_sync_worker.py
# Runs as: python -m workers.notion_sync_worker
```

### Systemd Service (Google Cloud VM)

```ini
# /etc/systemd/system/reelise-reel-worker.service
[Unit]
Description=Reelise Reel Worker
After=network.target docker.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/reelise
ExecStart=docker compose -f docker-compose.prod.yml run --rm worker-reel
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

---

## 9. Playwright Session Management

### `playwright/instagram/session.py`

```python
import json
import os
from pathlib import Path
from playwright.async_api import BrowserContext, async_playwright
from automation.config import settings
from automation.utils.logger import get_logger

logger = get_logger("session")

SESSION_PATH = Path(settings.INSTAGRAM_SESSION_PATH)

async def load_session(context: BrowserContext) -> bool:
    """Load saved session into browser context. Returns True if session file exists."""
    if not SESSION_PATH.exists():
        logger.warning("No session file found at %s", SESSION_PATH)
        return False
    await context.storage_state  # Playwright loads via new_context(storage_state=...)
    return True

async def save_session(context: BrowserContext) -> None:
    """Save current browser session to file."""
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    await context.storage_state(path=str(SESSION_PATH))
    logger.info("Session saved to %s", SESSION_PATH)

async def validate_session(page) -> bool:
    """Check if current session is authenticated."""
    await page.goto("https://www.instagram.com/", wait_until="networkidle", timeout=30_000)
    # If redirected to login, session is invalid
    current_url = page.url
    if "accounts/login" in current_url:
        logger.warning("Session invalid — redirected to login")
        return False
    logger.info("Session valid — on Instagram feed")
    return True

async def create_browser_context(playwright):
    """Create browser context with stored session if available."""
    browser = await playwright.chromium.launch(
        headless=False,  # Use Xvfb on VM
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
        ]
    )
    context_args = {
        "viewport": {"width": 390, "height": 844},
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        "locale": "en-US",
    }
    if SESSION_PATH.exists():
        context_args["storage_state"] = str(SESSION_PATH)

    context = await browser.new_context(**context_args)
    return browser, context
```

---

## 10. CTA Detection Engine

### `utils/cta_detector.py`

```python
import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class CTAResult:
    requires_comment: bool = False
    requires_follow: bool = False
    requires_dm: bool = False
    comment_keyword: Optional[str] = None
    dm_keyword: Optional[str] = None
    confidence: float = 0.0
    raw_triggers: list[str] = None

    def __post_init__(self):
        if self.raw_triggers is None:
            self.raw_triggers = []

    @property
    def has_cta(self) -> bool:
        return self.requires_comment or self.requires_follow or self.requires_dm

class CTADetector:
    # Comment trigger verbs
    COMMENT_TRIGGERS = [
        r'\bcomment\b', r'\btype\b', r'\breply\b', r'\bsay\b',
        r'\bdrop\b', r'\bwrite\b', r'\bleave\b',
    ]

    # Follow triggers
    FOLLOW_TRIGGERS = [
        r'\bfollow\b.*?\bcomment\b',
        r'\bfollow\b.*?\bget\b',
        r'\bfollow\s*\+\s*comment\b',
        r'\bfollow\s+me\b.*?\bcomment\b',
    ]

    # DM triggers
    DM_TRIGGERS = [
        r'\bdm\s+me\b', r'\bdm\s+\w+\b', r'\bsend\s+me\s+a\s+dm\b',
        r'\bmessage\s+me\b', r'\bsend\s+\w+\s+to\s+get\b',
    ]

    # Common keywords to extract
    KNOWN_KEYWORDS = [
        'guide', 'pdf', 'ai', 'toolkit', 'resource', 'link',
        'free', 'start', 'yes', 'template', 'checklist',
        'roadmap', 'course', 'ebook', 'cheatsheet',
    ]

    def detect(self, caption: str) -> CTAResult:
        if not caption:
            return CTAResult()

        text = caption.lower().strip()
        result = CTAResult()

        # Detect follow requirement
        for pattern in self.FOLLOW_TRIGGERS:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                result.requires_follow = True
                result.raw_triggers.append(f"follow:{pattern}")
                break

        # Detect comment requirement + extract keyword
        for trigger in self.COMMENT_TRIGGERS:
            match = re.search(
                rf'{trigger}\s+["\']?([A-Z][A-Z0-9]{{1,20}}|{"|".join(self.KNOWN_KEYWORDS)})["\']?',
                caption,  # Use original case for keyword extraction
                re.IGNORECASE
            )
            if match:
                result.requires_comment = True
                result.comment_keyword = match.group(1).upper()
                result.raw_triggers.append(f"comment:{trigger}")
                break

        # Detect DM requirement
        for pattern in self.DM_TRIGGERS:
            dm_match = re.search(
                rf'{pattern}\s+["\']?(\w+)["\']?',
                text, re.IGNORECASE
            )
            if dm_match:
                result.requires_dm = True
                result.dm_keyword = dm_match.group(1).upper()
                result.raw_triggers.append(f"dm:{pattern}")
                break

        # Calculate confidence
        if result.has_cta:
            result.confidence = self._calculate_confidence(result, text)

        return result

    def _calculate_confidence(self, result: CTAResult, text: str) -> float:
        score = 0.5  # Base score for having a trigger

        # Keyword match boost
        if result.comment_keyword:
            if any(kw in result.comment_keyword.lower() for kw in self.KNOWN_KEYWORDS):
                score += 0.3
            else:
                score += 0.2  # Unknown keyword still valid

        # Emoji presence (common in CTA captions)
        if any(ord(c) > 127 for c in text):
            score += 0.1

        # Multiple signals
        if result.requires_follow and result.requires_comment:
            score += 0.1

        return min(score, 1.0)

# Module-level singleton
detector = CTADetector()

def detect_cta(caption: str) -> CTAResult:
    return detector.detect(caption)
```

---

## 11. Retry System

### `utils/retry.py`

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)
import logging

logger = logging.getLogger(__name__)

class RetryableError(Exception):
    """Errors that should trigger a retry."""
    pass

class FatalError(Exception):
    """Errors that should NOT be retried."""
    pass

class RateLimitError(RetryableError):
    """Instagram rate limit detected."""
    pass

class SessionExpiredError(RetryableError):
    """Browser session expired."""
    pass

class ReelNotFoundError(FatalError):
    """Reel has been deleted or is unavailable."""
    pass

# Standard retry decorator for automation actions
automation_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=30, max=300),
    retry=retry_if_exception_type(RetryableError),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    after=after_log(logger, logging.INFO),
    reraise=True,
)

# Notion sync retry (shorter backoff)
notion_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=10, max=120),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
```

---

## 12. Logging Strategy

### `utils/logger.py`

```python
import logging
import json
import sys
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level":     record.levelname,
            "logger":    record.name,
            "message":   record.getMessage(),
            "module":    record.module,
            "function":  record.funcName,
            "line":      record.lineno,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "reel_id"):
            log_data["reel_id"] = record.reel_id
        if hasattr(record, "step"):
            log_data["step"] = record.step
        return json.dumps(log_data)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"reelise.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
```

### Log Levels by Context

```
DEBUG   → Playwright selector activity, raw caption text
INFO    → Pipeline step completions, queue operations
WARNING → Retry attempts, rate limit detections
ERROR   → Step failures with recoverable context
CRITICAL → Session expiry, worker crash, DB connection failure
```

### Database Log Writer

Every pipeline step writes to `process_logs` table:

```python
async def log_step(
    db: AsyncSession,
    reel_id: str,
    step_name: str,
    status: str,  # success | error | warning | info
    message: str = None,
    error_message: str = None,
    metadata: dict = None,
) -> None:
    log = ProcessLog(
        reel_id=reel_id,
        step_name=step_name,
        status=status,
        message=message,
        error_message=error_message,
        metadata=metadata,
    )
    db.add(log)
    await db.commit()
```

---

## 13. Error Handling

### Global FastAPI Exception Handler

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "code": "INTERNAL_ERROR",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": str(exc),
            "code": "VALIDATION_ERROR",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
```

### HTTP Error Codes Used

```
200 OK              → Successful GET
201 Created         → Successful POST
204 No Content      → Successful DELETE
400 Bad Request     → Invalid input data
404 Not Found       → Resource doesn't exist
409 Conflict        → Duplicate reel URL
422 Unprocessable   → Validation error
429 Too Many Reqs   → Rate limit (not used in V1 — no public API)
500 Internal Error  → Unhandled server error
503 Unavailable     → Worker/DB connection issue
```

---

## 14. Notion Sync Service

### `services/notion_service.py`

```python
from notion_client import AsyncClient
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("notion")

notion = AsyncClient(auth=settings.NOTION_API_KEY)

CATEGORY_KEYWORDS = {
    "AI": ["ai", "chatgpt", "llm", "gpt", "claude", "prompt", "artificial"],
    "Programming": ["python", "code", "dev", "api", "backend", "frontend", "javascript"],
    "Career": ["career", "job", "resume", "linkedin", "interview", "salary"],
    "Fitness": ["fitness", "workout", "gym", "diet", "nutrition", "health"],
    "Communication": ["communication", "speaking", "writing", "email", "negotiation"],
}

def detect_category(text: str) -> str:
    text_lower = (text or "").lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return "Other"

async def create_resource_page(
    reel_id: str,
    creator_name: str,
    caption: str,
    reel_url: str,
    resource_type: str,
    resource_url: str = None,
    resource_text: str = None,
    keyword: str = None,
) -> str:
    """Create a Notion page for a new resource. Returns Notion page ID."""

    category = detect_category(f"{caption} {keyword} {resource_text}")
    title = f"{creator_name or 'Unknown'} — {keyword or resource_type}"

    page = await notion.pages.create(
        parent={"database_id": settings.NOTION_RESOURCES_DB_ID},
        properties={
            "Name":          {"title": [{"text": {"content": title}}]},
            "Category":      {"select": {"name": category}},
            "Resource Type": {"select": {"name": resource_type.capitalize()}},
            "Creator":       {"rich_text": [{"text": {"content": creator_name or ""}}]},
            "Caption":       {"rich_text": [{"text": {"content": (caption or "")[:2000]}}]},
            "Status":        {"select": {"name": "Unread"}},
            "Source Reel":   {"url": reel_url},
            **({"URL": {"url": resource_url}} if resource_url else {}),
            "Received":      {"date": {"start": datetime.utcnow().isoformat()}},
        },
        children=[
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": resource_text or "No text content extracted."}
                    }]
                }
            }
        ] if resource_text else [],
    )

    return page["id"]
```

---

## 15. Environment Variables

### Backend `.env`

```env
# ─── Application ───────────────────────────
APP_ENV=production
APP_SECRET_KEY=change_me_64_char_random_string
API_PORT=8000

# ─── Database ──────────────────────────────
DATABASE_URL=postgresql+asyncpg://postgres:password@db.xxx.supabase.co:5432/postgres
DATABASE_POOL_SIZE=5

# ─── Redis ─────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ─── Supabase ──────────────────────────────
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJxxx
SUPABASE_SERVICE_KEY=eyJxxx
SUPABASE_STORAGE_BUCKET=reelise-resources

# ─── Instagram ─────────────────────────────
INSTAGRAM_USERNAME=reelise_collector
INSTAGRAM_PASSWORD=your_secure_password
INSTAGRAM_SESSION_PATH=/app/session/instagram_session.json

# ─── Notion ────────────────────────────────
NOTION_API_KEY=secret_xxx
NOTION_RESOURCES_DB_ID=xxx-xxx-xxx

# ─── Worker Limits ─────────────────────────
MAX_DAILY_FOLLOWS=10
FOLLOW_COOLDOWN_SECONDS=300
COMMENT_DELAY_MIN=10
COMMENT_DELAY_MAX=30
DM_POLL_INTERVAL_MIN=45
DM_POLL_INTERVAL_MAX=90
DM_MAX_WAIT_MINUTES=30
```

### Frontend `.env.local`

```env
NEXT_PUBLIC_API_URL=https://api.reelise.railway.app
NEXT_PUBLIC_APP_NAME=Reelise
NEXT_PUBLIC_APP_VERSION=1.0.0
```

---

## 16. Deployment Architecture

### Docker Compose (Local Dev + VM Production)

```yaml
version: '3.9'

services:
  api:
    build: ./backend
    container_name: reelise-api
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=${APP_ENV}
    env_file: ./backend/.env
    depends_on:
      - redis
    networks:
      - reelise-net
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  worker-dm-listener:
    build: ./automation
    container_name: reelise-dm-listener
    command: python -m workers.dm_listener_worker
    env_file: ./automation/.env
    volumes:
      - session-data:/app/session
    depends_on:
      - redis
      - api
    networks:
      - reelise-net
    restart: unless-stopped
    environment:
      - DISPLAY=:99

  worker-reel:
    build: ./automation
    container_name: reelise-reel-worker
    command: python -m workers.reel_worker
    env_file: ./automation/.env
    volumes:
      - session-data:/app/session
    depends_on:
      - redis
      - api
    networks:
      - reelise-net
    restart: unless-stopped
    environment:
      - DISPLAY=:99

  worker-notion-sync:
    build: ./automation
    container_name: reelise-notion-sync
    command: python -m workers.notion_sync_worker
    env_file: ./automation/.env
    depends_on:
      - redis
      - api
    networks:
      - reelise-net
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: reelise-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --save 60 1 --loglevel warning
    networks:
      - reelise-net
    restart: unless-stopped

  frontend:
    build: ./frontend
    container_name: reelise-frontend
    ports:
      - "3000:3000"
    env_file: ./frontend/.env.local
    networks:
      - reelise-net
    profiles: ["local"]  # Only in local dev

volumes:
  redis-data:
  session-data:    # Persists Instagram session across container restarts

networks:
  reelise-net:
    driver: bridge
```

### Backend `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Automation `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    xvfb \
    x11-utils \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY . .

# Start Xvfb virtual display before running worker
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

### `entrypoint.sh`

```bash
#!/bin/bash
# Start virtual display
Xvfb :99 -screen 0 1280x1024x24 &
export DISPLAY=:99

# Start the worker command
exec "$@"
```

---

*Document Version: 1.0.0 | Reelise MVP*
