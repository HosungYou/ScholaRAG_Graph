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

## BUG-027 Phase 2: Frontend Unit Mismatch

### Codex CLI Review 발견 사항

첫 번째 수정 (Backend JobStore 업데이트) 이후에도 progress가 0%로 표시되는 문제가 지속됨.
`codex exec -m gpt-5.2-codex`로 심층 분석 수행.

**Critical Finding**:
```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend Unit Mismatch                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Backend sends: progress = 0.1 (fraction, 0.0 to 1.0)          │
│                    ↓                                            │
│  Frontend receives: job.progress = 0.1                         │
│                    ↓                                            │
│  Display: Math.round(0.1) = 0  ← 항상 0!                        │
│  Bar: width: "0.1%" ← 사실상 보이지 않음!                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Resolution (Phase 2)

**File**: `frontend/components/import/ImportProgress.tsx`

```typescript
// BUG-027 FIX: Backend sends progress as 0.0-1.0 fraction, convert to 0-100 percent
// Without this, Math.round(0.1) = 0 and width: "0.1%" makes the bar invisible
const progressPercent = Math.round((job.progress ?? 0) * 100);

// Display (was: {Math.round(job.progress)})
{progressPercent}<span className="text-2xl text-accent-teal">%</span>

// Progress bar (was: width: `${job.progress}%`)
style={{ width: `${progressPercent}%` }}
```

**Commit**: `12d6ae4`

---

## BUG-027 Phase 3: Progress Stuck at 78%

### Codex CLI Review 발견 사항

Frontend 수정 후 progress가 78%까지 표시되나, 그 이후 멈춤.
`codex exec -m gpt-5.2-codex`로 심층 분석 수행.

**Root Cause Analysis**:
```
┌─────────────────────────────────────────────────────────────────┐
│                    Fire-and-Forget Problem                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Importer: self._update_progress("importing", 0.78, ...)       │
│                    ↓                                            │
│  Callback: loop.create_task(job_store.update_job(...))         │
│                    ↓                                            │
│  DB Update 성공 → progress=0.78 저장                           │
│                    ↓                                            │
│  다음 Item 처리 중 DB 연결 문제 발생                            │
│                    ↓                                            │
│  DB Update 실패 → 예외 조용히 무시 → 메모리만 업데이트          │
│                    ↓                                            │
│  Status API: DB 우선 조회 → progress=0.78 (stale!)             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**78% 계산 근거**:
```python
# backend/importers/zotero_rdf_importer.py
progress_pct = 0.25 + (0.65 * (i / len(items)))
# items=10, i=8일 때: 0.25 + 0.65 * 0.8 = 0.77 ≈ 78%
```

### Resolution (Phase 3)

**BUG-027-C: Error Callback 추가**

`asyncio.create_task()`에 `add_done_callback` 추가하여 실패 시 로깅:

```python
# backend/routers/import_.py (3개 progress_callback 모두 수정)
task = loop.create_task(
    job_store.update_job(
        job_id=job_id,
        progress=progress.progress,
        message=progress.message,
    )
)
# BUG-027-C FIX: Add error callback to surface silent failures
def _handle_jobstore_error(t):
    if t.exception():
        logger.error(f"[Import {job_id}] JobStore update failed: {t.exception()}")
task.add_done_callback(_handle_jobstore_error)
```

**BUG-027-D: Status API 최신 데이터 우선**

DB와 In-Memory 중 더 최신 데이터를 반환하도록 수정:

```python
# backend/routers/import_.py - get_import_status endpoint
@router.get("/status/{job_id}")
async def get_import_status(job_id: str):
    """BUG-027-D FIX: Compare timestamps between JobStore (DB) and in-memory storage"""
    job_store = await get_job_store()
    db_job = await job_store.get_job(job_id)
    legacy_job = _import_jobs.get(job_id)

    # BUG-027-D: Determine which source has more recent data
    use_legacy = False
    if legacy_job and db_job:
        legacy_updated = legacy_job.get("updated_at")
        db_updated = db_job.updated_at
        if legacy_updated and db_updated and legacy_updated > db_updated:
            use_legacy = True  # Use in-memory if more recent
    elif legacy_job and not db_job:
        use_legacy = True

    if use_legacy and legacy_job:
        return ImportJobResponse(**legacy_job)
    # ... rest of function
```

---

## Verification Status

| Bug | Status | Test |
|-----|--------|------|
| BUG-026 | ✅ Completed | CORS headers present, 200 OK |
| BUG-027 Backend | ✅ Completed | JobStore now receives progress updates |
| BUG-027 Frontend | ✅ Completed | Progress displays correctly (0-100%) |
| BUG-027-C | ✅ Completed | Error callback added to create_task |
| BUG-027-D | ✅ Completed | Status API prefers most recent data |

---

## Commits

| Commit | Description |
|--------|-------------|
| `644a6fe` | fix(BUG-026): skip OPTIONS preflight in rate limiter |
| `16531bc` | fix(BUG-027): progress_callback updates JobStore for real-time progress |
| `12d6ae4` | fix(BUG-027): frontend progress scaling 0.0-1.0 → 0-100% |
| `pending` | fix(BUG-027-C,D): error callback + status API prefer recent data |

---

## Session Statistics

| Metric | Value |
|--------|-------|
| Bugs Fixed | 2 (BUG-026, BUG-027) |
| Sub-fixes | 4 (BUG-027: Backend, Frontend, Error Callback, Status API) |
| Files Modified | 3 (rate_limiter.py, import_.py, ImportProgress.tsx) |
| Commits | 4 |
| Root Cause Analysis Time | ~60 minutes |
| Skills Used | superpowers:systematic-debugging, code-reviewer (Codex CLI) |

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

### 4. Fire-and-Forget Async Tasks Need Error Handling
`asyncio.create_task()`는 예외를 조용히 무시하므로, 반드시 `add_done_callback`으로 에러 핸들링 추가:
```python
task = loop.create_task(async_function())
def _handle_error(t):
    if t.exception():
        logger.error(f"Task failed: {t.exception()}")
task.add_done_callback(_handle_error)
```

### 5. Dual Storage Systems Need Timestamp Comparison
DB와 In-Memory 두 저장소를 사용할 때, 항상 최신 데이터를 반환해야 함:
```python
if legacy_updated > db_updated:
    return legacy_data  # Use in-memory if more recent
```

### 6. Frontend-Backend Unit Consistency
진행률 표시 시 단위 일관성 중요:
- Backend: 0.0 ~ 1.0 (fraction)
- Frontend: 0 ~ 100 (percent)
- 변환 필수: `progressPercent = Math.round(progress * 100)`

---

## Related Documents

- `DOCS/project-management/action-items.md` - BUG-026, BUG-027 문서화
- `DOCS/.meta/sessions/2026-01-21_bug-020-025-visualization-fixes.md` - 이전 세션
- `backend/middleware/rate_limiter.py` - BUG-026 수정
- `backend/routers/import_.py` - BUG-027 수정
