# Release Notes - v0.3.1 Render Starter Plan Optimization

**Release Date**: 2026-01-19
**Type**: Performance / Stability Fix
**Commit**: `a9161ad`

---

## Overview

This release optimizes ScholaRAG_Graph for **Render Starter Plan** ($7/month) deployment, addressing intermittent 503 errors caused by database connection pool exhaustion. The fixes include backend connection pool tuning, frontend automatic retry logic, and improved error handling.

---

## Problem Statement

### Symptoms
- Intermittent `503 Service Unavailable` errors on `/api/projects/`
- CORS errors accompanying 503 responses (secondary effect)
- `500 Internal Server Error` on centrality/visualization endpoints
- Inconsistent API behavior (sometimes works, sometimes fails)

### Root Cause Analysis
| Issue | Root Cause |
|-------|------------|
| 503 errors | Database connection pool (min=5, max=20) too large for free-tier DB (~20 connection limit) |
| CORS errors | 503 responses don't include CORS headers |
| Intermittent failures | Connection pool exhaustion under concurrent requests |

---

## Changes

### Backend Optimizations

#### 1. Database Connection Pool Tuning
**File**: `backend/database.py`

```python
# Before (problematic)
min_size=5, max_size=20, command_timeout=60.0

# After (optimized for Starter)
min_size=2, max_size=5, command_timeout=30.0
max_inactive_connection_lifetime=300.0  # Close idle connections after 5 min
```

**Rationale**:
- Free-tier databases (Supabase, Render PostgreSQL) have ~20 connection limit
- Smaller pool prevents exhaustion under concurrent requests
- Idle connection cleanup prevents stale connections

#### 2. Health Check Enhancement
**File**: `backend/main.py`

- Returns `503 Service Unavailable` when database is disconnected
- Previously returned `200 OK` even when DB was down
- Adds `llm_provider` field to health response

#### 3. LLM Provider Validation
**File**: `backend/config.py`

- Added `validate_llm_keys()` method
- Clear error messages when no LLM API key is configured
- Supports Anthropic, OpenAI, and Groq providers

#### 4. Improved Error Logging
**File**: `backend/routers/graph.py`

- Added `exc_info=True` to centrality endpoint errors
- Provides full stack trace for debugging

---

### Frontend Optimizations

#### 1. Automatic Retry Logic
**File**: `frontend/lib/api.ts`

```typescript
/**
 * Make API request with automatic retry for transient errors (503).
 *
 * Render Starter plan has zero downtime (no cold starts), but may have
 * transient 503 errors due to DB connection pool exhaustion.
 * Fast retry with short delays handles these gracefully.
 */
private async request<T>(
  endpoint: string,
  options: RequestInit = {},
  retries: number = 3
): Promise<T> {
  // Retry on 503 with fast exponential backoff: 500ms, 1s, 1.5s
  if (response.status === 503 && attempt < retries) {
    await this.delay(500 * attempt);
    continue;
  }
}
```

**Why fast backoff for Starter?**
- Starter plan has **zero cold starts** (server always warm)
- 503 errors are transient DB connection issues
- Fast retries (500ms) quickly recover without user noticing

#### 2. Hardcoded Fallback URL
**File**: `frontend/lib/api.ts`

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || (
  typeof window !== 'undefined' && window.location.hostname !== 'localhost'
    ? 'https://scholarag-graph-api.onrender.com'  // Production fallback
    : 'http://localhost:8000'  // Development
);
```

**Rationale**: Prevents empty URL issues when Vercel env vars are not set.

#### 3. StatusBar Silent Fallback
**File**: `frontend/components/graph/StatusBar.tsx`

- Silently handles missing `/api/system/status` endpoint
- Shows default values instead of error state

#### 4. GapPanel HTML Fix
**File**: `frontend/components/graph/GapPanel.tsx`

- Fixed button nesting error (`<button>` inside `<button>`)
- Improves HTML validity and accessibility

#### 5. Supabase Error Logging
**File**: `frontend/lib/supabase.ts`

- Improved console logging when credentials are not configured
- Helps debug authentication issues in production

---

## Render Starter Plan Characteristics

| Feature | Starter ($7/mo) | Free ($0) |
|---------|-----------------|-----------|
| Cold Starts | **None** | 15 min sleep |
| DB Connections | ~20 limit | ~20 limit |
| Recovery Strategy | Fast retry (500ms) | Long retry (1-3s) |
| Uptime | 24/7 | On-demand |

**Optimization Focus**: Since Starter has no cold starts, we use faster retry intervals.

---

## Verification Results

### Stability Test
```bash
# 5 consecutive requests to /api/projects/
Test 1: 200 OK
Test 2: 200 OK
Test 3: 200 OK
Test 4: 200 OK
Test 5: 200 OK
```

### Endpoint Tests
```bash
# Health Check
curl https://scholarag-graph-api.onrender.com/health
{"status":"healthy","database":"connected","llm_provider":"groq"}

# Visualization (156KB response)
curl https://scholarag-graph-api.onrender.com/api/graph/visualization/{project_id}
{"nodes":[...], "edges":[...]}  # 200 OK

# Centrality
curl https://scholarag-graph-api.onrender.com/api/graph/centrality/{project_id}
{"metric":"betweenness","centrality":{...},"top_bridges":[...]}  # 200 OK
```

---

## Files Changed

| File | Changes | Description |
|------|---------|-------------|
| `backend/database.py` | +16, -4 | Connection pool optimization |
| `backend/main.py` | +58, -6 | Health check enhancement |
| `backend/config.py` | +59, -1 | LLM validation |
| `backend/routers/graph.py` | +9, -1 | Error logging |
| `frontend/lib/api.ts` | +89, -17 | Retry logic |
| `frontend/lib/supabase.ts` | +13, -1 | Error logging |
| `frontend/components/graph/StatusBar.tsx` | +12, -12 | Silent fallback |
| `frontend/components/graph/GapPanel.tsx` | +9, -2 | HTML fix |

**Total**: 9 files, +257 insertions, -46 deletions

---

## Configuration

### Environment Variables (Render Dashboard)

| Key | Required | Description |
|-----|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `DEFAULT_LLM_PROVIDER` | Recommended | `groq`, `openai`, or `anthropic` |
| `GROQ_API_KEY` | If using Groq | Free API key |
| `CORS_ORIGINS` | Recommended | Comma-separated allowed origins |

### Environment Variables (Vercel Dashboard)

| Key | Required | Description |
|-----|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Recommended | Backend URL (has fallback) |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase anon key |

---

## Migration Notes

### From v0.3.0 or earlier

No breaking changes. Deployment will:
1. Auto-apply connection pool settings on server restart
2. Frontend retry logic activates immediately

### Recommended Post-Deployment Steps

1. **Clear browser cache**: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
2. **Verify health**: `curl https://scholarag-graph-api.onrender.com/health`
3. **Test graph load**: Navigate to a project and verify graph renders

---

## Known Limitations

1. **Free-tier DB limits**: Connection exhaustion can still occur under very high load
2. **Retry visibility**: Users don't see retry attempts (intentional for UX)
3. **StatusBar fallback**: Shows placeholder data if `/api/system/status` not implemented

---

## Credits

Optimization implemented with Claude Code (Opus 4.5).
Production debugging session: 2026-01-19

---

## Related Documents

- Session Log: `DOCS/.meta/sessions/2026-01-19_render-starter-optimization.md`
- Action Items: `DOCS/project-management/action-items.md`
- Previous Release: `RELEASE_NOTES_v0.3.0.md`
