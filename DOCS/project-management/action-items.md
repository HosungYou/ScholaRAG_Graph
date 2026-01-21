# ScholaRAG_Graph Action Items

> 이 문서는 코드 리뷰, 기능 구현, 버그 수정 등에서 발견된 액션 아이템을 추적합니다.
>
> **마지막 업데이트**: 2026-01-20 (Codex Review)
> **관리자**: Claude Code

---

## 📊 Status Overview

| Priority | Total | Completed | In Progress | Pending |
|----------|-------|-----------|-------------|---------|
| 🔴 High | 15 | 15 | 0 | 0 |
| 🟡 Medium | 17 | 17 | 0 | 0 |
| 🟢 Low | 8 | 8 | 0 | 0 |
| **Total** | **40** | **40** | **0** | **0** |

---

## 🔴 High Priority (Immediate Action Required)

*All High Priority items have been completed! 🎉*

---

### TEST-001: InfraNodus DB Migrations 실행
- **Source**: InfraNodus Integration 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: DevOps Team
- **Files**:
  - `database/migrations/012_relationship_evidence.sql`
  - `database/migrations/013_entity_temporal.sql`
- **Description**: 새로운 InfraNodus 기능을 위한 DB 마이그레이션 실행 필요
- **Acceptance Criteria**:
  - [ ] Supabase에서 012_relationship_evidence.sql 실행
  - [ ] Supabase에서 013_entity_temporal.sql 실행
  - [ ] `migrate_entity_temporal_data()` 함수 실행하여 기존 데이터 백필
  - [ ] 테이블 및 인덱스 생성 확인
- **Created**: 2026-01-20
- **Related**: Session `2026-01-20_infranodus-integration.md`

---

## 🟡 Medium Priority (Short-term)

### ARCH-002: GraphStore God Object 리팩토링
- **Source**: Codex Review 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/graph/graph_store.py` - Facade로 리팩토링 (~300 라인)
  - `backend/graph/persistence/entity_dao.py` - Entity/Relationship CRUD (신규)
  - `backend/graph/persistence/chunk_dao.py` - Chunk 저장/검색 (신규)
  - `backend/graph/embedding/embedding_pipeline.py` - 임베딩 생성/검색 (신규)
  - `backend/graph/analytics/graph_analytics.py` - 통계/분석 (신규)
- **Description**: GraphStore가 persistence, graph algorithms, embeddings, import helpers, chunk storage를 모두 담당하여 결합도가 높고 테스트/확장이 어려움
- **Resolution**: Facade 패턴으로 리팩토링하여 4개 모듈로 분리. 기존 API는 100% 하위 호환성 유지.
- **Acceptance Criteria**:
  - [x] Persistence DAO 분리 (EntityDAO)
  - [x] Embedding pipeline 분리 (EmbeddingPipeline)
  - [x] Graph analytics 분리 (GraphAnalytics)
  - [x] Chunk storage 분리 (ChunkDAO)
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Related**: Codex Review Report

---

### PERF-008: 임베딩 업데이트 배치 처리
- **Source**: Codex Review 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/graph/graph_store.py:623-662` - 엔티티 임베딩 배치 업데이트
  - `backend/graph/graph_store.py:1329-1357` - 청크 임베딩 배치 업데이트
- **Description**: 임베딩 업데이트가 row별 개별 쿼리로 실행되어 대량 처리 시 성능 저하
- **Resolution**:
  1. `executemany`를 사용한 배치 업데이트 구현
  2. 배치 실패 시 개별 업데이트로 fallback
  3. 엔티티 및 청크 임베딩 모두 적용
- **Acceptance Criteria**:
  - [x] `executemany` 사용한 배치 업데이트 구현
  - [x] Fallback 로직 추가
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Related**: Codex Review Report, PERF-006 (동일 이슈)

---

### SEC-012: Auth 설정 불일치 처리
- **Source**: Codex Review 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/main.py:81-107` - Supabase 초기화 및 검증 로직
- **Description**: Supabase가 설정되지 않았지만 `require_auth=true`인 경우 503/401 에러 발생
- **Resolution**:
  1. 프로덕션에서 `require_auth=true`지만 Supabase 미설정 시 startup 실패
  2. 개발 환경에서 명확한 경고 출력 후 auth 자동 비활성화
- **Acceptance Criteria**:
  - [x] dev 모드에서 auth 자동 비활성화 + 명확한 경고
  - [x] prod에서 auth 필수인데 미설정 시 startup 실패
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Related**: Codex Review Report

---

### TEST-002: InfraNodus 새 API 엔드포인트 테스트
- **Source**: InfraNodus Integration 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Description**: 새로 추가된 6개 API 엔드포인트에 대한 단위 테스트 작성
- **Endpoints**:
  - `GET /api/graph/relationships/{id}/evidence`
  - `GET /api/graph/temporal/{project_id}`
  - `POST /api/graph/temporal/{project_id}/migrate`
  - `POST /api/graph/gaps/{id}/generate-bridge`
  - `GET /api/graph/diversity/{project_id}`
  - `GET /api/graph/compare/{a}/{b}`
- **Acceptance Criteria**:
  - [ ] 각 엔드포인트별 테스트 케이스 작성
  - [ ] 인증 및 권한 테스트 포함
  - [ ] 에러 케이스 테스트 포함
- **Created**: 2026-01-20
- **Related**: Session `2026-01-20_infranodus-integration.md`

---

### FUNC-004: TemporalSlider KnowledgeGraph 통합
- **Source**: InfraNodus Integration 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Frontend Team
- **Files**:
  - `frontend/components/graph/KnowledgeGraph.tsx`
  - `frontend/components/graph/TemporalSlider.tsx`
- **Description**: TemporalSlider 컴포넌트를 KnowledgeGraph 메인 뷰에 통합
- **Acceptance Criteria**:
  - [ ] KnowledgeGraph.tsx에 TemporalSlider 렌더링
  - [ ] useTemporalGraph 훅 연동
  - [ ] 연도별 노드 필터링 동작 확인
  - [ ] 애니메이션 재생/정지 기능 테스트
- **Created**: 2026-01-20
- **Related**: Session `2026-01-20_infranodus-integration.md`

---

### DOC-002: InfraNodus API 문서화
- **Source**: InfraNodus Integration 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Docs Team
- **Description**: 새로운 InfraNodus 관련 API 엔드포인트 문서화
- **Acceptance Criteria**:
  - [ ] API 엔드포인트별 요청/응답 스키마 문서화
  - [ ] 사용 예제 추가
  - [ ] CLAUDE.md API 섹션 업데이트
- **Created**: 2026-01-20
- **Related**: Session `2026-01-20_infranodus-integration.md`

---

### PERF-006: 청크 임베딩 배치 업데이트
- **Source**: Code Review (Codex) 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/graph/graph_store.py:1329-1357` - 청크 임베딩 배치 업데이트
- **Description**: 청크 임베딩이 개별 쿼리로 실행되어 대량 처리 시 성능 저하
- **Resolution**: PERF-008과 동일 - `executemany` 배치 업데이트 적용
- **Acceptance Criteria**:
  - [x] `executemany` 배치 업데이트 사용
  - [x] Fallback 로직 추가
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Related**: PERF-008 (동일 이슈로 함께 해결), Session `2026-01-20_render-docker-deployment-troubleshooting.md`

---

### PERF-004: 503 에러 모니터링
- **Source**: Render Starter Optimization 2026-01-19
- **Status**: ✅ Completed
- **Assignee**: DevOps Team
- **Files**:
  - `backend/middleware/error_tracking.py` - 에러 추적 서비스 (신규)
  - `backend/routers/system.py` - 에러 메트릭 엔드포인트 추가
  - `backend/main.py` - ErrorTrackingMiddleware 등록
  - `DOCS/operations/503-error-monitoring.md` - 모니터링 가이드 (신규)
- **Description**: 배포 후 503 에러 발생률 모니터링
- **Resolution**:
  1. `ErrorTracker` 클래스 - 에러 이벤트 인메모리 추적 (최근 100개)
  2. `ErrorTrackingMiddleware` - 모든 4xx/5xx 응답 자동 기록
  3. 503 에러 로그 포맷: `[503_ERROR] path=... method=... response_time_ms=...`
  4. API 엔드포인트:
     - `GET /api/system/metrics/errors` - 전체 에러 요약
     - `GET /api/system/metrics/error-rate` - 시간 윈도우별 에러율
     - `GET /api/system/metrics/503` - 503 에러 상세 분석
     - `GET /api/system/metrics/recent-errors` - 최근 에러 목록
  5. Render 알림 설정 가이드 문서화
- **Acceptance Criteria**:
  - [x] Render 로그에서 503 에러 빈도 확인 (로그 패턴 `[503_ERROR]`)
  - [x] 에러 발생 시 알림 설정 (문서화 완료)
  - [x] 에러 메트릭 API 엔드포인트 추가
- **Created**: 2026-01-19
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Related**: Session `2026-01-19_render-starter-optimization.md`

---

## 🟢 Low Priority (Long-term)

### TEST-004: Frontend 테스트 추가
- **Source**: Codex Review 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Frontend Team
- **Files**:
  - `frontend/jest.config.js` - Jest 설정 (신규)
  - `frontend/jest.setup.js` - 테스트 setup (신규)
  - `frontend/__tests__/components/ui/ErrorDisplay.test.tsx` - ErrorDisplay 테스트 (신규)
  - `frontend/__tests__/components/ui/Skeleton.test.tsx` - Skeleton 테스트 (신규)
  - `frontend/__tests__/components/auth/LoginForm.test.tsx` - LoginForm 테스트 (신규)
  - `frontend/package.json` - 테스트 의존성 추가
- **Description**: 프론트엔드 컴포넌트 테스트 및 E2E smoke 테스트 부재
- **Resolution**:
  1. Jest + React Testing Library 설정
  2. Next.js router 및 Supabase 클라이언트 mock
  3. ErrorDisplay, Skeleton, LoginForm 컴포넌트 테스트 작성
- **Acceptance Criteria**:
  - [x] 핵심 컴포넌트 unit 테스트 추가
  - [ ] Auth flow E2E 테스트 (future)
  - [ ] CI에 테스트 연동 (future)
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Related**: Codex Review Report

---

### FUNC-005: Per-Project/User API 할당량
- **Source**: Codex Review 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `database/migrations/014_api_quota.sql` - DB 스키마 (신규)
  - `backend/middleware/quota_service.py` - 쿼터 서비스 (신규)
  - `backend/middleware/quota_middleware.py` - FastAPI 미들웨어 (신규)
  - `backend/routers/quota.py` - 쿼터 API 라우터 (신규)
  - `backend/routers/integrations.py` - 쿼터 의존성 적용
  - `backend/main.py` - 쿼터 미들웨어 등록
- **Description**: 외부 통합(Semantic Scholar, OpenAlex 등)에 대한 프로젝트/사용자별 할당량 없음
- **Resolution**:
  1. DB 스키마 추가: `api_quota_plans`, `user_quota_assignments`, `api_usage` 테이블
  2. 4단계 플랜 (free, basic, premium, enterprise) 각각 다른 할당량
  3. `QuotaService` - 쿼터 확인, 사용량 추적, 인메모리 캐싱
  4. `QuotaDependency` - FastAPI 의존성으로 쿼터 체크
  5. `QuotaTrackingMiddleware` - 자동 사용량 추적
  6. `/api/quota/*` 엔드포인트 - 사용량 조회 API
  7. 응답 헤더에 쿼터 정보 포함 (X-Quota-Limit, X-Quota-Used, X-Quota-Remaining)
- **Acceptance Criteria**:
  - [x] 프로젝트별 또는 사용자별 일일 API 호출 제한
  - [x] 초과 시 경고 (80%) 또는 차단 (100%)
  - [x] 쿼터 현황 조회 API
  - [x] 응답 헤더에 쿼터 정보 포함
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Related**: Codex Review Report

---

### TEST-003: InfraNodus E2E 테스트
- **Source**: InfraNodus Integration 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: QA Team
- **Description**: 모든 InfraNodus 기능에 대한 수동 E2E 테스트
- **Test Cases**:
  - [ ] Edge 클릭 → EdgeContextModal 열림 → 원문 표시 확인
  - [ ] TemporalSlider 연도 조절 → 노드 필터링 확인
  - [ ] GapPanel "Generate Bridge" 클릭 → 가설 생성 확인
  - [ ] InsightHUD 다양성 게이지 표시 확인
  - [ ] /projects/compare 페이지 → 프로젝트 비교 동작 확인
- **Created**: 2026-01-20
- **Related**: Session `2026-01-20_infranodus-integration.md`

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

### SEC-011: Rate Limiter X-Forwarded-For Spoofing 취약점
- **Source**: Codex Review 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Priority**: 🔴 High (Security Vulnerability)
- **Files**:
  - `backend/middleware/rate_limiter.py:305-356` - trusted proxy 로직 추가
  - `backend/config.py:81-87` - `trusted_proxy_mode` 설정 추가
- **Description**: Rate limiter가 `X-Forwarded-For` 헤더를 무조건 신뢰하여 IP 스푸핑으로 rate limit 우회 가능
- **Risk**: DoS 공격, Rate limit 우회
- **Resolution**:
  1. `trusted_proxy_mode` 설정 추가 (`auto`, `always`, `never`)
  2. `auto` 모드: 프로덕션에서만 X-Forwarded-For 신뢰 (Render LB 뒤)
  3. 개발 환경에서는 직접 연결 IP 사용하여 스푸핑 방지
  4. 디버그 로깅으로 IP 소스 추적 가능
- **Acceptance Criteria**:
  - [x] Trusted proxy 설정 추가
  - [x] 프록시 뒤에 있을 때만 `X-Forwarded-For` 사용
  - [x] 환경별 자동 감지 (`auto` 모드)
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Related**: Codex Review Report, Session `2026-01-20_mixed-content-cors-fix.md`

---

### ARCH-001: DB 연결 실패 시 일관된 동작 구현
- **Source**: Codex Review 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Priority**: 🔴 High (Architecture)
- **Files**:
  - `backend/main.py:88-114` - DB 초기화 + fail-fast 로직
  - `backend/database.py:184-207` - `require_db()` dependency 추가
- **Description**: DB 초기화 실패 시 앱이 계속 실행되지만 대부분의 엔드포인트가 500 에러 발생
- **Risk**: Cascading 500 에러, 불일치한 동작
- **Resolution**:
  1. 프로덕션/스테이징에서 DB 연결 실패 시 fail-fast (앱 시작 차단)
  2. `require_db()` dependency 추가 - DB 없으면 503 반환
  3. 개발 환경에서만 memory-only 모드 허용
- **Acceptance Criteria**:
  - [x] 프로덕션에서 DB 실패 시 fail-fast
  - [x] `require_db()` dependency로 일관된 503 응답
  - [x] 개발 환경에서 memory-only 모드 허용
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: Claude Code
- **Related**: Codex Review Report

---

### BUG-015: Mixed Content & CORS Error (Vercel Preview)
- **Source**: Production Error 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Frontend Team
- **Priority**: 🔴 High (Production CORS Error)
- **Files**:
  - `frontend/lib/api.ts` - HTTPS 강제 로직 추가
- **Description**: Vercel Preview 배포에서 Mixed Content 에러와 CORS 에러 발생
- **Error Messages**:
  ```
  Mixed Content: The page at 'https://...' was loaded over HTTPS, but requested
  an insecure resource 'http://scholarag-graph-docker.onrender.com/api/projects/'

  CORS error: Access to fetch blocked - No 'Access-Control-Allow-Origin' header
  Origin: https://schola-rag-graph-1fugffud8-hosung-yous-projects.vercel.app
  ```
- **Root Cause**: `NEXT_PUBLIC_API_URL` 환경변수가 HTTP로 설정되어 HTTPS 페이지에서 HTTP 요청 차단됨
- **Resolution**:
  1. `enforceHttps()` 함수 추가하여 HTTPS 페이지에서 자동으로 HTTP → HTTPS 변환
  2. 디버그 로깅 개선으로 HTTPS 강제 여부 표시
- **Commit**: `22217b5`
- **Completed**: 2026-01-20
- **Related**: Session `2026-01-20_mixed-content-cors-fix.md`

---

### BUG-014: Rate Limiter 429 응답에 CORS 헤더 누락
- **Source**: Production Error 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Priority**: 🔴 High (Production CORS Error)
- **Files**:
  - `backend/middleware/rate_limiter.py:330-342` - 429 응답 생성 로직
- **Description**: Import 진행 중 status 폴링이 rate limit(5/min)에 걸리면 429 응답이 CORS 헤더 없이 반환되어 브라우저에서 CORS 에러로 표시됨
- **Error Message**:
  ```
  429 Too Many Requests
  CORS error: No 'Access-Control-Allow-Origin' header present
  ```
- **Root Cause**: `JSONResponse`를 직접 반환하면 CORS middleware를 우회함
- **Resolution**:
  1. Rate limiter 429 응답에 CORS 헤더 추가
  2. `/api/import/status/*` 폴링 limit 완화 (60/min)
  3. `/api/import/*` limit 증가 (5 → 10/min)
- **Commit**: `882f14a`
- **Completed**: 2026-01-20
- **Related**: Session `2026-01-20_render-docker-deployment-troubleshooting.md`

---

### BUG-013: semantic_chunker `Any` 타입 임포트 누락
- **Source**: Production Error Log 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Priority**: 🔴 High (Production 500 Error)
- **Files**:
  - `backend/importers/semantic_chunker.py:15` - typing import
  - `backend/importers/semantic_chunker.py:461` - `Dict[str, Any]` 반환 타입
- **Description**: `/api/import/zotero/validate` 엔드포인트 호출 시 500 Internal Server Error 발생
- **Error Message**:
  ```
  NameError: name 'Any' is not defined
  File "/app/importers/semantic_chunker.py", line 461, in SemanticChunker
  ```
- **Root Cause**: `typing` 모듈에서 `Any`가 임포트되지 않았으나 `Dict[str, Any]` 타입 힌트에서 사용됨
- **Fix**:
  ```python
  # Before
  from typing import List, Optional, Dict, Tuple
  # After
  from typing import List, Optional, Dict, Tuple, Any
  ```
- **Acceptance Criteria**:
  - [x] `Any` 타입 임포트 추가
  - [x] `/api/import/zotero/validate` 정상 작동 확인
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Commit**: `d2dd6d6`
- **Verified By**: Claude Code
- **Lesson Learned**: 타입 힌트 추가 시 해당 타입이 임포트되었는지 확인 필요

---

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

### INFRA-004: 기존 Python 서비스 삭제
- **Source**: Render Docker Deployment 2026-01-20
- **Status**: ✅ Completed
- **Assignee**: DevOps Team
- **Description**: Docker 서비스로 마이그레이션 완료 후 기존 Python 서비스 삭제
- **Service ID**: `srv-d5n4aesoud1c739ot8a0` (삭제됨)
- **Acceptance Criteria**:
  - [x] 기존 Python 서비스 삭제
- **Created**: 2026-01-20
- **Completed**: 2026-01-20
- **Verified By**: User (수동 삭제)
- **Notes**: Render Dashboard에서 수동 삭제 완료
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
