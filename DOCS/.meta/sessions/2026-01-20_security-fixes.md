# Session Log: Security Fixes from Code Review

## Session Metadata
- **Session ID**: `2026-01-20_security-fixes`
- **Date**: 2026-01-20
- **Duration**: ~45 minutes
- **Agent**: Claude Code (Opus 4.5)
- **Type**: Security Fix / Bug Fix
- **Source**: Codex Code Review (from previous session)

---

## Context

### Trigger
사용자가 Codex 코드 리뷰에서 식별된 보안 문제들을 수정하고 문서화할 것을 요청함.

### Related Sessions
- `2026-01-20_render-docker-deployment-troubleshooting.md` - Docker 배포 및 코드 리뷰 세션

### Related Decisions
- N/A (기존 보안 패턴 강화)

---

## Summary

Codex 코드 리뷰에서 발견된 5개의 보안/버그 이슈와 1개의 인프라 항목을 모두 수정 완료:

| ID | Issue | Status |
|----|-------|--------|
| SEC-007 | CORS 와일드카드 보안 위험 | ✅ Fixed |
| SEC-008 | DB 불가 시 인증 우회 | ✅ Fixed |
| SEC-009 | SQL Injection 취약점 | ✅ Fixed |
| SEC-010 | Import Path Traversal | ✅ Fixed |
| BUG-012 | Chat 메시지 트랜잭션 누락 | ✅ Fixed |
| INFRA-003 | Docker 캐시 활성화 | ✅ Auto-enabled |

---

## Changes Made

### SEC-007: CORS Security Hardening
**File**: `backend/main.py:116-136`

**Before**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",  # DANGEROUS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**After**:
```python
# SECURITY: Use explicit origins only. Wildcard regex with credentials is dangerous.
_cors_origins = settings.cors_origins_list or []
if settings.environment == "development":
    _cors_origins = list(set(_cors_origins + [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    # REMOVED: allow_origin_regex - wildcard regex with credentials is a security risk
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)
```

**Impact**: Cross-origin 공격 벡터 제거, Vercel 프리뷰 배포는 `CORS_ORIGINS` 환경변수로 명시적 추가 필요

---

### SEC-008: DB Unavailable Access Control
**File**: `backend/routers/chat.py:81`

**Change**: Production/staging 환경에서 DB 연결 실패 시 503 에러 반환, 개발 모드에서만 memory-only 허용

```python
if not await _check_db_available():
    # SECURITY: In production/staging, deny access if DB is unavailable
    if settings.environment in ("production", "staging"):
        logger.warning(f"Chat access denied: database unavailable in {settings.environment}")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again later."
        )
    logger.warning("Database unavailable - allowing memory-only mode (development only)")
    return
```

**Impact**: DB 장애 시 인증 우회 취약점 제거

---

### SEC-009: SQL Injection Prevention
**File**: `backend/graph/graph_store.py:1381`

**Change**: `top_k` 값을 f-string 대신 파라미터화된 쿼리로 변경, 입력 검증 추가

```python
# SECURITY: Validate and sanitize top_k to prevent injection
top_k = max(1, min(int(top_k), 100))

# Add LIMIT as parameterized query (last parameter)
limit_param_idx = len(params) + 1
sql += f"\nORDER BY similarity DESC\nLIMIT ${limit_param_idx}"
params.append(top_k)
```

**Impact**: SQL Injection 공격 벡터 제거, 최대 100개 결과로 제한

---

### SEC-010: Import Path Traversal Protection
**File**: `backend/routers/import_.py:139`

**Change**: 개발 모드에서도 시스템 디렉토리 차단

```python
blocked_prefixes = [
    "/etc", "/var", "/usr", "/bin", "/sbin", "/lib", "/boot",
    "/root", "/sys", "/proc", "/dev", "/run", "/snap",
    "/System", "/Library", "/private",  # macOS system directories
    "C:\\Windows", "C:\\Program Files",  # Windows system directories
]
resolved_str = str(resolved_path)
for blocked in blocked_prefixes:
    if resolved_str.startswith(blocked):
        logger.warning(f"Blocked access to system directory: {resolved_str}")
        raise HTTPException(
            status_code=403,
            detail="Access denied: Cannot import from system directories"
        )
```

**Impact**: 시스템 파일 접근을 통한 정보 노출 방지

---

### BUG-012: Chat Message Transaction
**File**: `backend/routers/chat.py:160`

**Change**: 채팅 메시지 삽입을 트랜잭션으로 래핑

```python
async with db.transaction() as conn:
    # Insert user message
    await conn.execute(...)
    # Insert assistant message
    await conn.execute(...)
    # Update conversation timestamp
    await conn.execute(...)
```

**Impact**: 부분 삽입 실패 시 데이터 일관성 보장

---

### INFRA-003: Render Docker Cache
**Status**: Auto-enabled by Render

Render 문서 확인 결과: "Render caches all intermediate build layers" - 별도 설정 불필요, 자동 활성화됨.

---

## Action Items

### Completed This Session
- [x] SEC-007: CORS 보안 강화
- [x] SEC-008: DB 불가 시 chat 액세스 제어
- [x] SEC-009: SQL Injection 방어
- [x] SEC-010: Import Path Validation
- [x] BUG-012: Chat 메시지 트랜잭션
- [x] INFRA-003: Docker 캐시 확인

### Manual Action Required
- [ ] **INFRA-004**: 기존 Python 서비스 삭제 (Render Dashboard에서 수동 삭제 필요)
  - Service ID: `srv-d5n4aesoud1c739ot8a0`
  - Dashboard URL: https://dashboard.render.com/
  - Docker 서비스 안정성 확인 후 삭제 권장

---

## Verification

모든 코드 변경은 IDE에서 구문 검증 완료. 런타임 테스트는 다음 배포 후 Render 로그에서 확인 필요.

---

## Session Statistics

| Metric | Value |
|--------|-------|
| Files Modified | 4 |
| Security Issues Fixed | 4 |
| Bug Fixes | 1 |
| Infrastructure Items | 1 |
| Lines Changed | ~80 |
| Documentation Updated | 2 files |

---

## Files Modified

1. `backend/main.py` - CORS 보안 설정
2. `backend/routers/chat.py` - DB 액세스 제어 + 트랜잭션
3. `backend/graph/graph_store.py` - SQL Injection 방어
4. `backend/routers/import_.py` - Path Validation
5. `DOCS/project-management/action-items.md` - 상태 업데이트
6. `DOCS/.meta/sessions/2026-01-20_security-fixes.md` - 본 세션 로그
