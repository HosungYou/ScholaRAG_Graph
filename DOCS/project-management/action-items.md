# ScholaRAG_Graph Action Items

> 이 문서는 코드 리뷰, 기능 구현, 버그 수정 등에서 발견된 액션 아이템을 추적합니다.
>
> **마지막 업데이트**: 2026-01-20 (Security Fixes from Code Review)
> **관리자**: Claude Code

---

## 📊 Status Overview

| Priority | Total | Completed | In Progress | Pending |
|----------|-------|-----------|-------------|---------|
| 🔴 High | 10 | 10 | 0 | 0 |
| 🟡 Medium | 11 | 9 | 0 | 2 |
| 🟢 Low | 5 | 2 | 0 | 3 |
| **Total** | **26** | **21** | **0** | **5** |

---

## 🔴 High Priority (Immediate Action Required)

*현재 High Priority 항목 없음 - 모두 완료됨*

---

## 🟡 Medium Priority (Short-term)

### PERF-006: 청크 임베딩 배치 업데이트
- **Source**: Code Review (Codex) 2026-01-20
- **Status**: ⬜ Pending
- **Assignee**: Backend Team
- **Files**:
  - `backend/graph/graph_store.py:1311` - 임베딩 업데이트 로직
- **Description**: 청크 임베딩이 개별 쿼리로 실행되어 대량 처리 시 성능 저하
- **Acceptance Criteria**:
  - [ ] `executemany` 또는 배치 INSERT 사용
  - [ ] 대량 처리 시 성능 테스트
- **Created**: 2026-01-20
- **Related**: Session `2026-01-20_render-docker-deployment-troubleshooting.md`

---

### PERF-004: 503 에러 모니터링
- **Source**: Render Starter Optimization 2026-01-19
- **Status**: ⬜ Pending
- **Assignee**: DevOps Team
- **Description**: 배포 후 503 에러 발생률 모니터링
- **Acceptance Criteria**:
  - [ ] Render 로그에서 503 에러 빈도 확인
  - [ ] 에러 발생 시 알림 설정
- **Created**: 2026-01-19
- **Related**: Session `2026-01-19_render-starter-optimization.md`

---

## 🟢 Low Priority (Long-term)

### INFRA-004: 기존 Python 서비스 삭제
- **Source**: Render Docker Deployment 2026-01-20
- **Status**: ⬜ Pending
- **Assignee**: DevOps Team
- **Description**: Docker 서비스로 마이그레이션 완료 후 기존 Python 서비스 삭제
- **Service ID**: `srv-d5n4aesoud1c739ot8a0`
- **Acceptance Criteria**:
  - [ ] Docker 서비스 안정성 확인 (1주일)
  - [ ] 기존 Python 서비스 삭제
- **Created**: 2026-01-20
- **Related**: Session `2026-01-20_render-docker-deployment-troubleshooting.md`

---

### DOC-001: 배포 가이드에 Starter 플랜 권장사항 추가
- **Source**: Render Starter Optimization 2026-01-19
- **Status**: ⬜ Pending
- **Assignee**: Docs Team
- **Description**: Render Starter 플랜 최적화 설정 문서화
- **Acceptance Criteria**:
  - [ ] 연결 풀 설정 권장값 문서화
  - [ ] 프론트엔드 재시도 로직 설명 추가
- **Created**: 2026-01-19

---

### FUNC-003: /api/system/status 엔드포인트 구현
- **Source**: Render Starter Optimization 2026-01-19
- **Status**: ⬜ Pending
- **Assignee**: Backend Team
- **Description**: StatusBar 컴포넌트용 시스템 상태 API 구현
- **Acceptance Criteria**:
  - [ ] LLM 연결 상태 반환
  - [ ] 벡터 인덱싱 상태 반환
  - [ ] 데이터 소스 정보 반환
- **Created**: 2026-01-19

---

## 📝 Completed Items Archive

### SEC-007: CORS 보안 강화
- **Source**: Code Review (Codex) 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/main.py:116-136` - CORS 설정
- **Description**: `*.vercel.app` 와일드카드 + credentials 허용은 보안 위험
- **Risk**: Cross-origin 공격 가능성
- **Acceptance Criteria**:
  - [x] 명시적 origin 목록으로 변경
  - [x] 프로덕션 환경에서 와일드카드 제거
  - [x] 개발 모드에서만 localhost 허용
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Notes**: `allow_origin_regex` 제거, 명시적 origin 목록만 사용, 메서드/헤더 제한
- **Related**: Session `2026-01-20_security-fixes.md`

---

### SEC-008: DB 불가 시 Chat 액세스 비활성화
- **Source**: Code Review (Codex) 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/chat.py:81` - DB 연결 검사 로직
- **Description**: DB 연결 실패 시 인증 우회 가능 취약점
- **Risk**: 무단 채팅 접근
- **Acceptance Criteria**:
  - [x] DB 불가 시 chat 엔드포인트 비활성화 (production/staging)
  - [x] 적절한 에러 응답 반환 (503 Service Unavailable)
  - [x] 개발 모드에서만 memory-only 허용
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Notes**: 환경별 분기 처리로 프로덕션 보안 강화
- **Related**: Session `2026-01-20_security-fixes.md`

---

### SEC-009: SQL Injection 방어 추가
- **Source**: Code Review (Codex) 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/graph/graph_store.py:1381` - search_chunks 함수
- **Description**: 사용자 입력 검증 부족으로 SQL injection 위험
- **Acceptance Criteria**:
  - [x] 파라미터화된 쿼리 사용 (LIMIT 파라미터화)
  - [x] 입력 검증 로직 추가 (top_k: 1-100 범위 제한)
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Notes**: `top_k` f-string → 파라미터화 쿼리, 최대값 100 제한
- **Related**: Session `2026-01-20_security-fixes.md`

---

### SEC-010: Import Path Validation 강화
- **Source**: Code Review (Codex) 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/import_.py:139` - 경로 검증 로직
- **Description**: `ALLOWED_IMPORT_ROOTS` 비어있을 때 모든 경로 허용됨
- **Acceptance Criteria**:
  - [x] 시스템 디렉토리 차단 (개발 모드 포함)
  - [x] Path traversal 공격 방어 추가
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Notes**: `/etc`, `/var`, `/usr` 등 시스템 경로 차단, macOS/Windows 경로 포함
- **Related**: Session `2026-01-20_security-fixes.md`

---

### BUG-012: 채팅 메시지 트랜잭션 적용
- **Source**: Code Review (Codex) 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/chat.py:160` - 메시지 삽입 로직
- **Description**: 채팅 메시지 삽입이 트랜잭션 없이 실행됨
- **Acceptance Criteria**:
  - [x] 트랜잭션으로 메시지 삽입 래핑
  - [x] 실패 시 롤백 처리
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Notes**: `db.transaction()` 컨텍스트 매니저로 래핑
- **Related**: Session `2026-01-20_security-fixes.md`

---

### INFRA-003: Render Docker 캐시 활성화
- **Source**: Render Docker Deployment 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: DevOps Team
- **Description**: Docker 빌드 캐시 활성화로 빌드 시간 단축
- **Acceptance Criteria**:
  - [x] Render는 자동으로 Docker 빌드 캐시 활성화
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Notes**: Render 문서 확인: "Render caches all intermediate build layers" - 별도 설정 불필요
- **Related**: Session `2026-01-20_security-fixes.md`

---

### BUG-011: DATABASE_URL 특수문자 연결 실패
- **Source**: Render Docker Deployment 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: DevOps Team
- **Description**: Supabase 비밀번호의 특수문자(`!!!!`)로 인한 URL 인코딩 문제
- **Error**: `InvalidPasswordError: password authentication failed`
- **Acceptance Criteria**:
  - [x] Supabase 비밀번호 변경 (특수문자 제거)
  - [x] DATABASE_URL 환경변수 업데이트
  - [x] Health endpoint에서 DB 연결 확인
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Notes**: 비밀번호를 `ScholaRAG2026`으로 변경하여 해결
- **Related**: Session `2026-01-20_render-docker-deployment-troubleshooting.md`

---

### BUG-010: DB 연결 에러 로깅 개선
- **Source**: Render Docker Deployment 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/database.py` - 예외 로깅 상세화
- **Description**: DB 연결 실패 시 구체적인 에러 정보 로깅
- **Acceptance Criteria**:
  - [x] 예외 타입과 메시지 로깅 추가
  - [x] `{type(e).__name__}: {e}` 형식으로 출력
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Commit**: `866b23c fix(docker): optimize build with split requirements and improved error logging`
- **Related**: Session `2026-01-20_render-docker-deployment-troubleshooting.md`

---

### PERF-007: Docker 빌드 최적화 (Requirements 분리)
- **Source**: Render Docker Deployment 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: DevOps Team
- **Files**:
  - `Dockerfile` - requirements 분리 로직 추가
  - `backend/requirements-base.txt` - 경량 의존성 (신규)
  - `backend/requirements-specter.txt` - SPECTER2 의존성 (신규)
- **Description**: PyTorch/SPECTER2를 선택적으로 분리하여 이미지 크기 ~200MB 감소
- **Acceptance Criteria**:
  - [x] requirements-base.txt 생성 (SPECTER2 제외)
  - [x] requirements-specter.txt 생성 (선택적)
  - [x] Dockerfile에 ENABLE_SPECTER2 빌드 인자 추가
  - [x] 커밋 및 푸시
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Commit**: `866b23c fix(docker): optimize build with split requirements and improved error logging`
- **Notes**: Pipeline minutes 소진으로 배포 대기 중. 다음 달 리셋 시 자동 적용 예정.
- **Related**: Session `2026-01-20_render-docker-deployment-troubleshooting.md`

---

### BUG-005: pgbouncer prepared statement 충돌 수정
- **Source**: Production Error 2026-01-19
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/database.py` - `statement_cache_size=0` 추가
- **Description**: Supabase pgbouncer (transaction mode)와 asyncpg prepared statement 충돌 해결
- **Error**: `DuplicatePreparedStatementError: prepared statement "__asyncpg_stmt_16__" already exists`
- **Acceptance Criteria**:
  - [x] `statement_cache_size=0` 설정으로 prepared statement 비활성화
  - [x] 프로덕션 500 에러 해결 확인
  - [x] API 정상 응답 (200 OK) 확인
- **Created**: 2026-01-19
- **Completed**: 2026-01-19
- **Verified By**: Claude Code
- **Commit**: `888c96e fix(database): disable prepared statements for pgbouncer compatibility`
- **Notes**: CORS 에러로 표시되었지만 실제 원인은 서버 측 pgbouncer 충돌

---

### BUG-004: 503 에러 - DB 연결 풀 최적화
- **Source**: Render Starter Optimization 2026-01-19
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/database.py` - 연결 풀 크기 축소 (min:2, max:5)
- **Description**: Free-tier DB 연결 제한(~20)에 맞게 풀 크기 최적화
- **Acceptance Criteria**:
  - [x] min_size=2, max_size=5 설정
  - [x] max_inactive_connection_lifetime=300 추가
  - [x] 503 에러 감소 확인
- **Created**: 2026-01-19
- **Completed**: 2026-01-19
- **Verified By**: Claude Code
- **Notes**: 5회 연속 테스트 모두 200 OK 확인

---

### PERF-005: 프론트엔드 API 재시도 로직
- **Source**: Render Starter Optimization 2026-01-19
- **Status**: ✅ Completed
- **Assignee**: Frontend Team
- **Files**:
  - `frontend/lib/api.ts` - 503 에러 자동 재시도 로직 추가
- **Description**: Starter 플랜용 빠른 재시도 로직 (500ms 백오프)
- **Acceptance Criteria**:
  - [x] 3회 재시도 로직 구현
  - [x] 500ms × attempt 지수 백오프
  - [x] 네트워크 에러 및 503 처리
- **Created**: 2026-01-19
- **Completed**: 2026-01-19
- **Verified By**: Claude Code
- **Notes**: Starter 플랜은 cold start 없음 → 빠른 백오프 적용

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
