# FRONTEND_GUIDELINES.md — Reelise
**Version:** 1.0.0
**Status:** MVP
**Last Updated:** 2025

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Visual Identity](#2-visual-identity)
3. [Typography System](#3-typography-system)
4. [Color System](#4-color-system)
5. [Spacing System](#5-spacing-system)
6. [Component Architecture](#6-component-architecture)
7. [Folder Structure](#7-folder-structure)
8. [Page Layouts](#8-page-layouts)
9. [State Management](#9-state-management)
10. [API Integration](#10-api-integration)
11. [Loading States](#11-loading-states)
12. [Error States](#12-error-states)
13. [Responsive Design](#13-responsive-design)
14. [Accessibility](#14-accessibility)
15. [TailwindCSS Standards](#15-tailwindcss-standards)
16. [Dashboard Design Specification](#16-dashboard-design-specification)

---

## 1. Design Philosophy

### Core Principle: Clarity Over Decoration

The Reelise frontend is a **monitoring and retrieval tool** — not a marketing page. Every design decision must serve either:

1. **Operational awareness** — What is the system doing right now?
2. **Knowledge retrieval** — Find a specific resource quickly

### Design Persona

Think: **developer tool meets productivity dashboard**. The aesthetic is dark, dense, and information-rich — similar to Linear, Raycast, or Railway's own dashboard. Clean, minimal, with data-forward components.

### Anti-Patterns (Never Do)

- ❌ Decorative animations that don't communicate state
- ❌ Full-page loading spinners for partial data
- ❌ Generic placeholder text ("Loading...")
- ❌ Empty states without action prompts
- ❌ Modal confirmations for non-destructive actions
- ❌ Pagination where infinite scroll works better
- ❌ Tables without sorting or filtering
- ❌ Success toasts that auto-dismiss before user reads them

---

## 2. Visual Identity

### Theme: Dark-first

The primary theme is **dark**. Reasoning:
- Users will monitor this dashboard during heavy browsing sessions
- Dark reduces eye strain during long sessions
- Data tables are more readable on dark backgrounds
- Status colors (green/red/yellow) pop on dark

### Aesthetic Reference

**Primary inspiration:** Linear, Vercel Dashboard, Railway
**Secondary inspiration:** Raycast, Supabase Dashboard

### Logo & Naming

- Product name: **Reelise**
- Wordmark style: lowercase, monospace-adjacent
- Icon concept: reel (film/Instagram) + knowledge node

---

## 3. Typography System

### Font Pairing

```css
/* Primary: Display + UI text */
--font-sans: 'Geist', 'Inter Variable', system-ui, sans-serif;

/* Secondary: Code, IDs, URLs, technical data */
--font-mono: 'Geist Mono', 'JetBrains Mono', 'Fira Code', monospace;
```

**Load via Next.js `next/font`:**
```tsx
import { GeistSans } from 'geist/font/sans'
import { GeistMono } from 'geist/font/mono'
```

### Type Scale

```css
/* Scale — Tailwind classes */
text-xs    → 12px / 16px  — metadata, timestamps, badges
text-sm    → 14px / 20px  — table content, descriptions, labels
text-base  → 16px / 24px  — body text, card content
text-lg    → 18px / 28px  — card titles, section headers
text-xl    → 20px / 28px  — page section titles
text-2xl   → 24px / 32px  — page titles
text-3xl   → 30px / 36px  — metric numbers, hero stats
text-4xl   → 36px / 40px  — dashboard hero metric
```

### Font Weight Standards

```
font-normal  (400) — body text, descriptions
font-medium  (500) — labels, navigation items
font-semibold (600) — card titles, table headers
font-bold    (700) — metric values, status badges, page titles
```

### Typography Rules

- **Metric numbers** → `text-3xl font-bold font-mono`
- **Table headers** → `text-xs font-semibold uppercase tracking-wider text-zinc-400`
- **Status text** → `text-xs font-medium`
- **Creator names** → `text-sm font-medium`
- **Reel captions** → `text-sm text-zinc-400 line-clamp-2`
- **Timestamps** → `text-xs text-zinc-500 font-mono`
- **URLs** → `text-xs font-mono text-blue-400 truncate`

---

## 4. Color System

### Palette (CSS Variables in `globals.css`)

```css
:root {
  /* Background layers */
  --bg-base:       #09090b;   /* zinc-950 — page background */
  --bg-surface:    #18181b;   /* zinc-900 — card/panel bg */
  --bg-elevated:   #27272a;   /* zinc-800 — hover, selected */
  --bg-overlay:    #3f3f46;   /* zinc-700 — dividers, borders */

  /* Text */
  --text-primary:  #fafafa;   /* zinc-50 */
  --text-secondary:#a1a1aa;   /* zinc-400 */
  --text-muted:    #71717a;   /* zinc-500 */
  --text-disabled: #52525b;   /* zinc-600 */

  /* Brand */
  --brand:         #6366f1;   /* indigo-500 */
  --brand-hover:   #4f46e5;   /* indigo-600 */
  --brand-subtle:  #1e1b4b;   /* indigo-950 */

  /* Status Colors */
  --status-pending:    #f59e0b;   /* amber-500 */
  --status-processing: #3b82f6;   /* blue-500 */
  --status-completed:  #10b981;   /* emerald-500 */
  --status-failed:     #ef4444;   /* red-500 */
  --status-timeout:    #f97316;   /* orange-500 */
  --status-no-cta:     #6b7280;   /* gray-500 */

  /* Status subtle backgrounds */
  --status-pending-bg:    #451a03;
  --status-processing-bg: #172554;
  --status-completed-bg:  #052e16;
  --status-failed-bg:     #450a0a;

  /* Border */
  --border:        #27272a;   /* zinc-800 */
  --border-hover:  #3f3f46;   /* zinc-700 */
}
```

### Tailwind Config Extension

```js
// tailwind.config.ts
colors: {
  zinc: { /* default zinc palette */ },
  brand: {
    DEFAULT: '#6366f1',
    hover: '#4f46e5',
    subtle: '#1e1b4b',
  },
  status: {
    pending: '#f59e0b',
    processing: '#3b82f6',
    completed: '#10b981',
    failed: '#ef4444',
    timeout: '#f97316',
    'no-cta': '#6b7280',
  }
}
```

### Status Badge Colors

```tsx
const statusConfig = {
  pending:           { bg: 'bg-amber-950',   text: 'text-amber-400',   dot: 'bg-amber-500'   },
  processing:        { bg: 'bg-blue-950',    text: 'text-blue-400',    dot: 'bg-blue-500'    },
  commenting:        { bg: 'bg-blue-950',    text: 'text-blue-400',    dot: 'bg-blue-400 animate-pulse' },
  completed:         { bg: 'bg-emerald-950', text: 'text-emerald-400', dot: 'bg-emerald-500' },
  failed:            { bg: 'bg-red-950',     text: 'text-red-400',     dot: 'bg-red-500'     },
  dm_timeout:        { bg: 'bg-orange-950',  text: 'text-orange-400',  dot: 'bg-orange-500'  },
  no_cta:            { bg: 'bg-zinc-800',    text: 'text-zinc-400',    dot: 'bg-zinc-500'    },
}
```

---

## 5. Spacing System

### Base Unit: 4px (Tailwind default)

```
Tailwind scale → actual size:
p-1  = 4px     (tight internal padding)
p-2  = 8px     (badge padding, small elements)
p-3  = 12px    (input padding)
p-4  = 16px    (card padding — standard)
p-5  = 20px    (card padding — comfortable)
p-6  = 24px    (section padding)
p-8  = 32px    (page section gaps)
p-12 = 48px    (page padding x)
p-16 = 64px    (large section separation)
```

### Layout Spacing Conventions

```
Page horizontal padding:  px-6 (24px) mobile, px-8 (32px) desktop
Page vertical padding:    py-8 (32px) top, py-6 (24px) bottom
Section gap:              gap-6 (24px) or gap-8 (32px)
Card padding:             p-4 (16px) compact, p-6 (24px) default
Table cell padding:       px-4 py-3
Sidebar width:            w-56 (224px) collapsed, w-64 (256px) expanded
Header height:            h-14 (56px)
```

---

## 6. Component Architecture

### Atomic Structure

```
atoms/           → Button, Badge, Input, Spinner, Icon, Dot
molecules/       → SearchBar, StatusBadge, MetricCard, ReelCard
organisms/       → ReelTable, ResourceGrid, LogViewer, SideNav
templates/       → DashboardLayout, ContentPageLayout
pages/           → app/ directory (Next.js App Router)
```

### Key Component Contracts

#### `<StatusBadge status={ReelStatus} />`
```tsx
interface StatusBadgeProps {
  status: ReelStatus;
  showDot?: boolean;     // default: true
  size?: 'sm' | 'md';   // default: 'sm'
}
```

#### `<MetricCard title label value delta />`
```tsx
interface MetricCardProps {
  title: string;
  value: string | number;
  label?: string;
  delta?: { value: number; direction: 'up' | 'down' };
  loading?: boolean;
}
```

#### `<ReelRow reel onSelect />`
```tsx
interface ReelRowProps {
  reel: ReelRecord;
  onSelect?: (id: string) => void;
  isSelected?: boolean;
}
```

#### `<LogEntry log />`
```tsx
interface LogEntryProps {
  log: ProcessLog;
  expanded?: boolean;
}
```

### shadcn/ui Usage Pattern

Always extend shadcn components — never use raw Radix:

```tsx
// ✅ Correct — extends shadcn
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

// ❌ Avoid — raw Radix in page code
import * as Dialog from '@radix-ui/react-dialog'
```

### Component File Naming

```
PascalCase for components:  ReelTable.tsx
camelCase for utilities:    formatStatus.ts
kebab-case for pages:       app/history/page.tsx
```

---

## 7. Folder Structure

```
frontend/
├── app/                          ← Next.js App Router
│   ├── layout.tsx                ← Root layout (font, theme, providers)
│   ├── page.tsx                  ← Redirect to /dashboard
│   ├── dashboard/
│   │   └── page.tsx              ← Main dashboard
│   ├── history/
│   │   ├── page.tsx              ← Reel history table
│   │   └── [id]/
│   │       └── page.tsx          ← Single reel detail
│   ├── resources/
│   │   ├── page.tsx              ← Resource gallery
│   │   └── [id]/
│   │       └── page.tsx          ← Single resource detail
│   ├── logs/
│   │   └── page.tsx              ← Process logs viewer
│   ├── search/
│   │   └── page.tsx              ← Search interface
│   ├── analytics/
│   │   └── page.tsx              ← Metrics and charts
│   └── creators/
│       └── page.tsx              ← Creator relationships
│
├── components/
│   ├── ui/                       ← shadcn/ui components (auto-generated)
│   ├── layout/
│   │   ├── SideNav.tsx           ← Sidebar navigation
│   │   ├── Header.tsx            ← Top header bar
│   │   ├── PageContainer.tsx     ← Standard page wrapper
│   │   └── AppProviders.tsx      ← React Query + theme providers
│   ├── dashboard/
│   │   ├── MetricCard.tsx
│   │   ├── MetricsGrid.tsx
│   │   ├── RecentReels.tsx
│   │   ├── PipelineStatus.tsx
│   │   └── SuccessRateChart.tsx
│   ├── reels/
│   │   ├── ReelTable.tsx
│   │   ├── ReelRow.tsx
│   │   ├── ReelDetail.tsx
│   │   ├── ReelStatusBadge.tsx
│   │   └── CTADetails.tsx
│   ├── resources/
│   │   ├── ResourceGrid.tsx
│   │   ├── ResourceCard.tsx
│   │   ├── ResourceDetail.tsx
│   │   └── ResourceTypeIcon.tsx
│   ├── logs/
│   │   ├── LogTable.tsx
│   │   ├── LogEntry.tsx
│   │   └── LogFilters.tsx
│   └── search/
│       ├── SearchBar.tsx
│       ├── SearchResults.tsx
│       └── SearchResult.tsx
│
├── lib/
│   ├── api/
│   │   ├── client.ts             ← Axios instance + interceptors
│   │   ├── reels.ts              ← Reel API calls
│   │   ├── resources.ts          ← Resource API calls
│   │   ├── logs.ts               ← Log API calls
│   │   ├── analytics.ts          ← Analytics API calls
│   │   └── search.ts             ← Search API calls
│   ├── hooks/
│   │   ├── useReels.ts           ← React Query hooks for reels
│   │   ├── useResources.ts
│   │   ├── useLogs.ts
│   │   ├── useAnalytics.ts
│   │   └── useSearch.ts
│   ├── types/
│   │   ├── reel.ts               ← Reel TypeScript types
│   │   ├── resource.ts
│   │   ├── log.ts
│   │   └── api.ts                ← API response wrapper types
│   └── utils/
│       ├── formatDate.ts
│       ├── formatStatus.ts
│       ├── cn.ts                 ← clsx + tailwind-merge utility
│       └── constants.ts
│
├── public/
│   └── favicon.ico
│
├── .env.local
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

## 8. Page Layouts

### Dashboard Layout (All Pages)

```
┌──────────────────────────────────────────────────────────────┐
│  HEADER                                              h-14    │
│  [logo] [nav breadcrumb]          [status dot] [health]      │
├────────────┬─────────────────────────────────────────────────┤
│            │                                                  │
│  SIDEBAR   │  MAIN CONTENT AREA                              │
│  w-56      │  flex-1, overflow-y-auto                        │
│            │  px-8 py-6                                       │
│  ─────     │                                                  │
│  Dashboard │                                                  │
│  History   │                                                  │
│  Resources │                                                  │
│  Logs      │                                                  │
│  Search    │                                                  │
│  Analytics │                                                  │
│  ─────     │                                                  │
│  Creators  │                                                  │
│            │                                                  │
└────────────┴─────────────────────────────────────────────────┘
```

### Dashboard Page

```
METRICS ROW (4 cards):
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│  Reels   │ │Resources │ │ Comment  │ │  Follow  │
│ Processed│ │Collected │ │ Success  │ │ Success  │
│    47    │ │    31    │ │   94%    │ │   98%    │
└──────────┘ └──────────┘ └──────────┘ └──────────┘

PIPELINE STATUS (live):
┌─────────────────────────────────────────────────────────────┐
│ Active Pipeline                                    2 active │
│ ─────────────────────────────────────────────────────────── │
│ [spinner] @fitnesscreator    commenting...          2m ago  │
│ [spinner] @aicreator         waiting for DM...      5m ago  │
└─────────────────────────────────────────────────────────────┘

TWO COLUMNS:
┌─────────────────────────────┐ ┌──────────────────────────────┐
│ Recent Reels                │ │ Recent Resources             │
│ ─────────────────────────── │ │ ─────────────────────────── │
│ Creator  │ Status │ Time    │ │ [type] Creator  │ Category  │
│ @user    │ ✅done  │ 5m     │ │ 📄 @dev  PDF    │ Prog.     │
│ @user2   │ 🔄proc  │ 2m     │ │ 🔗 @ai   Link   │ AI        │
│ @user3   │ ⏳wait  │ 8m     │ │ 📄 @fit  PDF    │ Fitness   │
└─────────────────────────────┘ └──────────────────────────────┘
```

### History Page

```
┌─────────────────────────────────────────────────────────────┐
│ Reel History                           [Filter ▼] [Search]  │
│ ─────────────────────────────────────────────────────────── │
│ CREATOR    │ STATUS      │ CTA      │ KEYWORD │ PROCESSED   │
│ ─────────────────────────────────────────────────────────── │
│ @creator1  │ ✅ completed │ comment  │ GUIDE   │ 2h ago      │
│ @creator2  │ ❌ failed    │ follow+  │ PDF     │ 4h ago      │
│ @creator3  │ ⏸ dm_timeout│ comment  │ AI      │ 1d ago      │
│ @creator4  │ ✅ completed │ none     │ —       │ 2d ago      │
│ ─────────────────────────────────────────────────────────── │
│ Showing 1-20 of 47                       [< Prev] [Next >]  │
└─────────────────────────────────────────────────────────────┘
```

### Resources Page

```
[Filter: All / AI / Career / Programming / Fitness / Other]
[Sort: Newest / Oldest]  [View: Grid / List]

┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ 📄 PDF        │ │ 🔗 Link      │ │ 📄 PDF        │
│ @devfolio     │ │ @aicreators  │ │ @fitpro       │
│ Programming   │ │ AI           │ │ Fitness       │
│ Python Guide  │ │ ChatGPT Tips │ │ Workout Plan  │
│ 3h ago        │ │ 1d ago       │ │ 2d ago        │
│ [Open] [View] │ │ [Open] [View]│ │ [Open] [View] │
└──────────────┘ └──────────────┘ └──────────────┘
```

### Logs Page

```
┌─────────────────────────────────────────────────────────────┐
│ Process Logs          [Filter: All/Error] [Reel: All ▼]     │
│ ─────────────────────────────────────────────────────────── │
│ 14:32:01 │ ✅ CAPTION_EXTRACTED    │ @creator1              │
│ 14:32:15 │ ✅ CTA_DETECTED         │ requires_comment=true  │
│ 14:32:45 │ ✅ COMMENTED            │ keyword=GUIDE          │
│ 14:45:22 │ ✅ DM_RECEIVED          │ from @creator1         │
│ 14:45:35 │ ✅ RESOURCE_EXTRACTED   │ type=link              │
│ 14:45:40 │ ✅ NOTION_SYNCED        │                        │
│ ─────────────────────────────────────────────────────────── │
│ 13:18:00 │ ❌ COMMENT_FAILED       │ rate_limited           │
│           └─ Error: Instagram rate limit. Retry in 5min.    │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. State Management

### Server State: TanStack Query v5

All API data is server state — managed by React Query.

```tsx
// lib/hooks/useReels.ts
export function useReels(filters?: ReelFilters) {
  return useQuery({
    queryKey: ['reels', filters],
    queryFn: () => api.reels.list(filters),
    staleTime: 30_000,        // 30 seconds
    refetchInterval: 30_000,  // Auto-refresh dashboard
  })
}

export function useReel(id: string) {
  return useQuery({
    queryKey: ['reels', id],
    queryFn: () => api.reels.get(id),
    staleTime: 10_000,
  })
}
```

### Refresh Strategy

| Page | Refresh Interval |
|---|---|
| Dashboard | 30 seconds |
| Pipeline Status | 15 seconds |
| Logs | 20 seconds |
| History | On focus |
| Resources | On focus |
| Analytics | 5 minutes |

### Local UI State

Only for: modal open/close, filter selections, tab state, search input debounce.
Use `useState` directly — no external state library needed.

---

## 10. API Integration

### Axios Client (`lib/api/client.ts`)

```ts
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor — add correlation ID
apiClient.interceptors.request.use((config) => {
  config.headers['X-Request-ID'] = crypto.randomUUID()
  return config
})

// Response interceptor — normalize errors
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || 'Unknown error'
    throw new APIError(message, error.response?.status)
  }
)
```

### API Response Shape (standardized)

```ts
interface APIResponse<T> {
  data: T;
  meta?: {
    total: number;
    page: number;
    per_page: number;
  };
}

interface APIError {
  detail: string;
  code: string;
  timestamp: string;
}
```

---

## 11. Loading States

### Skeleton Strategy

Every data component must have a skeleton variant:

```tsx
// Pattern: conditional render
function ReelTable({ reels, isLoading }) {
  if (isLoading) return <ReelTableSkeleton rows={10} />
  return <ReelTableContent reels={reels} />
}
```

### Skeleton Component

```tsx
// Use shadcn Skeleton
import { Skeleton } from '@/components/ui/skeleton'

function MetricCardSkeleton() {
  return (
    <div className="p-6 rounded-lg border border-zinc-800 bg-zinc-900">
      <Skeleton className="h-4 w-24 mb-3 bg-zinc-800" />
      <Skeleton className="h-8 w-16 bg-zinc-800" />
    </div>
  )
}
```

### Loading State Rules

- **Metric cards** → show skeleton with same dimensions
- **Tables** → show 10 skeleton rows matching column count
- **Status badges** → show pulsing dot, not spinner
- **Resource cards** → show skeleton cards in grid
- **Never** → block entire page with loading overlay

---

## 12. Error States

### Error Boundary (Page-Level)

```tsx
// components/layout/ErrorBoundary.tsx
function ErrorFallback({ error, resetErrorBoundary }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4">
      <div className="text-zinc-500 text-sm font-mono">
        {error.message}
      </div>
      <Button variant="outline" size="sm" onClick={resetErrorBoundary}>
        Try Again
      </Button>
    </div>
  )
}
```

### Component-Level Error States

```tsx
// Pattern for data components
function ReelTable() {
  const { data, isLoading, error } = useReels()

  if (error) return (
    <div className="py-8 text-center text-sm text-zinc-500">
      Failed to load reels. 
      <button className="ml-1 text-brand underline">Retry</button>
    </div>
  )
}
```

### Empty States (with context)

```tsx
function EmptyReels() {
  return (
    <div className="py-16 text-center">
      <p className="text-zinc-400 text-sm">No reels processed yet.</p>
      <p className="text-zinc-600 text-xs mt-1">
        Share a reel to @reelise_collector on Instagram to get started.
      </p>
    </div>
  )
}
```

---

## 13. Responsive Design

### Breakpoints (Tailwind defaults)

```
sm:  640px  — unused (this is a dashboard, not mobile-first)
md:  768px  — sidebar collapses
lg:  1024px — standard dashboard layout
xl:  1280px — wider content areas
2xl: 1536px — max content width cap
```

### Dashboard Responsiveness

```
< 768px (mobile):
  - Sidebar hidden, hamburger menu
  - Single column metrics
  - Table → card list view
  - Simplified header

768px–1024px (tablet):
  - Sidebar icon-only (collapsed)
  - 2-column metrics
  - Full table

> 1024px (desktop):
  - Full sidebar with labels
  - 4-column metrics
  - Full table with all columns
```

---

## 14. Accessibility

### Minimum Requirements (WCAG 2.1 AA)

- All interactive elements keyboard-navigable
- Focus rings visible on keyboard navigation
- Color is never the sole indicator (always pair with text/icon)
- Status badges include sr-only text descriptions
- Tables have proper `<thead>` / `<th scope>` markup
- Images have `alt` text
- Loading states announce to screen readers

### Focus Ring Customization

```css
/* globals.css */
:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 2px;
  border-radius: 4px;
}
```

### Screen Reader Helpers

```tsx
// Status badge with sr-only
<Badge>
  <span aria-hidden="true">✅</span>
  <span>{status}</span>
  <span className="sr-only">Status: {status}</span>
</Badge>
```

---

## 15. TailwindCSS Standards

### Class Ordering Convention

Follow Tailwind's recommended order:
1. Layout (display, position, flex, grid)
2. Box model (width, height, margin, padding)
3. Typography (font, text)
4. Visual (background, border, shadow, opacity)
5. Interactive (hover, focus, active)
6. Responsive prefixes last

### Utility Patterns

```tsx
// Page container
'flex flex-col gap-6 px-8 py-6 max-w-screen-xl mx-auto'

// Card
'rounded-lg border border-zinc-800 bg-zinc-900 p-6'

// Card hover
'rounded-lg border border-zinc-800 bg-zinc-900 p-6 hover:border-zinc-700 transition-colors'

// Table header cell
'px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-zinc-400'

// Table data cell
'px-4 py-3 text-sm text-zinc-300'

// Primary button
'bg-brand hover:bg-brand-hover text-white font-medium px-4 py-2 rounded-md text-sm'

// Ghost button
'border border-zinc-700 hover:border-zinc-600 hover:bg-zinc-800 text-zinc-300 px-4 py-2 rounded-md text-sm'
```

### cn() Utility (Required)

```ts
// lib/utils/cn.ts
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

Always use `cn()` for conditional classes — never string concatenation.

### Forbidden Patterns

```tsx
// ❌ Never
className={`bg-zinc-900 ${isActive ? 'border-brand' : 'border-zinc-800'}`}

// ✅ Always
className={cn('bg-zinc-900', isActive ? 'border-brand' : 'border-zinc-800')}
```

---

## 16. Dashboard Design Specification

### Sidebar Navigation Items

```
/ dashboard     → "Dashboard"      [LayoutDashboard icon]
/ history       → "Reel History"   [Film icon]
/ resources     → "Resources"      [Database icon]
/ logs          → "Logs"           [ScrollText icon]
/ search        → "Search"         [Search icon]
/ analytics     → "Analytics"      [BarChart icon]
─────────────────────────────────────
/ creators      → "Creators"       [Users icon]
```

### Header Content

```
Left:   [Reelise logo/wordmark] / [Page breadcrumb]
Right:  [System health dot + label] [Queue depth badge]
```

### System Health Dot

```tsx
// Green pulsing = healthy, Yellow = degraded, Red = down
<span className={cn(
  'h-2 w-2 rounded-full',
  health === 'healthy'  && 'bg-emerald-500 animate-pulse',
  health === 'degraded' && 'bg-amber-500',
  health === 'down'     && 'bg-red-500',
)} />
```

---

*Document Version: 1.0.0 | Reelise MVP*
