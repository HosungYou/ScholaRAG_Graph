# ScholaRAG_Graph Action Items

> 이 문서는 코드 리뷰, 기능 구현, 버그 수정 등에서 발견된 액션 아이템을 추적합니다.
>
> **마지막 업데이트**: 2026-01-15
> **관리자**: Claude Code

---

## 📊 Status Overview

| Priority | Total | Completed | In Progress | Pending |
|----------|-------|-----------|-------------|---------|
| 🔴 High | 3 | 3 | 0 | 0 |
| 🟡 Medium | 3 | 3 | 0 | 0 |
| 🟢 Low | 3 | 3 | 0 | 0 |
| **Total** | **9** | **9** | **0** | **0** |

---

## 🔴 High Priority (Immediate Action Required)

*모든 High Priority 항목이 완료되어 Archive 섹션으로 이동되었습니다.*

---

## 🟡 Medium Priority (Short-term)

*모든 Medium Priority 항목이 완료되어 Archive 섹션으로 이동되었습니다.*

---

## 🟢 Low Priority (Long-term)

*모든 Low Priority 항목이 완료되어 Archive 섹션으로 이동되었습니다.*

---

## 📝 Completed Items Archive

### SEC-001: Graph/Chat 엔드포인트 인증 강제
- **Source**: Code Review 2026-01-15
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/graph.py` - `require_auth_if_configured` dependency 추가
  - `backend/routers/chat.py` - `require_auth_if_configured` dependency 추가
- **Description**: 모든 graph/chat 엔드포인트에 인증 및 프로젝트 접근 검사를 강제
- **Acceptance Criteria**:
  - [x] 모든 graph 엔드포인트에 `require_auth_if_configured` 추가
  - [x] 프로젝트 소유권/협업자 접근 검증 로직 추가
  - [x] 테스트 통과 확인
- **Created**: 2026-01-15
- **Completed**: 2026-01-15
- **Verified By**: Claude Code
- **Notes**: `require_auth_if_configured` dependency를 통해 구현됨

---

### SEC-002: AuthMiddleware 중앙화
- **Source**: Code Review 2026-01-15
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/main.py:117` - AuthMiddleware 적용
- **Description**: AuthMiddleware를 미들웨어로 설치
- **Acceptance Criteria**:
  - [x] 중앙 집중식 인증 미들웨어 구현
  - [x] main.py에서 미들웨어로 등록
- **Created**: 2026-01-15
- **Completed**: 2026-01-15
- **Verified By**: Claude Code
- **Notes**: `main.py:117`에서 AuthMiddleware가 app에 추가됨

---

### SEC-003: Supabase RLS 정책 활성화
- **Source**: Code Review 2026-01-15
- **Status**: ✅ Completed
- **Assignee**: Database Team
- **Files**:
  - `database/migrations/005_user_profiles.sql` - RLS 정책 활성화됨
- **Description**: Supabase RLS 정책 활성화
- **Acceptance Criteria**:
  - [x] RLS 정책 활성화
  - [x] `ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;`
  - [x] `ALTER TABLE projects ENABLE ROW LEVEL SECURITY;`
  - [x] 적절한 정책 생성 (`Users can view own profile` 등)
- **Created**: 2026-01-15
- **Completed**: 2026-01-15
- **Verified By**: Claude Code
- **Notes**: 마이그레이션 파일에서 RLS가 활성화되어 있음 (주석 처리되지 않음)

---

### FUNC-001: Orchestrator DB/GraphStore 연결
- **Source**: Code Review 2026-01-15
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/chat.py:445,454` - DB 및 GraphStore 전달
- **Description**: `AgentOrchestrator`를 `db`와 `GraphStore`로 초기화
- **Acceptance Criteria**:
  - [x] Orchestrator 초기화 시 DB 연결 전달
  - [x] GraphStore 인스턴스 전달
- **Created**: 2026-01-15
- **Completed**: 2026-01-15
- **Verified By**: Claude Code
- **Notes**: `chat.py`에서 `graph_store`와 `db_connection` 파라미터로 전달됨

---

### BUG-001: datetime import 누락 수정
- **Source**: Code Review 2026-01-15
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/teams.py:8` - datetime import 추가됨
- **Description**: `datetime` import 누락 수정
- **Acceptance Criteria**:
  - [x] `from datetime import datetime` 추가
- **Created**: 2026-01-15
- **Completed**: 2026-01-15
- **Verified By**: Claude Code
- **Notes**: `teams.py:8`에 import 문 확인됨

---

### FUNC-002: Frontend API Authorization 헤더
- **Source**: Code Review 2026-01-15
- **Status**: ✅ Completed
- **Assignee**: Frontend Team
- **Files**:
  - `frontend/lib/api.ts` - Bearer token 헤더 추가됨
- **Description**: API 클라이언트에 Supabase 액세스 토큰을 Authorization 헤더로 첨부
- **Acceptance Criteria**:
  - [x] Supabase 세션에서 토큰 추출
  - [x] API 요청에 Bearer 토큰 첨부
- **Created**: 2026-01-15
- **Completed**: 2026-01-15
- **Verified By**: Claude Code
- **Notes**: `api.ts`에서 Authorization: Bearer 헤더 설정 확인됨

---

### PERF-001: LLM 결과 캐싱
- **Source**: Code Review 2026-01-15
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/llm/cached_provider.py` - CachedLLMProvider 구현됨
- **Description**: LLM 결과에 캐싱 추가
- **Acceptance Criteria**:
  - [x] 캐싱 Provider 구현
  - [x] TTL 기반 캐시 무효화
- **Created**: 2026-01-15
- **Completed**: 2026-01-15
- **Verified By**: Claude Code
- **Notes**: `CachedLLMProvider` 클래스로 인메모리 캐싱 구현됨

---

### PERF-002: Redis Rate Limiting
- **Source**: Code Review 2026-01-15
- **Status**: ✅ Completed
- **Assignee**: DevOps Team
- **Files**:
  - `backend/middleware/rate_limiter.py` - Redis 기반 Rate Limiter 구현됨
- **Description**: Redis 기반 Rate Limiting
- **Acceptance Criteria**:
  - [x] Redis 기반 Rate Limiter 구현
  - [x] 환경별 설정 지원
- **Created**: 2026-01-15
- **Completed**: 2026-01-15
- **Verified By**: Claude Code
- **Notes**: Redis 연결 시 Redis 사용, 없으면 인메모리 fallback

---

### PERF-003: N+1 쿼리 최적화
- **Source**: Code Review 2026-01-15
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/chat.py` - `json_agg` 사용한 쿼리 최적화
- **Description**: 프로젝트 통계 및 채팅 기록에 쿼리 배칭 추가
- **Acceptance Criteria**:
  - [x] N+1 쿼리 패턴 수정
  - [x] `json_agg`를 사용한 집계 쿼리로 최적화
- **Created**: 2026-01-15
- **Completed**: 2026-01-15
- **Verified By**: Claude Code
- **Notes**: `chat.py`에서 `json_agg`를 사용한 효율적인 쿼리 확인됨

---

## 📋 How to Use This Document

### Adding New Items
```markdown
### [TYPE]-[NUMBER]: 제목
- **Source**: [리뷰/기능/버그 출처]
- **Status**: ⬜ Pending | 🔄 In Progress | ✅ Completed
- **Assignee**: [담당자/팀]
- **Files**: [관련 파일 목록]
- **Description**: [상세 설명]
- **Acceptance Criteria**:
  - [ ] 조건 1
  - [ ] 조건 2
- **Created**: YYYY-MM-DD
- **Completed**: -
```

### Status Legend
- ⬜ **Pending**: 아직 시작되지 않음
- 🔄 **In Progress**: 진행 중
- ✅ **Completed**: 완료됨
- ❌ **Won't Fix**: 수정하지 않기로 결정

### Type Prefixes
- `SEC`: Security (보안)
- `BUG`: Bug Fix (버그 수정)
- `FUNC`: Functionality (기능)
- `PERF`: Performance (성능)
- `DOC`: Documentation (문서)
- `TEST`: Testing (테스트)

---

*이 문서는 Claude Code에 의해 자동으로 관리됩니다.*
