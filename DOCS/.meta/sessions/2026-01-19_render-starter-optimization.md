# Session Log: Render Starter Plan Optimization

**Session ID**: 2026-01-19_render-starter-optimization
**Date**: 2026-01-19
**Agent**: Claude Code (Opus 4.5)
**Type**: Performance Optimization / Bug Fix
**Duration**: ~1.5 hours

---

## Context

### User Request
> "Render 스타터 플랜을 유지하고 싶어. 유지하는 차원에서 최적화를 해줘"

User wanted to keep Render Starter Plan ($7/month) while resolving intermittent 503 errors.

### Related Sessions
- `2026-01-19_production-deployment-fixes.md` - Initial production debugging
- `2026-01-19_infranodus-visualization.md` - v0.3.0 feature release

### Initial Problem
- Intermittent 503 errors on `/api/projects/`
- CORS errors accompanying 503 responses
- 500 errors on centrality/visualization endpoints

---

## Exploration Phase

### Files Read
| Path | Purpose |
|------|---------|
| `backend/database.py` | Check connection pool settings |
| `frontend/lib/api.ts` | Understand API client behavior |
| `backend/config.py` | Check LLM provider configuration |
| `backend/main.py` | Check health endpoint |
| `frontend/components/graph/StatusBar.tsx` | Check status display |

### Key Findings

1. **Connection Pool Too Large**
   - `min_size=5, max_size=20` configured
   - Free-tier DBs have ~20 connection limit
   - Concurrent requests exhaust pool

2. **No Retry Logic**
   - Frontend API client had no retry mechanism
   - Transient 503 errors immediately shown to user

3. **Render Starter Characteristics**
   - $7/month = $0.0094/hour
   - **Zero cold starts** (server always warm)
   - DB connection is the bottleneck, not server startup

4. **CORS Header Missing on 503**
   - 503 responses don't include CORS headers
   - Browser reports CORS error, masking the actual 503

---

## Decisions Made

### Decision 1: Reduce Connection Pool Size

**Context**: Free-tier DBs have limited connections

**Options Considered**:
1. ❌ Upgrade to paid DB tier - Increases cost
2. ❌ Use connection pooler (PgBouncer) - Added complexity
3. ✅ **Reduce pool size** - Simple, effective, no cost

**Selected**: `min_size=2, max_size=5`

**Trade-offs**: May queue requests under very high load

---

### Decision 2: Fast Retry Logic for Starter Plan

**Context**: Starter has no cold starts, only transient DB issues

**Options Considered**:
1. ❌ Long retry delays (1-3 seconds) - Good for cold starts
2. ✅ **Fast retry delays (500ms)** - Better for transient errors
3. ❌ No retry - Poor user experience

**Selected**: 500ms × attempt number (500ms, 1s, 1.5s)

**Rationale**: Server is always warm on Starter, so fast retries work

---

### Decision 3: Hardcode Fallback API URL

**Context**: Empty env vars cause frontend to call `/api/...` on Vercel

**Options Considered**:
1. ❌ Require env var - Deployment friction
2. ✅ **Hardcode fallback** - Works out of the box
3. ❌ Use Vercel rewrites - Added complexity

**Selected**: Hardcode `https://scholarag-graph-api.onrender.com` as fallback

---

## Implementation Summary

### Changes Made
| File | Action | Description |
|------|--------|-------------|
| `backend/database.py` | Modified | Pool: min=2, max=5, idle cleanup |
| `frontend/lib/api.ts` | Modified | 3-retry logic with 500ms backoff |
| `backend/main.py` | Modified | Health returns 503 on DB failure |
| `backend/config.py` | Modified | LLM key validation |
| `backend/routers/graph.py` | Modified | Better error logging |
| `frontend/lib/supabase.ts` | Modified | Error logging |
| `frontend/components/graph/StatusBar.tsx` | Modified | Silent fallback |
| `frontend/components/graph/GapPanel.tsx` | Modified | HTML fix |

### Code Highlights

**Connection Pool (database.py)**:
```python
async def connect(
    self,
    min_size: int = 2,    # Reduced from 5
    max_size: int = 5,    # Reduced from 20
    command_timeout: float = 30.0,
) -> None:
    self._pool = await asyncpg.create_pool(
        dsn=self.dsn,
        min_size=min_size,
        max_size=max_size,
        command_timeout=command_timeout,
        max_inactive_connection_lifetime=300.0,  # 5 min idle cleanup
    )
```

**Retry Logic (api.ts)**:
```typescript
// Retry on 503 - transient DB connection issues
if (response.status === 503 && attempt < retries) {
  await this.delay(500 * attempt); // Fast backoff: 500ms, 1s, 1.5s
  continue;
}
```

---

## Validation

### Tests Performed
- [x] Health endpoint returns 200 with DB status
- [x] `/api/projects/` returns 200 consistently (5/5 attempts)
- [x] `/api/graph/visualization/` returns data (156KB)
- [x] `/api/graph/centrality/` returns data
- [x] Commit pushed, auto-deploy triggered

### Verification Commands
```bash
# Health check
curl https://scholarag-graph-api.onrender.com/health

# Stability test (5 requests)
for i in 1 2 3 4 5; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    https://scholarag-graph-api.onrender.com/api/projects/
done

# Endpoint test
curl https://scholarag-graph-api.onrender.com/api/graph/visualization/{id}
```

---

## Artifacts Created

### Documentation
- `RELEASE_NOTES_v0.3.1.md` - Full release documentation
- `DOCS/.meta/sessions/2026-01-19_render-starter-optimization.md` - This session log

### Code Changes
- Commit `a9161ad`: "fix(production): optimize DB pool and API retry for Render Starter plan"

---

## Follow-up Tasks

- [ ] **PERF-004**: Monitor 503 error rate after deployment - Assignee: DevOps
- [ ] **DOC-001**: Update deployment guide with Starter plan recommendations - Assignee: Docs Team
- [ ] **FUNC-003**: Implement `/api/system/status` endpoint - Assignee: Backend Team

---

## Session Statistics

| Metric | Value |
|--------|-------|
| Files Read | 6 |
| Files Modified | 9 |
| Lines Added | 257 |
| Lines Removed | 46 |
| Decisions Made | 3 |
| Follow-up Tasks | 3 |
| Commits | 1 |

---

## Notes

### Render Starter vs Free Plan

| Feature | Starter | Free |
|---------|---------|------|
| Cost | $7/mo | $0 |
| Cold Start | None | 15 min sleep |
| Retry Strategy | Fast (500ms) | Slow (1-3s) |

The retry logic is specifically optimized for Starter's zero-downtime characteristic.

### Future Considerations

1. **Connection Pooler**: If traffic increases, consider PgBouncer
2. **Upgrade Path**: Supabase Pro ($25/mo) has 60 connections
3. **Monitoring**: Add Sentry or similar for 503 tracking

---

## Related Documents

- Release Notes: `RELEASE_NOTES_v0.3.1.md`
- Action Items: `DOCS/project-management/action-items.md`
- Plan File: `~/.claude/plans/sleepy-cooking-dolphin.md`
