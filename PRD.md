# PRD.md — Instant!Q
**Version:** 1.0.0
**Status:** MVP
**Owner:** Admin (Single User)
**Last Updated:** 2025

---

## Table of Contents

1. [Vision](#1-vision)
2. [Problem Statement](#2-problem-statement)
3. [User Pain Points](#3-user-pain-points)
4. [Goals](#4-goals)
5. [Success Metrics](#5-success-metrics)
6. [Features — MVP Scope](#6-features--mvp-scope)
7. [Non-Features (V1 Exclusions)](#7-non-features-v1-exclusions)
8. [User Stories](#8-user-stories)
9. [Acceptance Criteria](#9-acceptance-criteria)
10. [Edge Cases](#10-edge-cases)
11. [MVP Scope Definition](#11-mvp-scope-definition)
12. [Future Scope (V2+)](#12-future-scope-v2)
13. [Constraints](#13-constraints)
14. [Risk Analysis](#14-risk-analysis)
15. [KPIs](#15-kpis)

---

## 1. Vision

> **"Every reel you forward becomes a resource you own."**

Instant!Q is a personal knowledge automation system that bridges the gap between Instagram's creator-gated knowledge economy and a user's personal second brain. The product transforms the passive act of saving a reel into an active, automated pipeline that claims the promised resource and stores it inside a structured Notion knowledge base — with zero manual follow-up required from the user.

The long-term vision is to become the definitive personal layer between social media content and personal knowledge management — starting with Instagram, expanding to TikTok, YouTube Shorts, and LinkedIn carousels.

---

## 2. Problem Statement

### The Creator CTA Economy

Instagram creators systematically gate valuable resources behind engagement mechanics:

- **"Comment GUIDE"** → Creator's automation DMs a PDF or link
- **"Follow + Comment PDF"** → Requires follow before triggering resource
- **"Comment AI to get my toolkit"** → Resource sent via DM after keyword comment
- **"DM me START"** → Direct message triggers drip sequence

These patterns are intentional — they boost algorithmic reach while rewarding engaged followers with resources.

### The User Failure Mode

Despite genuinely wanting the resource, users consistently fail to act because:

1. They scroll past at high speed and forget within seconds
2. The friction of switching from passive watching to active commenting breaks flow
3. They save the reel with the intention to "do it later" — which almost never happens
4. When they do comment, they never check DMs for the response
5. Resources received in DMs get buried under other messages
6. There is no organization, search, or retrieval system for collected resources

### The Knowledge Loss

The result is a systematic leak of potentially valuable content — career guides, programming tutorials, fitness protocols, AI toolkits, communication frameworks — that the user explicitly indicated interest in by saving the reel, but never claimed or organized.

---

## 3. User Pain Points

| Pain Point | Severity | Frequency |
|---|---|---|
| Save reels, never revisit them | Critical | Daily |
| Forget to comment keyword after saving | Critical | Daily |
| Miss DM response from creator | High | Per reel |
| Resources scattered across Instagram DMs | High | Cumulative |
| No way to search saved resources | High | Cumulative |
| Having to manually follow creators before commenting | Medium | Per reel |
| Not knowing what keyword to use for a specific reel | Medium | Per reel |
| Resources expire or creator deletes them | Low | Occasional |

---

## 4. Goals

### Primary Goal
Automate the full pipeline from reel share to structured knowledge entry — with **one manual action** from the user (sharing the reel to the collector account).

### Secondary Goals
- Build a personal knowledge base that is searchable and organized
- Track all creator relationships created by the automation
- Provide a Notion dashboard that functions as a second brain for collected resources
- Operate reliably with human-like behavior to minimize detection risk

### Technical Goals
- Maintain persistent Playwright sessions without repeated logins
- Process each reel within 10 minutes of detection
- Achieve 90%+ comment success rate on reels with detected CTAs
- Zero data loss — every reel shared is logged regardless of outcome

---

## 5. Success Metrics

### Core Metrics (MVP)

| Metric | Target |
|---|---|
| Reel detection rate | 100% of manually shared reels detected |
| CTA detection accuracy | ≥ 85% on standard CTA patterns |
| Comment success rate | ≥ 90% on reels requiring comment |
| Follow success rate | ≥ 95% on reels requiring follow |
| DM resource extraction rate | ≥ 80% of resources successfully extracted |
| End-to-end processing time | < 10 minutes per reel |
| System uptime | ≥ 99% on automation worker |
| Notion sync latency | < 2 minutes after resource is saved |

### Quality Metrics

| Metric | Target |
|---|---|
| False positive CTA detections | < 10% |
| Duplicate comments prevented | 100% |
| Failed reels logged with error context | 100% |
| Retry success rate (after first failure) | ≥ 60% |

---

## 6. Features — MVP Scope

### F1: Collector Account System
- Single dedicated Instagram account used as the automation target
- One-time manual login with persistent session storage
- Cookie-based session maintenance
- Never re-login unless session explicitly expires

### F2: DM Detection Worker
- Playwright worker that monitors collector account inbox
- Detects when user forwards a reel to collector account
- Extracts reel URL from the shared message
- Marks messages as processed to avoid duplicates
- Runs in temporary watch mode (not 24/7 polling)

### F3: Reel Caption Extraction
- Opens reel URL via Playwright
- Extracts caption text only
- Stores raw caption in Supabase
- No OCR, no audio, no transcript — caption only in V1

### F4: CTA Detection Engine
- Keyword-based pattern matching on caption text
- Detects: `comment`, `guide`, `pdf`, `follow`, `dm`, `send`, `resource`, `toolkit`, `link`, `free`
- Extracts action type: requires_follow, requires_comment
- Extracts keyword: the specific word to comment
- Handles multi-action CTAs ("Follow + Comment PDF")
- Confidence scoring on detection
- Stores structured CTA metadata in Supabase

### F5: Follow Requirement Handler
- Checks existing creator_relationship in database
- If not following: executes follow action via Playwright
- Randomized delay before following (5–15 seconds)
- Stores follow record with timestamp and reel context
- Maximum daily follow threshold (configurable)
- Follow cooldown between actions

### F6: Comment Automation
- Posts comment with detected keyword on reel
- Human-like random delay before commenting (10–30 seconds)
- Verifies comment was posted successfully
- Stores comment status in reel record
- Prevents duplicate comments via database check
- Retry on failure (up to 3 attempts)

### F7: DM Monitor
- Watches collector inbox for creator response DM
- Polls at human-like intervals after comment is posted
- Maximum wait time: 30 minutes per reel
- Extracts from DM: links, text, attached files, media
- Downloads and stores files to Supabase Storage
- Saves resource metadata to dm_resources table

### F8: Resource Processor
- Processes extracted DM content
- Categorizes resource type: link / pdf / text / media
- Downloads linked files where possible
- Stores file path in Supabase Storage
- Creates structured dm_resource record

### F9: Supabase Database
- PostgreSQL via Supabase
- Tables: reels, dm_resources, creator_relationships, process_logs
- Full status tracking per reel across all pipeline steps
- Soft deletes only

### F10: Notion Sync Worker
- FastAPI background worker syncs Supabase → Notion
- Creates/updates Notion pages per resource
- Organizes into categories: AI, Career, Programming, Fitness, Communication, Other
- Uses Notion database with gallery/board views
- Sync runs after resource is saved to Supabase

### F11: Notion Dashboard
- Primary interface for the user to browse collected resources
- Gallery view of all resources with cover images
- Board view by category
- Search via Notion search
- Progress tracking: unread, read, saved

### F12: Process Logging
- Every pipeline step logged with: step name, status, error, timestamp
- Linked to reel ID
- Queryable from dashboard
- Failed reels surface immediately

### F13: PostgreSQL Search (V1)
- Full-text search on caption, resource_text, creator_name
- Search API endpoint in FastAPI
- Query via dashboard or direct API

### F14: Health Monitoring
- `/health` endpoint on FastAPI
- Worker heartbeat logging
- Redis queue depth monitoring
- Failure rate alerting via logs

---

## 7. Non-Features (V1 Exclusions)

These are explicitly out of scope for V1:

| Feature | Reason Excluded |
|---|---|
| OCR on reel images | Cost and complexity |
| Audio transcription | Cost and complexity |
| AI embeddings / semantic search | Cost — PostgreSQL FTS sufficient for V1 |
| Multi-user support | Not needed — single admin |
| SaaS billing | Out of scope |
| Mobile app | Out of scope |
| TikTok / YouTube Shorts | Platform expansion is V2+ |
| Browser extension | V2+ |
| Email notifications | V1 uses Notion as notification layer |
| AI summarization of resources | V2+ |
| Automatic reel categorization via AI | V2+ |
| Public dashboard | Out of scope |
| User accounts / auth | Out of scope — single admin |
| Payment integration | Out of scope |

---

## 8. User Stories

### US-01: Reel Forwarding
> **As the admin user, I want to forward a reel to my collector account so that the system can automatically process it.**

### US-02: CTA Detection
> **As the admin user, I want the system to automatically detect whether a reel requires me to comment a keyword, so that I don't have to read the caption myself.**

### US-03: Automatic Follow
> **As the admin user, I want the system to follow the creator on my behalf when required, so that gated resources are unlocked without my intervention.**

### US-04: Automatic Comment
> **As the admin user, I want the system to comment the correct keyword on the reel, so that the creator's automation sends the resource to my collector DMs.**

### US-05: Resource Extraction
> **As the admin user, I want the system to detect and extract any link, PDF, or file sent in response to the comment, so that the resource is captured without me checking DMs.**

### US-06: Notion Knowledge Base
> **As the admin user, I want extracted resources to appear in my Notion dashboard organized by category, so that I have a searchable second brain of all collected content.**

### US-07: Failure Visibility
> **As the admin user, I want to see which reels failed to process and why, so that I can manually intervene if needed.**

### US-08: Search
> **As the admin user, I want to search my collected resources by keyword, so that I can find specific content when I need it.**

### US-09: Creator Tracking
> **As the admin user, I want to see which creators I'm following (via automation) and why, so that I maintain awareness of my collector account's relationships.**

### US-10: Process Status
> **As the admin user, I want to see the real-time status of each reel being processed, so that I understand what the system is doing.**

---

## 9. Acceptance Criteria

### AC-01: Reel Detection
- [ ] Within 5 minutes of forwarding, the reel URL is stored in Supabase
- [ ] Each reel is processed exactly once (no duplicates)
- [ ] DM message ID is tracked to prevent reprocessing

### AC-02: Caption Extraction
- [ ] Caption text is stored in the reels table
- [ ] If reel has no caption, status is set to `no_caption` and process continues

### AC-03: CTA Detection
- [ ] `requires_comment=true` when caption contains comment trigger + keyword
- [ ] `requires_follow=true` when caption explicitly requires follow
- [ ] `comment_keyword` is correctly extracted (e.g., "GUIDE", "PDF", "AI")
- [ ] CTA detection is case-insensitive
- [ ] If no CTA detected, status set to `no_cta` and reel is stored without automation

### AC-04: Follow Action
- [ ] Creator is not followed if already in creator_relationships with `followed=true`
- [ ] Follow action includes randomized delay of 5–20 seconds
- [ ] creator_relationships record created/updated after follow
- [ ] Daily follow limit enforced (default: 10 per day)

### AC-05: Comment Action
- [ ] Comment posted with correct keyword from CTA detection
- [ ] Comment includes randomized delay of 10–30 seconds before posting
- [ ] Comment status stored in reel record
- [ ] Comment not posted if reel already shows `commented=true`
- [ ] Retry up to 3 times on failure with exponential backoff

### AC-06: DM Resource Capture
- [ ] System polls DMs for up to 30 minutes after comment
- [ ] Links, PDFs, and text extracted from creator response
- [ ] Files downloaded to Supabase Storage
- [ ] dm_resources record created with full metadata

### AC-07: Notion Sync
- [ ] Resource appears in Notion within 2 minutes of Supabase save
- [ ] Correct category assigned
- [ ] Resource URL/file linked in Notion page

### AC-08: Logging
- [ ] Every pipeline step has a process_logs entry
- [ ] Failed steps include error message
- [ ] Logs are queryable by reel_id

---

## 10. Edge Cases

| Edge Case | Handling Strategy |
|---|---|
| Reel deleted before processing | Log error, mark reel `reel_deleted`, skip |
| CTA in image overlay (not caption) | Mark as `cta_not_detected`, store reel, no action |
| Creator never sends DM after comment | Mark as `dm_timeout` after 30 min wait |
| Creator DM is not a resource (just text reply) | Save as `resource_type=text`, sync to Notion |
| Already following creator from main account | Collector account still follows — they are separate |
| Comment fails due to rate limit | Retry after 5 min cooldown, up to 3 times |
| Multiple CTAs in one caption | Process first detected, log others |
| Reel requires DM (not comment) | Detect `requires_dm=true`, send DM with keyword |
| Resource link is expired | Store URL with `status=link_expired` |
| Playwright session expires | Re-authenticate using stored credentials, log event |
| Redis queue backlog | Process FIFO, max 50 reels queued, alert if exceeded |
| Supabase storage limit | Alert admin, stop downloading new files |
| Notion API rate limit | Queue sync tasks, retry with backoff |
| Network timeout during reel open | Retry 3 times, mark `open_failed` after exhaustion |
| Creator blocks collector account | Log, mark creator `blocked=true`, alert admin |
| Duplicate reel forwarded | Detect by reel URL, skip if exists with `status != failed` |

---

## 11. MVP Scope Definition

### In MVP
- Collector account DM monitoring
- Reel URL extraction
- Caption extraction
- CTA detection (keyword-based)
- Follow automation
- Comment automation
- DM response monitoring
- Resource extraction (links, text, files)
- Supabase as source of truth
- Notion sync and dashboard
- Process logging
- PostgreSQL full-text search
- Docker containerization
- Railway backend deployment
- Google Cloud VM automation worker

### Not in MVP (Hard Cutoff)
- Any AI/ML features
- Any OCR or transcription
- Any multi-user features
- Any mobile interface
- Any platform other than Instagram

---

## 12. Future Scope (V2+)

### V2 — Intelligence Layer
- AI caption summarization (GPT-4o-mini for cost optimization)
- Semantic search via pgvector
- Automatic resource categorization via AI
- Resource quality scoring

### V3 — Platform Expansion
- TikTok reel support
- YouTube Shorts support
- LinkedIn carousel support

### V4 — Interface Expansion
- Custom Next.js dashboard replacing/supplementing Notion
- Browser extension for one-click reel submission
- Mobile app

### V5 — Social Features (if SaaS)
- Multi-user support
- Shared knowledge bases
- Team workspaces

---

## 13. Constraints

### Technical Constraints
- Instagram does not provide a public API for DM or reel automation
- All automation via Playwright (browser simulation)
- Session persistence critical — avoid repeated logins
- Rate limits enforced by Instagram may change without notice

### Operational Constraints
- Single collector Instagram account
- Single admin user
- Must operate within Instagram's detection thresholds
- Google Cloud VM must remain running for automation worker

### Cost Constraints
- Supabase free tier: 500MB database, 1GB storage
- Redis: self-hosted on VM or Upstash free tier
- Notion: free tier API usage
- Railway: Starter plan ($5/month)
- Google Cloud VM: e2-micro (free tier eligible)

### Legal / Ethical Constraints
- **Instagram Terms of Service**: Automated interactions violate Instagram ToS
- This is a **personal tool for a single user** processing their own saved content
- Not spam, not commercial automation, not mass interaction
- Admin uses at their own risk with full awareness of ToS implications
- No data from other users is collected

---

## 14. Risk Analysis

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Instagram detects automation, suspends collector account | Medium | High | Human-like delays, minimal footprint, limited daily actions |
| Session expires frequently | Medium | Medium | Persistent cookies, graceful re-auth with stored credentials |
| CTA pattern not detected | Medium | Low | Log undetected, notify admin, system continues |
| Creator DM automation is delayed | Low | Low | Extended wait time (30 min), retry logic |
| Notion API rate limits | Low | Medium | Batched sync, retry with backoff |
| Redis queue overflow | Low | Medium | Queue depth monitoring, alerts |
| Supabase storage limit reached | Low | High | Monitor usage, alert at 80% |
| Google Cloud VM instance goes down | Low | High | Auto-restart script, health check monitoring |
| Playwright browser update breaks selectors | Medium | High | Version pinning, selector testing suite |
| Creator DM response contains no resource | Medium | Low | Save as text response, mark `no_resource` |

---

## 15. KPIs

### Operational KPIs

| KPI | Measurement | Target |
|---|---|---|
| Reels Processed / Week | Count in Supabase | All forwarded reels |
| CTA Detection Rate | detected / total | ≥ 85% |
| Comment Success Rate | commented / requires_comment | ≥ 90% |
| Follow Success Rate | followed / requires_follow | ≥ 95% |
| Resource Extraction Rate | resources / dm_received | ≥ 80% |
| End-to-End Latency | processed_at - created_at | < 10 min avg |
| Notion Sync Success | synced / saved | ≥ 99% |
| Pipeline Failure Rate | failed / total | < 10% |

### Knowledge Base KPIs

| KPI | Measurement |
|---|---|
| Total Resources Collected | Count in dm_resources |
| Resources by Category | Distribution in Notion/Supabase |
| Creators Followed | Count in creator_relationships |
| Search Queries Executed | Count in logs |

---

*Document Version: 1.0.0 | Instant!Q MVP*
