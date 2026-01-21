# Session Log: Recurring Error Root Cause Analysis

> **Session ID**: 2026-01-21-rca-recurring-errors
> **Date**: 2026-01-21
> **Agent**: Claude Code (Opus 4.5)
> **Type**: Root Cause Analysis / Debugging
> **Duration**: ~30 minutes

---

## Context

### User Request
사용자가 ScholaRAG_Graph 프로젝트에서 반복적으로 발생하는 에러(CORS, 500, Mixed Content)의 근본 원인을 분석 요청.

### Related Decisions
- INFRA-004: Backend migrated from Python service to Docker service (2026-01-20)
- Multiple CORS fix commits in recent history

---

## Summary

### 문제 증상 (스크린샷에서 관찰)
| 에러 유형 | 메시지 |
|----------|--------|
| CORS | `No 'Access-Control-Allow-Origin' header is present` |
| 500 Error | `/api/system/status` 반복 실패 |
| Mixed Content | HTTPS 페이지에서 HTTP 리소스 요청 |

### 근본 원인 분석 결과

#### 🔴 핵심 버그: `system.py:95` - 존재하지 않는 메서드 호출

```python
# backend/routers/system.py:95
database = await db.get_connection()  # ❌ AttributeError!
```

**Render 로그에서 확인된 실제 에러:**
```
AttributeError: 'Database' object has no attribute 'get_connection'
File "/app/routers/system.py", line 92, in get_system_status
    database = await db.get_connection()
```

**Database 클래스 실제 인터페이스 (`database.py`):**
```python
class Database:
    async def acquire(self):  # ✅ Context manager
    async def fetch(self, query, *args):  # ✅ Direct query
    async def fetchval(self, query, *args):  # ✅ Direct query
    async def fetchrow(self, query, *args):  # ✅ Direct query
    # get_connection() 메서드 없음!
```

#### 🟡 Configuration Drift 패턴

최근 커밋 히스토리에서 동일 유형 문제 반복 수정:
| 커밋 | 수정 내용 |
|------|----------|
| `1ca4f4b` | CORS origins 추가 |
| `ac11672` | Vercel Preview URL regex |
| `882f14a` | Rate limiter CORS 헤더 |
| `22217b5` | HTTPS 강제 변환 |

**원인**: 코드의 기본값과 Render 환경 변수 간 불일치

#### 🟡 500 에러 연쇄 반응

1. `/api/system/status` 호출 → `get_connection()` AttributeError → 500
2. 500 응답에 CORS 헤더 누락 → 브라우저에서 CORS 에러로 표시
3. 사용자는 CORS 문제로 인식 → CORS 수정 시도 → 실제 버그 미해결

---

## Action Items

### 🔴 BUG-015: system.py get_connection() AttributeError 수정
- **Priority**: High (즉시)
- **Status**: Pending
- **Files**: `backend/routers/system.py:95`
- **Description**: 존재하지 않는 `db.get_connection()` 메서드 호출로 500 에러 발생
- **Fix Required**:
```python
# Before (버그)
database = await db.get_connection()
result = await database.fetchval(...)

# After (수정)
result = await db.fetchval(...)
# 또는
async with db.acquire() as conn:
    result = await conn.fetchval(...)
```

### 🟡 INFRA-005: Infrastructure as Code 도입
- **Priority**: Medium (단기)
- **Status**: Pending
- **Description**: 환경 변수를 `render.yaml` / `vercel.json`으로 버전 관리하여 Configuration Drift 방지

### 🟢 DOC-003: 에러 디버깅 가이드 작성
- **Priority**: Low
- **Status**: Pending
- **Description**: CORS 에러가 실제로는 백엔드 500 에러를 마스킹할 수 있다는 점 문서화

---

## Render 서비스 상태 확인

### 서비스 정보
| 항목 | 값 |
|------|-----|
| Service Name | `scholarag-graph-docker` |
| Service ID | `srv-d5nen956ubrc73aqko8g` |
| URL | `https://scholarag-graph-docker.onrender.com` |
| Plan | Starter |
| Region | Oregon |
| Runtime | Docker |
| Status | `not_suspended` |

### 최근 로그 분석
```
2026-01-21T02:02:50 - GET /api/system/status?project_id=... 500 Internal Server Error
2026-01-21T02:02:50 - ERROR: Exception in ASGI application
2026-01-21T02:02:50 - AttributeError: 'Database' object has no attribute 'get_connection'
```

**결론**: 500 에러는 CORS 설정 문제가 아니라 **코드 버그**임

---

## Session Statistics

| Metric | Value |
|--------|-------|
| Files Analyzed | 8 |
| Commits Reviewed | 15+ |
| Bugs Found | 1 (Critical) |
| Action Items Created | 3 |
| Root Cause Identified | Yes |

---

## Recommendations

1. **즉시**: `BUG-015` 수정 후 재배포
2. **단기**: CI/CD에 린트/타입 체크 추가하여 유사 버그 사전 방지
3. **장기**: Infrastructure as Code 도입으로 Configuration Drift 방지

---

## Related Documents
- `DOCS/project-management/action-items.md`
- `CLAUDE.md` - Deployment section
- `backend/database.py` - Database class interface
- `backend/routers/system.py` - Bug location
