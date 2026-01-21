# ScholaRAG_Graph Action Items

> 이 문서는 코드 리뷰, 기능 구현, 버그 수정 등에서 발견된 액션 아이템을 추적합니다.
>
> **마지막 업데이트**: 2026-01-21
> **관리자**: Claude Code

---

## 📊 Status Overview

| Priority | Total | Completed | In Progress | Pending |
|----------|-------|-----------|-------------|---------|
| 🔴 High | 9 | 9 | 0 | 0 |
| 🟡 Medium | 5 | 5 | 0 | 0 |
| 🟢 Low | 3 | 3 | 0 | 0 |
| **Total** | **17** | **17** | **0** | **0** |

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

### PERF-009: Render 512MB 메모리 제한 최적화
- **Source**: Render Memory Exceeded Alert 2026-01-21
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/llm/cohere_embeddings.py` - batch_size 96 → 20
  - `backend/llm/openai_embeddings.py` - batch_size 50 → 20
  - `backend/graph/embedding/embedding_pipeline.py` - batch_size 50 → 20
  - `backend/graph/graph_store.py` - batch_size 50 → 20
  - `backend/config.py` - llm_cache_max_size 1000 → 100
- **Description**: Import 중 Render 서버가 512MB 메모리 제한 초과로 재시작되어 import 중단
- **Root Cause**:
  - Cohere embedding batch_size = 96 (너무 큼)
  - LLM 캐시 max_size = 1000 (메모리 과다 사용)
  - 동시 처리 시 메모리 사용량 급증
- **Solution Applied**:
  - [x] 모든 embedding batch_size를 20으로 감소 (메모리 ~150MB 절약)
  - [x] LLM 캐시 max_size를 100으로 감소 (메모리 ~50MB 절약)
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Notes**: 총 ~150-200MB 메모리 절약 예상, 문제 지속 시 인스턴스 업그레이드 검토 ($15/월 for 1GB)

---

### UI-001: Import Interrupted Resume 버튼 추가
- **Source**: BUG-028 관련 UX 개선
- **Status**: ✅ Completed
- **Assignee**: Frontend Team
- **Files**:
  - `frontend/components/import/ImportProgress.tsx` - Resume 버튼 구현
- **Description**: Import가 서버 재시작으로 중단되었을 때 Resume 버튼이 없어 사용자가 재개할 수 없음
- **Solution Applied**:
  - [x] `handleResumeImport()` 함수 구현 - `api.resumeImport(jobId)` 호출
  - [x] "Import 재개" 버튼을 primary action으로 추가
  - [x] 로딩 상태 및 에러 처리 추가
  - [x] 버튼 레이아웃 재구성: Resume (primary) → Re-upload → Partial results
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Notes**: Vercel 재배포 필요

---

### BUG-034: Chunk Embedding pgvector 형식 변환 누락
- **Source**: Render 로그 분석 2026-01-21 (import 실패)
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/graph/embedding/embedding_pipeline.py` - `create_chunk_embeddings` 메서드 수정
- **Description**: Cohere 임베딩 생성 후 semantic_chunks 테이블 저장 시 "expected str, got list" 에러 발생
- **Root Cause**: `create_chunk_embeddings` 메서드에서 embedding list를 pgvector 문자열 형식으로 변환하지 않음
  - `create_embeddings` (엔티티)에서는 `embedding_str = "[" + ",".join(map(str, embedding)) + "]"` 사용
  - `create_chunk_embeddings` (청크)에서는 변환 누락
- **Solution Applied**:
  - [x] `create_chunk_embeddings`에 문자열 변환 로직 추가
  - [x] batch_data 생성 시 `embedding_str` 사용
  - [x] fallback 개별 업데이트에서도 `embedding_str` 사용
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Verified By**: Claude Code
- **Notes**: Render 재배포 필요

---

### BUG-033: semantic_chunks 테이블 누락 및 Groq Rate Limit
- **Source**: Render 로그 분석 2026-01-21 (import 실패)
- **Status**: ✅ Completed
- **Assignee**: Database Team / Infrastructure
- **Files**:
  - `database/migrations/011_semantic_chunks.sql` - Supabase에서 수동 실행
- **Description**: Import 시 세 가지 에러 발생:
  1. `relation "semantic_chunks" does not exist` - 마이그레이션 미적용
  2. `Groq rate limit reached (429)` - 무료 티어 한도 초과 (500K tokens/day)
  3. `LLM extraction failed after 3 retries` - fallback 없이 완전 실패
- **Root Cause**:
  - 011_semantic_chunks.sql 마이그레이션이 Supabase에 적용되지 않음
  - Groq 무료 티어 일일 토큰 한도 500,000 초과
- **Solution Applied**:
  - [x] Supabase SQL Editor에서 011_semantic_chunks.sql 마이그레이션 실행
  - [x] Groq Dev Tier 업그레이드 (500K → 7M tokens/day)
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Verified By**: User
- **Notes**: Dev Tier 비용 $2/월 또는 pay-as-you-go

---

### INFRA-007: Groq Dev Tier 업그레이드
- **Source**: BUG-033 해결 과정
- **Status**: ✅ Completed
- **Assignee**: Infrastructure
- **Description**: Groq API 무료 티어에서 Dev Tier로 업그레이드하여 일일 토큰 한도 증가
- **Details**:
  - Before: Free Tier (500K tokens/day)
  - After: Dev Tier (7M tokens/day)
  - Console: https://console.groq.com/settings/billing
- **Created**: 2026-01-21
- **Completed**: 2026-01-21

---

### BUG-029: system.py DB 쿼리 - 존재하지 않는 컬럼 수정
- **Source**: Render 로그 분석 2026-01-21
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `database/migrations/011_add_import_tracking_to_projects.sql` - 새 마이그레이션 추가
- **Description**: `GET /api/system/status` 엔드포인트가 projects 테이블에 존재하지 않는 `import_source`, `last_synced_at` 컬럼을 쿼리하여 에러 발생
- **Root Cause**: 스키마 설계 불일치 - system.py가 존재하지 않는 컬럼을 가정하고 작성됨
- **Acceptance Criteria**:
  - [x] projects 테이블에 import_source, last_synced_at 컬럼 추가 마이그레이션 생성
  - [x] 기존 프로젝트 데이터 마이그레이션 (zotero_sync_state 기반)
  - [x] 인덱스 생성
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Verified By**: Claude Code
- **Notes**: ✅ Supabase에서 마이그레이션 실행 완료 (2026-01-21)

---

### BUG-031: entity_extractor.py JSON 파싱 실패 개선
- **Source**: 코드 분석 2026-01-21
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/graph/entity_extractor.py` - `_extract_json_from_text()` 메서드 추가
- **Description**: LLM 응답에서 JSON 추출 시 단순 regex만 사용하여 다양한 형식의 응답 처리 실패
- **Root Cause**: LLM이 코드 블록, 추가 텍스트 등 다양한 형식으로 JSON을 반환하는데 단일 패턴만 사용
- **Acceptance Criteria**:
  - [x] 다중 전략 JSON 추출 메서드 구현 (직접 파싱, 코드 블록, 중괄호 매칭)
  - [x] 기존 `_parse_llm_response` 메서드에 통합
  - [x] 에러 로깅 개선
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Verified By**: Claude Code
- **Notes**: 4단계 폴백 전략 구현 완료

---

### BUG-032: Groq API Rate Limiting 처리 부재
- **Source**: Render 로그 분석 2026-01-21 (429 Too Many Requests)
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/llm/groq_provider.py` - `AsyncRateLimiter` 클래스 및 retry 로직 추가
- **Description**: Groq API 호출 시 429 에러 발생해도 retry 없이 즉시 실패
- **Root Cause**: 다른 integration들(Zotero, Semantic Scholar, OpenAlex)과 달리 LLM provider에 retry 로직 미구현
- **Acceptance Criteria**:
  - [x] `AsyncRateLimiter` 클래스 구현 (token bucket 방식)
  - [x] `_execute_with_retry` 메서드 구현
  - [x] 429 에러 시 Retry-After 헤더 존중
  - [x] Exponential backoff 구현
  - [x] generate, generate_json 메서드에 적용
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Verified By**: Claude Code
- **Notes**: 기본 20 req/min rate limit, 최대 3회 retry

---

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
