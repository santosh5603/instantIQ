# APP_FLOW.md — Reelise
**Version:** 1.0.0
**Status:** MVP
**Last Updated:** 2025

---

## Table of Contents

1. [System Architecture Diagram](#1-system-architecture-diagram)
2. [End-to-End Flow Overview](#2-end-to-end-flow-overview)
3. [Step-by-Step Pipeline](#3-step-by-step-pipeline)
4. [Instagram Collector Flow](#4-instagram-collector-flow)
5. [CTA Detection Flow](#5-cta-detection-flow)
6. [Follow Requirement Flow](#6-follow-requirement-flow)
7. [Comment Automation Flow](#7-comment-automation-flow)
8. [DM Monitoring Flow](#8-dm-monitoring-flow)
9. [Resource Processing Flow](#9-resource-processing-flow)
10. [Notion Sync Flow](#10-notion-sync-flow)
11. [Failure Recovery & Retry Architecture](#11-failure-recovery--retry-architecture)
12. [Queue Flow Diagrams](#12-queue-flow-diagrams)
13. [Database State Transitions](#13-database-state-transitions)
14. [Human-Like Worker Strategy](#14-human-like-worker-strategy)
15. [Session Management Flow](#15-session-management-flow)

---

## 1. System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                         REELISE ARCHITECTURE                         │
└──────────────────────────────────────────────────────────────────────┘

  [Admin User]
       │
       │  (1) Manually shares reel via Instagram app
       ▼
  [Instagram App]
       │
       │  Share to DM → @reelise_collector
       ▼
  ┌─────────────────────────────────────────────────────┐
  │              GOOGLE CLOUD VM (Ubuntu)               │
  │                                                     │
  │  ┌─────────────────┐    ┌──────────────────────┐   │
  │  │  DM Listener    │    │  Automation Worker   │   │
  │  │  Worker         │───▶│  (Playwright)        │   │
  │  │  (Playwright)   │    │                      │   │
  │  └─────────────────┘    └──────────┬───────────┘   │
  │                                    │               │
  │  ┌─────────────────────────────────▼────────────┐  │
  │  │              Redis Queue                     │  │
  │  │  reel_queue / comment_queue / resource_queue │  │
  │  └─────────────────────────────────┬────────────┘  │
  └────────────────────────────────────│───────────────┘
                                       │
                                       │ HTTP (internal)
                                       ▼
  ┌─────────────────────────────────────────────────────┐
  │              RAILWAY (FastAPI Backend)              │
  │                                                     │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
  │  │ Reels    │ │Resources │ │ Notion   │           │
  │  │ Router   │ │ Router   │ │ Sync Svc │           │
  │  └──────────┘ └──────────┘ └──────────┘           │
  └───────────────────────┬─────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
  ┌──────────────┐ ┌─────────────┐ ┌──────────────┐
  │  Supabase    │ │  Supabase   │ │  Notion API  │
  │  PostgreSQL  │ │  Storage    │ │              │
  │  (DB)        │ │  (Files)    │ │  Dashboard   │
  └──────────────┘ └─────────────┘ └──────────────┘
                          ▲
                          │
  ┌───────────────────────┘
  │
  ▼
  ┌─────────────────────────────────────────────────────┐
  │              VERCEL (Next.js Frontend)              │
  │                                                     │
  │  Dashboard / History / Resources / Logs / Search   │
  └─────────────────────────────────────────────────────┘
                          ▲
                          │
                    [Admin User]
                  (Pipeline Monitor)
```

---

## 2. End-to-End Flow Overview

```
[Admin] → Share Reel → [Instagram DMs]
                              │
                    ┌─────────▼──────────┐
                    │  DM Listener       │ (Playwright)
                    │  Detects new share │
                    └─────────┬──────────┘
                              │ Extracts reel URL
                    ┌─────────▼──────────┐
                    │  Push to           │
                    │  reel_queue        │ (Redis)
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Reel Worker       │ (Playwright)
                    │  Opens reel URL    │
                    │  Extracts caption  │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  CTA Detection     │ (Python)
                    │  Regex + keywords  │
                    └─────────┬──────────┘
                              │
               ┌──────────────┼──────────────┐
               ▼              ▼              ▼
        [No CTA]      [Comment Only]  [Follow + Comment]
               │              │              │
        Store reel     Comment with    Follow creator
        status=no_cta  keyword         then comment
                              │              │
                    ┌─────────▼──────────────▼──┐
                    │  DM Monitor               │ (Playwright)
                    │  Watch creator inbox      │
                    │  Up to 30 min             │
                    └─────────┬─────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Resource Extract  │ (Python)
                    │  Links/PDFs/Files  │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Supabase          │ (DB + Storage)
                    │  Save everything   │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Notion Sync       │ (FastAPI worker)
                    │  Create page       │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Notion Dashboard  │
                    │  Resource visible  │
                    └────────────────────┘
```

---

## 3. Step-by-Step Pipeline

### Stage Definitions

| Stage | Code | Description |
|---|---|---|
| `pending` | P | Reel detected, queued, not yet opened |
| `extracting_caption` | EC | Playwright opening reel, reading caption |
| `cta_detected` | CD | CTA found, action determined |
| `no_cta` | NC | No CTA found, reel stored |
| `awaiting_follow` | AF | Follow action queued |
| `following` | FL | Follow action in progress |
| `awaiting_comment` | AC | Comment queued |
| `commenting` | CM | Comment being posted |
| `commented` | CO | Comment posted, DM monitoring started |
| `waiting_dm` | WD | Waiting for creator DM response |
| `dm_received` | DR | DM response detected |
| `extracting_resource` | ER | Downloading/extracting resource |
| `completed` | ✅ | Resource stored, Notion synced |
| `failed` | ❌ | Unrecoverable error |
| `dm_timeout` | DT | No DM received within wait window |
| `retrying` | RT | In retry backoff |

---

## 4. Instagram Collector Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  COLLECTOR ACCOUNT FLOW                     │
└─────────────────────────────────────────────────────────────┘

SETUP (One-time):
─────────────────
1. Admin runs: python scripts/login.py
2. Playwright opens Instagram login page
3. Admin manually enters credentials in browser
4. Admin completes 2FA if required
5. Session saved: session/instagram_session.json
6. Credentials stored in .env (for re-auth only)
7. Login script exits

NORMAL OPERATION:
─────────────────
1. DM Listener worker starts
2. Loads session from instagram_session.json
3. Navigates to Instagram DM inbox
4. Scans for unread messages from admin's main account
5. Identifies reel shares (contain reel URLs)
6. Extracts reel URL from message
7. Records message ID as processed
8. Pushes reel URL to Redis reel_queue
9. Marks message as read (optional)
10. Continues polling at randomized intervals

SESSION VALIDATION:
───────────────────
Before each worker cycle:
1. Check if session file exists
2. Load session into Playwright context
3. Navigate to Instagram home
4. Check if redirected to login page
5. If login page: trigger re-auth flow
6. If home page: session valid, proceed

RE-AUTHENTICATION FLOW:
────────────────────────
1. Worker detects session expiry
2. Logs critical event: SESSION_EXPIRED
3. Attempts login with stored credentials
4. If 2FA required: pauses worker, alerts admin via log
5. On success: saves new session, resumes
6. On failure: worker stops, requires manual intervention
```

### DM Detection Sequence
```
DM Listener Worker
       │
       │ 1. Open Instagram DMs page
       ▼
Check message list
       │
       ├── No new messages → Wait (randomized: 45-90 seconds) → Loop
       │
       └── New message found
                  │
                  ▼
          Check sender = admin's main account?
                  │
                  ├── No → Skip message, mark checked
                  │
                  └── Yes → Extract message content
                                    │
                                    ▼
                           Contains Instagram reel URL?
                           (regex: instagram.com/reel/)
                                    │
                                    ├── No → Skip, log
                                    │
                                    └── Yes → Extract URL
                                                   │
                                                   ▼
                                          Check reel URL exists in DB?
                                                   │
                                                   ├── Yes → Skip (duplicate)
                                                   │
                                                   └── No → INSERT reel record
                                                                  │
                                                                  ▼
                                                         Push to reel_queue
                                                         Log: REEL_DETECTED
```

---

## 5. CTA Detection Flow

```
INPUT: caption_text (string)
OUTPUT: CTAResult { requires_follow, requires_comment, comment_keyword, confidence }

┌─────────────────────────────────────────────────────────────┐
│                    CTA DETECTION ENGINE                     │
└─────────────────────────────────────────────────────────────┘

Step 1: Normalize
─────────────────
caption_lower = caption.lower().strip()

Step 2: Follow Detection
─────────────────────────
Patterns:
  - "follow" + ("then" | "and" | "+") + "comment"
  - "follow me" + "comment"
  - "follow" + "to get"
  
Result: requires_follow = True | False

Step 3: Comment Detection
──────────────────────────
Patterns:
  - "comment [KEYWORD]"
  - "type [KEYWORD]"
  - "reply [KEYWORD]"
  - "say [KEYWORD]"
  
Keyword extraction:
  - Word immediately following trigger verb
  - Uppercase word in vicinity of trigger
  - Word in quotes following trigger

Result: requires_comment = True | False
        comment_keyword = "GUIDE" | "PDF" | "AI" | etc.

Step 4: DM Trigger Detection
──────────────────────────────
Patterns:
  - "dm me [KEYWORD]"
  - "send [KEYWORD] to get"
  - "message [KEYWORD]"

Result: requires_dm = True | False
        dm_keyword = extracted keyword

Step 5: Confidence Scoring
───────────────────────────
HIGH (0.9+):   Exact match: "comment GUIDE below"
MEDIUM (0.7):  Partial match: "guide in comments"
LOW (0.5):     Weak signal: "comment for more"
NONE (0.0):    No trigger found

Step 6: Output
───────────────
{
  requires_follow: bool,
  requires_comment: bool,
  requires_dm: bool,
  comment_keyword: str | None,
  dm_keyword: str | None,
  confidence: float,
  raw_triggers: list[str]
}

EXAMPLE MAPPINGS:
──────────────────
"Comment GUIDE below 👇"
→ requires_comment=true, keyword="GUIDE", confidence=0.95

"Follow + Comment PDF to get my toolkit"  
→ requires_follow=true, requires_comment=true, keyword="PDF", confidence=0.92

"DM me START and I'll send you the resource"
→ requires_dm=true, dm_keyword="START", confidence=0.88

"Free guide in my bio 👆"
→ no_cta, confidence=0.0

"Drop 'AI' in the comments 🔥"
→ requires_comment=true, keyword="AI", confidence=0.90
```

---

## 6. Follow Requirement Flow

```
INPUT: creator_name (string), reel_id (UUID)
OUTPUT: FollowResult { followed, already_following, skipped_reason }

┌─────────────────────────────────────────────────────────────┐
│                  FOLLOW REQUIREMENT HANDLER                 │
└─────────────────────────────────────────────────────────────┘

                    START
                      │
                      ▼
           Query creator_relationships
           WHERE creator_name = ?
                      │
           ┌──────────┴──────────┐
           │ Record exists       │ No record
           │ followed = true     │
           ▼                     ▼
     Already following      Check daily follow count
     → Skip follow          (process_logs for today)
     → Proceed to comment          │
                         ┌─────────┴─────────┐
                         │ Count < MAX_DAILY  │ Count >= MAX_DAILY
                         │ (default: 10)      │
                         ▼                    ▼
                   Check cooldown       Queue for tomorrow
                   (last follow         Log: DAILY_LIMIT_REACHED
                    < 5 min ago?)
                         │
                ┌────────┴────────┐
                │ Cooldown OK     │ In cooldown
                ▼                 ▼
         Execute follow      Wait for cooldown
         via Playwright      then retry
                │
                ▼
         Random delay: 5–20 seconds
                │
                ▼
         Navigate to creator profile
                │
                ▼
         Click Follow button
                │
                ▼
         Verify follow state changed
                │
         ┌──────┴──────┐
         │ Success     │ Failure
         ▼             ▼
   UPDATE/INSERT    Log error
   creator_         Retry (max 3)
   relationships
   followed=true
         │
         ▼
   Log: CREATOR_FOLLOWED
   Proceed to comment
```

---

## 7. Comment Automation Flow

```
INPUT: reel_url, comment_keyword, reel_id
OUTPUT: CommentResult { success, comment_text, posted_at }

┌─────────────────────────────────────────────────────────────┐
│                    COMMENT AUTOMATION                       │
└─────────────────────────────────────────────────────────────┘

                    START
                      │
                      ▼
         Check reel record: already_commented?
                      │
              ┌───────┴───────┐
              │ True          │ False
              ▼               ▼
         Skip (idempotent)  Navigate to reel URL
                                     │
                                     ▼
                          Human-like delay:
                          random.uniform(10, 30) seconds
                                     │
                                     ▼
                          Locate comment input field
                                     │
                                     ▼
                          Type comment character by character
                          with random delays (50-150ms per char)
                                     │
                                     ▼
                          Pause: random.uniform(1.5, 3.5) seconds
                                     │
                                     ▼
                          Submit comment
                                     │
                              ┌──────┴──────┐
                              │ Success     │ Failure
                              ▼             ▼
                       Verify comment    Classify error:
                       appears in feed   
                              │           ├─ Rate limited:
                              ▼           │  Wait 5 min, retry
                       UPDATE reel        │
                       commented=true     ├─ Session expired:
                       comment_posted_at  │  Re-auth, retry
                              │           │
                       Push to            └─ Unknown:
                       resource_queue        Log, mark failed
                                             if attempt < 3:
                                               retry with backoff

COMMENT TEXT VARIANTS (randomized):
─────────────────────────────────────
Base keyword: "GUIDE"
Options:
  - "GUIDE"
  - "guide"
  - "Guide"
  → Selected randomly for human variation

Optionally append (configurable):
  - "GUIDE 🙏"
  - "guide!"
  - "GUIDE please"
```

---

## 8. DM Monitoring Flow

```
INPUT: reel_id, creator_name, comment_posted_at
OUTPUT: DMResult { received, messages, resources_extracted }

┌─────────────────────────────────────────────────────────────┐
│                     DM MONITOR SYSTEM                       │
└─────────────────────────────────────────────────────────────┘

               START: comment_posted_at
                         │
                         ▼
              Navigate to Instagram DMs
                         │
                         ▼
              Start monitoring loop
              timeout = 30 minutes
              poll_interval = 60–90 seconds (randomized)
                         │
              ┌──────────▼──────────┐
              │     POLL CYCLE      │◄──────────────┐
              └──────────┬──────────┘               │
                         │                          │
                         ▼                          │
              Check DM list for message             │
              from creator_name                     │
                         │                          │
              ┌──────────┴──────────┐               │
              │ No message from     │ Message found  │
              │ creator             │               │
              ▼                     ▼               │
   Check elapsed time    Open DM thread             │
              │                     │               │
   ┌──────────┴──────┐              ▼               │
   │ < 30 min        │ > 30 min  Extract content:   │
   ▼                 ▼           - Text messages    │
   Wait 60-90s   Mark reel       - URLs/links       │
   then loop     dm_timeout      - File attachments │
   ─────────────►               - Media files       │
              │                     │               │
              └─────────────────────┘               │
                         │                          │
                         ▼                          │
              Content extraction                    │
                         │                          │
              ┌──────────┴──────────┐               │
              │ Contains resource?  │               │
              ├─────────────────────┤               │
              │ YES: links/files    │               │
              │ NO: text only       │               │
              └──────────┬──────────┘               │
                         │                          │
                         ▼                          │
              Push to resource_queue                │
              Log: DM_RECEIVED                      │
                         │                          │
              Check: more messages                  │
              expected? (multi-part)                │
                         │                          │
              ┌──────────┴──────────┐               │
              │ Yes (drip sequence) │ No             │
              ▼                     ▼               │
         Continue monitoring    Close DM thread     │
         ─────────────────────────────────────────►─┘
```

---

## 9. Resource Processing Flow

```
INPUT: dm_content (text, links, files)
OUTPUT: Structured dm_resource records in Supabase

┌─────────────────────────────────────────────────────────────┐
│                   RESOURCE PROCESSOR                        │
└─────────────────────────────────────────────────────────────┘

For each extracted DM item:
         │
         ▼
Classify resource type:
         │
┌────────┼──────────┬──────────┬──────────┐
▼        ▼          ▼          ▼          ▼
URL    PDF        Image     Video     Plain text
         │
         ├── External link → Store as resource_url
         │                   Attempt HTTP HEAD to verify
         │                   Store: title, type, status
         │
         ├── PDF direct URL → Download file
         │                    Upload to Supabase Storage
         │                    Store: attachment_path
         │
         ├── Image/Media → Download
         │                  Upload to Supabase Storage
         │                  Store: attachment_path
         │
         └── Text → Store as resource_text
                    No download needed

After processing all items:
         │
         ▼
INSERT dm_resources record:
  - reel_id
  - resource_type
  - resource_url (if link)
  - resource_text (if text)
  - attachment_path (if file)
  - received_at

UPDATE reel status → 'completed'

Push to notion_sync_queue
```

---

## 10. Notion Sync Flow

```
INPUT: dm_resource record + reel record
OUTPUT: Notion database page created/updated

┌─────────────────────────────────────────────────────────────┐
│                     NOTION SYNC WORKER                      │
└─────────────────────────────────────────────────────────────┘

                    START
                      │
                      ▼
         Pull job from notion_sync_queue
                      │
                      ▼
         Fetch full reel + resource data
         from Supabase
                      │
                      ▼
         Check: Notion page exists for reel_id?
         (query Notion DB by reel_id property)
                      │
              ┌───────┴───────┐
              │ Exists        │ Doesn't exist
              ▼               ▼
         UPDATE page      CREATE new page
                      │
                      ▼
         Page properties:
         ─────────────────
         Name:          "{creator} — {keyword}"
         Category:      auto-detected from keyword/caption
         Resource Type: link | pdf | text | media
         URL:           resource_url
         Creator:       creator_name
         Caption:       first 200 chars of caption
         Status:        "Unread" (default)
         Received:      received_at date
         Source Reel:   reel_url
                      │
                      ▼
         If file attached:
         Upload to Notion as file block
                      │
                      ▼
         Mark notion_synced=true in Supabase
         Log: NOTION_SYNCED

CATEGORY AUTO-DETECTION:
─────────────────────────
keyword/caption contains:
  "ai" | "chatgpt" | "llm"    → "AI"
  "python" | "code" | "dev"   → "Programming"
  "career" | "job" | "resume" → "Career"
  "fitness" | "workout"       → "Fitness"
  "communication" | "speak"   → "Communication"
  default                     → "Other"
```

---

## 11. Failure Recovery & Retry Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  RETRY ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────┘

RETRY POLICY (using tenacity):
───────────────────────────────
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=30, max=300),
    retry=retry_if_exception_type(RetryableError)
)

ATTEMPT SCHEDULE:
  Attempt 1: immediate
  Attempt 2: 30 seconds later
  Attempt 3: 2 minutes later
  → If all fail: mark status='failed', log error

ERROR CLASSIFICATION:
─────────────────────
RetryableError (retry):
  - Network timeout
  - Instagram rate limit (HTTP 429)
  - Playwright timeout
  - Session temporarily invalid
  - DM not received yet (in wait window)

FatalError (no retry):
  - Reel deleted/not found (HTTP 404)
  - Creator blocked collector account
  - Session permanently invalid (manual fix required)
  - Invalid reel URL format

DEAD LETTER HANDLING:
─────────────────────
After 3 failed attempts:
1. Move job to dead_letter_queue in Redis
2. Update reel status = 'failed'
3. Log detailed error context
4. Admin visible in dashboard logs
5. Manual retry available from dashboard (future V2)

PARTIAL FAILURE RECOVERY:
──────────────────────────
Each pipeline stage is checkpointed in Supabase.
On worker restart, incomplete reels are re-queued
from their last successful checkpoint stage — not
restarted from beginning.

Stage checkpoints:
  caption_extracted=true → skip to CTA detection
  cta_detected=true      → skip to action phase
  followed=true          → skip to comment phase
  commented=true         → skip to DM monitoring
```

---

## 12. Queue Flow Diagrams

```
QUEUE ARCHITECTURE:
────────────────────

Producer                Queue               Consumer
────────────────────────────────────────────────────

DM Listener     →   [reel_queue]    →   Reel Worker
                    [job, job, job]       (opens reel,
                                          extracts caption,
                                          detects CTA)

Reel Worker     →   [comment_queue] →   Comment Worker
(after CTA          [job, job]           (follows if needed,
 detection)                               posts comment)

Comment Worker  →   [resource_queue]→   Resource Worker
(after comment      [job]                (monitors DMs,
 posted)                                  extracts resources)

Resource Worker →   [notion_queue]  →   Notion Sync Worker
(after resource     [job]                (creates Notion page)
 extracted)

QUEUE DEPTH MONITORING:
────────────────────────
GET /health/queue returns:
{
  "reel_queue": 2,
  "comment_queue": 1,
  "resource_queue": 0,
  "notion_queue": 3,
  "retry_queue": 0,
  "dead_letter_queue": 1
}
```

---

## 13. Database State Transitions

```
REEL STATUS STATE MACHINE:
────────────────────────────

         [CREATED]
              │
              ▼
    ┌─────[PENDING]────┐
    │         │         │
    │         ▼         │
    │  [EXTRACTING_     │
    │   CAPTION]        │ (error)
    │         │         │
    │         ▼         │
    │  [CTA_DETECTED]   │
    │   or [NO_CTA]     │
    │         │         │
    │         ▼         │
    │  [AWAITING_       │
    │   FOLLOW]         │
    │   (optional)      │
    │         │         │
    │         ▼         │
    │  [COMMENTING]     │
    │         │         │
    │         ▼         │
    │  [COMMENTED]      │
    │         │         │
    │         ▼         │
    │  [WAITING_DM]     │
    │         │         │
    │    ┌────┴────┐     │
    │    ▼         ▼    │
    │ [DM_TIMEOUT] │    │
    │              ▼    │
    │    [DM_RECEIVED]  │
    │              │    │
    │              ▼    │
    │  [EXTRACTING_     │
    │   RESOURCE]       │
    │              │    │
    └──────────────┴────┘
                   │
              ┌────┴────┐
              ▼         ▼
         [COMPLETED] [FAILED]
```

---

## 14. Human-Like Worker Strategy

```
┌─────────────────────────────────────────────────────────────┐
│               HUMAN-LIKE BEHAVIOR SYSTEM                    │
└─────────────────────────────────────────────────────────────┘

CORE PRINCIPLE:
All automated actions mimic realistic human Instagram usage
patterns. Actions are never instantaneous or perfectly timed.

1. TIMING RANDOMIZATION
────────────────────────
Action delays (configurable in .env):

  Load reel:         wait 3–8 seconds  (reading time)
  Before follow:     wait 5–20 seconds
  Before comment:    wait 10–30 seconds
  Between polls:     wait 45–90 seconds
  After rate limit:  wait 5–10 minutes
  Between sessions:  wait 2–5 minutes (idle)

2. TYPING SIMULATION
─────────────────────
Character-by-character typing:
  delay_per_char = random.uniform(0.05, 0.15) seconds
  Occasional "typo + delete" (configurable, default off)
  Pause before submit: random.uniform(1.5, 4.0) seconds

3. SCROLL BEHAVIOR
───────────────────
Before commenting:
  Scroll reel page down 200-400px
  Pause 1-3 seconds
  Scroll back to comment area
  Pause 0.5-1.5 seconds

4. SESSION MANAGEMENT
──────────────────────
  Browser context kept alive across jobs (same session)
  Browser closed after 5 minutes of inactivity
  New context opened when next job arrives
  Never open multiple browser instances simultaneously

5. DAILY LIMITS
────────────────
  Max follows per day: 10 (configurable)
  Max comments per day: 20 (configurable)
  Follow cooldown: 5 minutes between follows
  Comment cooldown: 2 minutes between comments

6. WATCH MODE STRATEGY
───────────────────────
  Worker does NOT run 24/7
  DM Listener runs in short burst cycles:
    - Active period: 10 minutes
    - Check interval: 60-90 seconds within cycle
    - Then sleep: 20-30 minutes
    - Repeat
  
  This mimics a human checking Instagram periodically
  rather than being permanently connected.

7. USER AGENT & BROWSER CONFIG
───────────────────────────────
  Consistent user agent (not randomized per request)
  Realistic viewport: 390x844 (iPhone 14 equivalent)
  Timezone: set to admin's local timezone
  Language: en-US
  Disable: automation flag, webdriver flag
```

---

## 15. Session Management Flow

```
SESSION LIFECYCLE:
───────────────────

INITIAL SETUP:
──────────────
1. Run: python automation/scripts/manual_login.py
2. Playwright opens visible Chromium browser
3. Navigate to instagram.com
4. Admin manually logs in (+ 2FA)
5. On success: save session
   context.storage_state(path="session/instagram_session.json")
6. Script prints: "Session saved. You can close the browser."
7. Browser closes

SESSION FILE CONTAINS:
───────────────────────
{
  "cookies": [...],        ← Instagram auth cookies
  "origins": [...]         ← Local storage state
}

WORKER SESSION RESTORE:
────────────────────────
On every worker start:
1. Check session file exists
2. Load into new Playwright context:
   browser.new_context(storage_state="path/to/session.json")
3. Navigate to instagram.com
4. Check: on feed? → valid session
5. Check: on login page? → session expired

SESSION EXPIRY HANDLING:
─────────────────────────
1. Log: SESSION_EXPIRED (critical)
2. Attempt automated re-login:
   a. Navigate to login
   b. Enter username from env
   c. Enter password from env
   d. Submit form
   e. Check for 2FA prompt
3. If 2FA required:
   a. Log: MFA_REQUIRED
   b. Send alert (via log)
   c. Pause worker
   d. Admin must complete manually
4. On success: save new session, resume
5. On failure after 3 attempts: stop worker

SESSION SECURITY:
──────────────────
  session.json → stored in /session/ directory
  /session/ → mounted as Docker volume (persists across container restarts)
  /session/ → never committed to git (.gitignore)
  Access: backend + worker only (not exposed to frontend)
```

---

*Document Version: 1.0.0 | Reelise MVP*
