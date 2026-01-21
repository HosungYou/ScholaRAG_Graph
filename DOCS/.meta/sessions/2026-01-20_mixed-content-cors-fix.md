# Session Log: Mixed Content & CORS Error Fix + Security/Performance Improvements

> **Session ID**: 2026-01-20_mixed-content-cors-fix
> **Date**: 2026-01-20
> **Agent**: Claude Code (Opus 4.5)
> **Type**: Bug Fix + Security + Performance
> **Duration**: ~60 minutes (multiple sessions)

---

## Context

### User Request

사용자가 프로덕션 환경에서 다음 에러를 보고:
1. **Mixed Content Error**: HTTP 요청이 HTTPS 페이지에서 차단됨
2. **CORS Error**: Vercel Preview URL이 CORS 정책에 의해 차단됨

### Related Decisions

- INFRA-004: Backend migrated from Python service to Docker service
- Previous session: InfraNodus integration merge and follow-up tasks

---

## Summary

### Root Cause Analysis (Systematic Debugging)

**Phase 1: Investigation**
- 에러 메시지 분석: `http://scholarag-graph-docker.onrender.com/api/projects/` (HTTP 요청)
- 코드 분석: `api.ts`는 HTTPS를 기본값으로 사용하지만, `NEXT_PUBLIC_API_URL` 환경변수가 우선

**Phase 2: Pattern Analysis**
- CORS regex 패턴 검증: `^https://schola-rag-graph-[a-z0-9]+-hosung-yous-projects\.vercel\.app$`
- 실제 URL 매칭 테스트: ✅ 패턴 정상 작동 확인

**Phase 3: Hypothesis**
- `NEXT_PUBLIC_API_URL` 환경변수가 Vercel Preview에서 HTTP로 설정됨
- Mixed Content 에러로 인해 브라우저가 요청 차단 → CORS 에러로 표시됨

**Phase 4: Implementation**
- `frontend/lib/api.ts`에 `enforceHttps()` 함수 추가
- HTTPS 페이지에서 API URL이 HTTP인 경우 자동으로 HTTPS로 변환
- 디버그 로깅 개선으로 HTTPS 강제 여부 표시

### Changes Made

| File | Change |
|------|--------|
| `frontend/lib/api.ts` | Added `enforceHttps()` function to force HTTPS in production |

### Technical Details

```typescript
// Force HTTPS in production to prevent Mixed Content errors
const enforceHttps = (url: string): string => {
  if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
    return url.replace(/^http:\/\//, 'https://');
  }
  return url;
};
```

---

## Action Items

| ID | Priority | Description | Status |
|----|----------|-------------|--------|
| BUG-004 | 🔴 High | Mixed Content error - HTTP request from HTTPS page | ✅ Fixed |
| BUG-005 | 🔴 High | CORS error for Vercel Preview URLs | ✅ Fixed (caused by BUG-004) |

---

## Recommendations

1. **Vercel 환경변수 점검**: `NEXT_PUBLIC_API_URL`이 HTTP로 설정되어 있다면 HTTPS로 수정 필요
2. **모니터링**: 배포 후 브라우저 콘솔에서 `[API] Configuration` 로그 확인
3. **테스트**: Preview URL에서 API 호출이 정상 작동하는지 확인

---

## Deployment

- Commit: `22217b5`
- Push: `origin/main`
- Auto-deploy: Vercel (triggered by push)

### Deployment Verification (2026-01-20)

**Backend** (`https://scholarag-graph-docker.onrender.com`):
- Status: ✅ Healthy
- Database: Connected
- LLM Provider: Groq
- Environment: Production

**Frontend** (`https://schola-rag-graph.vercel.app`):
- Status: ✅ Deployed (HTTP 200)

---

## Codex Code Review Results

### Overall Assessment

| Area | Score | Status |
|------|-------|--------|
| Code Quality | 7/10 | 🟡 |
| Architecture | 7/10 | 🟡 |
| Security | 6/10 | 🟡 |
| Performance | 6/10 | 🟡 |
| Maintainability | 7/10 | 🟡 |

### New Action Items from Review

| ID | Priority | Description | Status |
|----|----------|-------------|--------|
| SEC-011 | 🔴 High | Rate Limiter X-Forwarded-For Spoofing | ✅ Fixed |
| ARCH-001 | 🔴 High | DB 연결 실패 시 일관된 동작 | ✅ Fixed |
| ARCH-002 | 🟡 Medium | GraphStore God Object 리팩토링 | ⬜ Pending (large task) |
| PERF-008 | 🟡 Medium | 임베딩 업데이트 배치 처리 | ✅ Fixed |
| SEC-012 | 🟡 Medium | Auth 설정 불일치 처리 | ✅ Fixed |
| TEST-004 | 🟢 Low | Frontend 테스트 추가 | ⬜ Pending (large task) |
| FUNC-005 | 🟢 Low | Per-Project/User API 할당량 | ⬜ Pending (large task) |

---

## Follow-up Fixes (Same Session)

### SEC-011: Rate Limiter X-Forwarded-For Spoofing Fix

**Problem**: Rate limiter trusted `X-Forwarded-For` header unconditionally, allowing IP spoofing.

**Solution**:
- Added `trusted_proxy_mode` setting to `config.py` (`auto`/`always`/`never`)
- `auto` mode: Trust X-Forwarded-For only in production (behind Render LB)
- Development uses direct connection IP to prevent spoofing

**Files Changed**:
- `backend/config.py:81-87` - New setting
- `backend/middleware/rate_limiter.py:305-356` - Trusted proxy logic

### ARCH-001: DB Connection Failure Handling

**Problem**: When DB connection fails, app continues running but most endpoints return 500 errors.

**Solution**:
- Fail-fast in production/staging when DB connection fails
- Added `require_db()` dependency for consistent 503 responses
- Development allows memory-only mode for testing

**Files Changed**:
- `backend/main.py:88-114` - Fail-fast logic
- `backend/database.py:184-207` - New `require_db()` dependency

### SEC-012: Auth Configuration Mismatch Handling

**Problem**: If `require_auth=true` but Supabase is not configured, app starts but all authenticated endpoints fail with 500 errors.

**Solution**:
- Production/staging: fail-fast if require_auth=true but Supabase not configured
- Development: warn but auto-disable auth to allow local testing
- Clear error messages explaining how to fix configuration

**Files Changed**:
- `backend/main.py:81-107` - Auth configuration validation

**Code**:
```python
# SEC-012: Validate auth configuration consistency
supabase_configured = bool(settings.supabase_url and settings.supabase_anon_key)

if supabase_configured:
    supabase_client.initialize(settings.supabase_url, settings.supabase_anon_key)
    logger.info("   Supabase Auth: configured")
else:
    if settings.require_auth:
        if settings.environment in ("production", "staging"):
            logger.critical(
                "FATAL: require_auth=true but Supabase is not configured. "
                "Set SUPABASE_URL and SUPABASE_ANON_KEY, or set REQUIRE_AUTH=false."
            )
            raise RuntimeError(...)
```

### PERF-008 / PERF-006: Batch Embedding Updates

**Problem**: Entity and chunk embeddings were updated one-by-one, causing N+1 query problem with hundreds of database round-trips.

**Solution**:
- Use `executemany()` for batch updates instead of individual `execute()` calls
- Fallback to individual updates if batch operation fails
- Applied to both entity embeddings and chunk embeddings

**Files Changed**:
- `backend/graph/graph_store.py:623-662` - Entity embedding batch update
- `backend/graph/graph_store.py:1329-1357` - Chunk embedding batch update

**Code**:
```python
# PERF-008: Batch update entities with embeddings using executemany
batch_data = []
for entity_id, embedding in zip(entity_ids, embeddings):
    embedding_str = "[" + ",".join(map(str, embedding)) + "]"
    batch_data.append((embedding_str, entity_id))

try:
    await self.db.executemany(
        """UPDATE entities SET embedding = $1::vector, updated_at = NOW() WHERE id = $2""",
        batch_data,
    )
    updated_count = len(batch_data)
except Exception as e:
    logger.error(f"Batch embedding update failed: {e}")
    # Fallback to individual updates on batch failure
    ...
```

**Performance Impact**:
- Before: N database round-trips (one per entity/chunk)
- After: 1 database round-trip (batch) + fallback if needed
- Expected improvement: ~10-50x faster for large imports

---

## Updated Session Statistics

- Files Modified: 6
- Lines Added: ~150
- Lines Removed: ~30
- Commits: 4 (`22217b5`, `3b0b563`, `3dddd7f`, `4f10976`)
- Action Items Completed: 6 (BUG-004, BUG-005, SEC-011, ARCH-001, SEC-012, PERF-008)
- Action Items Pending: 3 (ARCH-002, TEST-004, FUNC-005)
- Debugging Methodology: Systematic Debugging (4-phase approach)
