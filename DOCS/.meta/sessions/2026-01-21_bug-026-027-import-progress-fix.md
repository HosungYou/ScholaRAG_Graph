# Session Log: BUG-026/027 Import Progress Fixes

> **Session ID**: 2026-01-21_bug-026-027-import-progress-fix
> **Date**: 2026-01-21
> **Agent**: Claude Code (Opus 4.5)
> **Type**: Bug Fixes / Systematic Debugging
> **Skills Used**: `superpowers:systematic-debugging`, `superpowers:dispatching-parallel-agents`

---

## Context

### User Request
Zotero Import 시 Validation 단계에서 0%로 멈추는 문제. 이전에 BUG-026 (CORS/429) 수정 완료 후에도 progress가 업데이트되지 않음.

### Screenshots Analysis
1. **BUG-026**: CORS 에러 + 429 Too Many Requests
   - Origin: Vercel Preview URL
   - 원인: Rate limiter가 OPTIONS preflight 요청도 카운트

2. **BUG-027**: CORS 해결 후에도 progress 0%
   - Network: 200 OK 정상 응답
   - 문제: progress가 항상 0.0 반환

---

## BUG-026: CORS/429 Rate Limiter Issue

### Root Cause
Rate limiter가 OPTIONS preflight 요청을 일반 요청과 동일하게 rate limit에 카운트.
브라우저가 1초마다 폴링하면서 OPTIONS + GET 요청 쌍이 발생 → 60 req/min 초과 → 429 반환.

### Resolution
**File**: `backend/middleware/rate_limiter.py`

```python
# BUG-026: Skip rate limiting for OPTIONS preflight requests
if request.method == "OPTIONS":
    return await call_next(request)
```

**Commit**: `644a6fe`

---

## BUG-027: Import Progress Stuck at 0%

### Systematic Debugging Process

#### Phase 1: Root Cause Investigation

**Observation**:
- Network DevTools: 200 OK, CORS headers present
- Response body: `progress: 0.0` (항상)
- 98+ requests but progress never changes

**Code Tracing**:

1. **Status API** (`/api/import/status/{id}`):
```python
# Line 560-591: JobStore 먼저 조회
job_store = await get_job_store()
job = await job_store.get_job(job_id)
if job:
    return ImportJobResponse(progress=job.progress, ...)  # <-- 여기서 0.0 반환
# Fallback to _import_jobs (도달 안함)
```

2. **progress_callback** (Line 1361-1377):
```python
def progress_callback(progress):
    # 오직 _import_jobs만 업데이트!
    _import_jobs[job_id]["progress"] = progress.progress
    # job_store는 업데이트 안함!
```

3. **job_store.update_job** (Line 1381-1386):
```python
# 시작 시에만 호출 - progress=0.0으로 초기화
await job_store.update_job(job_id=job_id, status=RUNNING, progress=0.0, ...)
```

### Root Cause Identified

```
┌─────────────────────────────────────────────────────────────────┐
│                    Progress 업데이트 흐름 (문제)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Status API: JobStore 먼저 조회 → progress=0.0 반환            │
│                    ↓                                            │
│  progress_callback: _import_jobs만 업데이트                     │
│                    ↓                                            │
│  JobStore: 시작 시 한 번만 업데이트 (progress=0.0)              │
│                    ↓                                            │
│  결과: Frontend는 항상 0.0만 받음!                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Resolution

**File**: `backend/routers/import_.py`

3개의 progress_callback 모두 수정 (Zotero, PDF, Multi-PDF):

```python
def progress_callback(progress):
    # Update legacy in-memory store
    _import_jobs[job_id]["status"] = import_status
    _import_jobs[job_id]["progress"] = progress.progress
    _import_jobs[job_id]["message"] = progress.message
    _import_jobs[job_id]["updated_at"] = datetime.now()

    # BUG-027 FIX: Also update JobStore for persistent progress tracking
    try:
        import asyncio
        loop = asyncio.get_running_loop()
        loop.create_task(
            job_store.update_job(
                job_id=job_id,
                progress=progress.progress,
                message=progress.message,
            )
        )
    except RuntimeError:
        logger.warning("Could not update JobStore: no running event loop")

    logger.info(f"[Import {job_id}] {progress.status}: {progress.progress:.0%}")
```

**Key Insight**:
동기 함수(progress_callback) 내에서 비동기 함수(job_store.update_job) 호출을 위해
`asyncio.create_task()`를 사용하여 비동기 업데이트를 스케줄링.

**Commit**: `16531bc`

---

## Commits

| Commit | Description |
|--------|-------------|
| `644a6fe` | fix(BUG-026): skip OPTIONS preflight in rate limiter |
| `16531bc` | fix(BUG-027): progress_callback updates JobStore for real-time progress |

---

## Deployment Status

| Service | Platform | Status | Commit |
|---------|----------|--------|--------|
| Backend | Render | ⏳ Deploying | 16531bc |
| Frontend | Vercel | N/A (no changes) | - |

---

## Verification Pending

| Bug | Status | Test |
|-----|--------|------|
| BUG-026 | ✅ Completed | CORS headers present, 200 OK |
| BUG-027 | ⏳ Pending | Need new import to verify progress updates |

---

## Session Statistics

| Metric | Value |
|--------|-------|
| Bugs Fixed | 2 (BUG-026, BUG-027) |
| Files Modified | 2 (rate_limiter.py, import_.py) |
| Commits | 2 |
| Root Cause Analysis Time | ~20 minutes |
| Skills Used | superpowers:systematic-debugging |

---

## Key Learnings

### 1. JobStore vs Legacy In-Memory Store
프로젝트에서 두 가지 job 저장소를 사용:
- `JobStore`: 영구 저장소 (PostgreSQL 기반)
- `_import_jobs`: 레거시 인메모리 딕셔너리

Status API는 JobStore를 우선 조회하므로, progress 업데이트는 반드시 JobStore에도 반영되어야 함.

### 2. Async Function Call from Sync Context
동기 콜백에서 비동기 함수 호출 시:
```python
# 방법 1: asyncio.create_task (현재 사용)
loop = asyncio.get_running_loop()
loop.create_task(async_function())

# 방법 2: asyncio.ensure_future
asyncio.ensure_future(async_function())
```

### 3. Rate Limiter and CORS Preflight
Rate limiter는 반드시 OPTIONS preflight 요청을 제외해야 함.
그렇지 않으면 빈번한 폴링에서 CORS 에러로 위장된 429 에러가 발생.

---

## Related Documents

- `DOCS/project-management/action-items.md` - BUG-026, BUG-027 문서화
- `DOCS/.meta/sessions/2026-01-21_bug-020-025-visualization-fixes.md` - 이전 세션
- `backend/middleware/rate_limiter.py` - BUG-026 수정
- `backend/routers/import_.py` - BUG-027 수정
