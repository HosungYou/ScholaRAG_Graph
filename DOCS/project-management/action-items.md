# ScholaRAG_Graph Action Items

> 이 문서는 코드 리뷰, 기능 구현, 버그 수정 등에서 발견된 액션 아이템을 추적합니다.
>
> **마지막 업데이트**: 2026-02-04
> **관리자**: Claude Code

---

## 📊 Status Overview

| Priority | Total | Completed | In Progress | Pending |
|----------|-------|-----------|-------------|---------|
| 🔴 High | 19 | 19 | 0 | 0 |
| 🟡 Medium | 20 | 20 | 0 | 0 |
| 🟢 Low | 5 | 5 | 0 | 0 |
| **Total** | **44** | **44** | **0** | **0** |

---

## 🔴 High Priority (Immediate Action Required)

*모든 High Priority 항목이 완료되어 Archive 섹션으로 이동되었습니다.*

---

## 🟡 Medium Priority (Short-term)

*모든 Medium Priority 항목이 완료되어 Archive 섹션으로 이동되었습니다.*

---

## 📝 v0.4.0 Release - Completed Items (2026-02-04)

### BUG-041: AI Chat Returns Research Analysis for Greetings
- **Source**: 사용자 피드백 2026-02-04
- **Status**: ✅ Completed
- **Priority**: 🔴 High
- **Files**:
  - `backend/agents/intent_agent.py` - CONVERSATIONAL intent 추가
  - `backend/agents/orchestrator.py` - 조기 반환 로직 추가
- **Description**: "안녕" 입력 시 친근한 인사 대신 연구 갭 분석 결과 반환
- **Root Cause**: Intent Agent가 인사를 SEARCH로 분류 → 빈 검색 결과 → Gap 분석 반환
- **Solution Applied**:
  - [x] `CONVERSATIONAL` intent type 추가
  - [x] 인사 패턴 감지 (안녕, hello, hi, thanks 등)
  - [x] Orchestrator에서 조기 반환으로 친근한 응답 제공
- **Completed**: 2026-02-04
- **Commit**: 2b5c1ec

---

### BUG-042: Node Jitter on Hover/Highlight
- **Source**: UI 테스트 2026-02-04
- **Status**: ✅ Completed
- **Priority**: 🔴 High
- **Files**:
  - `frontend/components/graph/Graph3D.tsx` - dependency 수정
  - `frontend/next.config.js` - Three.js webpack alias
- **Description**: 노드에 마우스 올리거나 하이라이트 시 그래프 전체가 흔들림
- **Root Cause**: `nodeThreeObject`의 dependency에 `hoveredNode` 포함 → 모든 노드 재생성 → 시뮬레이션 재시작
- **Solution Applied**:
  - [x] `hoveredNode`를 dependency에서 제거
  - [x] `cooldownTicks` 50 → 0으로 변경 (비초기 렌더)
  - [x] CSS cursor로 hover 피드백 대체
  - [x] Three.js 다중 인스턴스 경고 수정
- **Completed**: 2026-02-04
- **Commit**: 2b5c1ec

---

### BUG-043: Filter Buttons Not Reactive
- **Source**: UI 테스트 2026-02-04
- **Status**: ✅ Completed
- **Priority**: 🟡 Medium
- **Files**:
  - `frontend/components/graph/KnowledgeGraph3D.tsx` - useMemo dependency 추가
- **Description**: Filter 버튼 클릭해도 그래프가 업데이트되지 않음
- **Root Cause**: `filters` 상태가 `displayData` useMemo dependency에 누락
- **Solution Applied**:
  - [x] `filters`를 useGraphStore subscription에 추가
  - [x] `filters`를 displayData useMemo dependency에 추가
- **Completed**: 2026-02-04
- **Commit**: 2b5c1ec

---

### FUNC-015: Bridge Creation Feature Implementation
- **Source**: 기능 요청 2026-02-04
- **Status**: ✅ Completed
- **Priority**: 🟢 Low
- **Files**:
  - `backend/routers/graph.py` - create-bridge endpoint
  - `frontend/lib/api.ts` - createBridge() method
  - `frontend/components/graph/GapPanel.tsx` - handler UI
- **Description**: Gap 분석에서 Bridge 가설 수락 시 실제 관계 생성
- **Solution Applied**:
  - [x] `POST /api/graph/gaps/{gap_id}/create-bridge` endpoint
  - [x] `BRIDGES_GAP` relationship 생성 로직
  - [x] Frontend API client method
  - [x] Loading state 및 결과 알림 UI
- **Completed**: 2026-02-04
- **Commit**: 2b5c1ec

---

### PERF-011: Memory Optimization for 512MB Render Starter
- **Source**: Render OOM 에러 2026-02-04
- **Status**: ✅ Completed
- **Priority**: 🔴 High
- **Files**:
  - `backend/llm/cohere_embeddings.py` - singleton 제거, close() 추가
  - `backend/llm/openai_embeddings.py` - singleton 제거, close() 추가
  - `backend/llm/groq_provider.py` - close() method
  - `backend/llm/claude_provider.py` - close() method
  - `backend/llm/openai_provider.py` - close() method
  - `backend/main.py` - periodic cleanup, shutdown cleanup
  - `backend/agents/orchestrator.py` - context TTL
- **Description**: Render Starter 512MB 메모리 제한에서 OOM 발생
- **Root Cause**:
  - Embedding/LLM provider singleton 패턴으로 클라이언트 누적
  - 캐시 정리 없이 무한 성장
  - 대화 컨텍스트 무한 저장
- **Solution Applied**:
  - [x] Embedding provider: singleton → factory + close()
  - [x] LLM provider: close() methods 추가
  - [x] 주기적 캐시 정리 (5분마다)
  - [x] 대화 컨텍스트 TTL (24시간, 최대 50개)
- **Memory Impact**: ~100MB+ 절감 (450-512MB → 320-400MB)
- **Completed**: 2026-02-04
- **Commit**: bce2f13

---

## 📝 Medium Priority - Completed Archive

### UI-010: Node Drag Stability (Snap-back, Jitter, Graph Reset)
- **Source**: 사용자 피드백 2026-01-21 (이전 수정 불완전)
- **Status**: ✅ Completed
- **Assignee**: Frontend Team
- **Files**:
  - `frontend/components/graph/Graph3D.tsx` - 위치 유지 시스템 종합 구현
- **Description**: 노드 드래그 시 3가지 문제 발생:
  1. 스냅백 (Snap-back): 드래그 후 원위치로 복귀
  2. 고주파 진동 (Jitter): 노드가 파르르 떨림
  3. 그래프 리셋 (Explosion): 하이라이트 변경 시 전체 그래프 재배치
- **Root Cause**:
  - `graphData` useMemo가 `highlightedNodeSet` 변경 시마다 노드 객체를 재생성
  - 새 객체로 인해 fx/fy/fz (고정 위치) 값이 손실
  - ForceGraph3D가 새 데이터로 인식하여 시뮬레이션 재시작
- **Solution Applied**:
  - [x] `nodePositionsRef`로 노드 위치를 re-render 간에 유지
  - [x] `graphData` useMemo에서 ref의 위치를 복원
  - [x] 500ms 간격으로 위치를 저장하는 interval 추가
  - [x] 드래그 핸들러에서 위치를 ref에 즉시 저장
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Commit**: bbe3554
- **Notes**: UI-005 물리 파라미터 수정은 증상만 완화, 이 수정이 근본 원인 해결

---

### UI-006: Node Labels 중심성 기반 폰트 스케일링 누락
- **Source**: 시각화 UI 리뷰 2026-01-21 (스크린샷 분석)
- **Status**: ✅ Completed
- **Assignee**: Frontend Team
- **Files**:
  - `frontend/components/graph/Graph3D.tsx` - 폰트 크기 동적 계산 추가
- **Description**: 노드 라벨이 고정 14px 폰트로 표시되어 시각적 계층 구조 부재
- **Root Cause**:
  - `createTextSprite(displayName, labelColor, 14)` 고정값 사용
  - 노드 중심성에 따른 폰트 스케일링 미구현
- **Solution Applied**:
  - [x] 중심성 기반 폰트 크기 계산 (10px ~ 22px 범위)
  - [x] `centralityNormalized = Math.min(1, nodeCentrality / 0.5)` 정규화
  - [x] 라벨 위치도 폰트 크기에 따라 동적 조정
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Notes**: 중심성 높은 노드 = 큰 폰트, 시각적 계층 구조 제공

---

### UI-004: LLM Panel에 잘못된 프로바이더 표시 (Groq 대신 Anthropic)
- **Source**: 사용자 리포트 2026-01-21 (StatusBar에 claude-3-5-haiku 표시되나 Groq만 사용)
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/system.py` - check_llm_connection()에 Groq 지원 추가
  - `backend/config.py` - 기본 LLM 프로바이더를 groq으로 변경
- **Description**: StatusBar에 "claude-3-5-haiku-20241022" 표시되지만 사용자는 Groq만 사용하도록 환경변수 설정함
- **Root Cause**:
  1. `backend/config.py`의 기본값이 anthropic/claude-3-5-haiku로 설정됨
  2. `check_llm_connection()`에서 Groq provider에 대한 API 키 체크 로직 누락
  3. `settings` 객체가 환경변수보다 기본값 우선 사용하는 경우 발생
- **Solution Applied**:
  - [x] `config.py` 기본값 변경: anthropic → groq, claude-3-5-haiku → llama-3.3-70b-versatile
  - [x] `check_llm_connection()`에 Groq provider case 추가
  - [x] `os.getenv()` 직접 사용으로 환경변수 우선 읽기
  - [x] 모든 4개 provider (anthropic, openai, google, groq)에 대한 API 키 체크 로직 통일
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Commit**: aa71318
- **Notes**: Render 수동 배포 필요 (INFRA-006: Auto-Deploy OFF)

---

### UI-005: Force Simulation Jitter/Oscillation - d3-force 파라미터 방향 오류
- **Source**: 시각화 UI 리뷰 2026-01-21 (스크린샷 분석 + 사용자 상세 피드백)
- **Status**: ✅ Completed
- **Assignee**: Frontend Team
- **Files**:
  - `frontend/components/graph/Graph3D.tsx` - d3 force 파라미터 최적화
- **Description**: 노드 드래그/클릭 시 "jittery, oscillating, rubber-banding" 현상 - 노드가 빠르게 진동하며 안정화되지 않음
- **Root Cause**:
  - d3-force 파라미터 방향 혼동 (높은 값 = 빠른 감쇠)
  - 초기 수정에서 값을 낮춰 오히려 악화시킴
- **Initial (Wrong) Fix**:
  - ❌ `d3AlphaDecay` 0.05 → 0.02 (더 느린 냉각 = 악화)
  - ❌ `d3VelocityDecay` 0.7 → 0.4 (더 적은 댐핑 = 악화)
- **Final (Correct) Fix**:
  - [x] `d3AlphaDecay` → 0.1 (빠른 냉각, 기본값 0.0228의 4배)
  - [x] `d3VelocityDecay` → 0.85 (높은 댐핑, 진동 억제)
  - [x] `d3AlphaMin` → 0.01 (조기 종료)
  - [x] `cooldownTicks` → 100 (충분한 냉각 틱)
- **d3-force Parameter Reference**:
  - `d3AlphaDecay`: 높은 값 = 빠른 냉각/안정화
  - `d3VelocityDecay`: 높은 값 = 높은 마찰/댐핑 (진동 감소)
  - `d3AlphaMin`: 높은 값 = 조기 시뮬레이션 종료
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Commit**: aa71318
- **Notes**: d3-force 파라미터는 Decay라는 이름과 달리 높은 값 = 빠른 감쇠. 공식 문서 확인 필수.

---

### UI-003: Node Type 토글 필터링 미작동 - 자동 동기화 버그
- **Source**: 시각화 UI 리뷰 2026-01-21 (스크린샷 분석)
- **Status**: ✅ Completed
- **Assignee**: Frontend Team
- **Files**:
  - `frontend/app/projects/[id]/page.tsx` - hasInitializedFilters 상태 추가
- **Description**: NODE TYPES 패널에서 토글 off/on해도 노드가 숨겨지거나 표시되지 않음
- **Root Cause**:
  - `useEffect`가 `actualEntityTypes` 변경 시마다 실행
  - 토글 off → validSelectedTypes.length === 0 → 모든 타입 자동 재선택
  - 사용자 필터 선택이 즉시 덮어씌워짐
- **Solution Applied**:
  - [x] `hasInitializedFilters` 상태 추가
  - [x] 초기 로드 시에만 자동 동기화 실행
  - [x] 초기화 후 사용자 자유로운 필터 토글 허용
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Notes**: 초기 필터 동기화 후 사용자 자유도 보장

---

### BUG-042: list_import_jobs가 빈 배열 반환
- **Source**: 사용자 리포트 2026-01-21 (중단된 Import 미표시)
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/import_.py` - 모든 import 관련 job_type 조회 추가
- **Description**: `/api/import/jobs` API가 빈 배열 `[]`을 반환하여 중단된 Import가 UI에 표시되지 않음
- **Root Cause**:
  - `list_import_jobs`가 `job_type="import"`만 조회
  - Zotero Import는 `job_type="zotero_import"` 사용
  - PDF Import는 `job_type="pdf_import"` 또는 `"pdf_import_multiple"` 사용
- **Solution Applied**:
  - [x] 모든 import 관련 job_type 조회: `import`, `pdf_import`, `pdf_import_multiple`, `zotero_import`
  - [x] 결과를 `created_at` 기준 정렬 후 limit 적용
- **Evidence**:
  ```
  GET /api/import/jobs?limit=20 → [] (empty)
  GET /api/import/status/{zotero_job_id} → {"status": "processing"} (works)
  ```
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Commit**: 908d60c
- **Notes**: Render 재배포 완료

---

### BUG-041: total_papers가 항상 0으로 표시
- **Source**: 사용자 리포트 2026-01-21 (프로젝트 목록 스크린샷)
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/projects.py` - paper_metadata 테이블 카운트 추가
- **Description**: 모든 프로젝트에서 `total_papers: 0`으로 표시되지만 실제로는 논문 데이터가 존재함
- **Root Cause**:
  - ADR-001에 따라 Papers는 `paper_metadata` 테이블에 저장 (엔티티 아님)
  - 하지만 `_get_project_stats_batch()`가 `entities` 테이블에서 `entity_type='Paper'` 카운트
  - 결과적으로 항상 0 반환
- **Solution Applied**:
  - [x] `paper_metadata` 테이블에서 별도 카운트 쿼리 추가
  - [x] `total_papers`가 `paper_lookup.get(pid, 0)` 사용하도록 변경
- **Evidence**:
  ```json
  // Before fix
  {"stats": {"total_papers": 0, "total_concepts": 1805, ...}}

  // After fix (expected)
  {"stats": {"total_papers": 16, "total_concepts": 1805, ...}}
  ```
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Commit**: 908d60c
- **Notes**: Render 재배포 완료

---

### INFRA-007: 502/503 에러 응답에 CORS 헤더 누락
- **Source**: Import 스크린샷 분석 2026-01-21 (CORS 에러 다수 발생)
- **Status**: ✅ Completed (Partial)
- **Assignee**: DevOps Team
- **Files**:
  - `backend/middleware/cors_error_handler.py` - CORSErrorHandlerMiddleware 추가
  - `backend/main.py` - 미들웨어 등록
  - `DOCS/development/frontend-cors-error-handling.md` - 프론트엔드 가이드
- **Description**: Render 서버 에러(502/503) 시 CORS 헤더가 없어서 브라우저가 응답 차단
- **Root Cause**:
  - FastAPI CORSMiddleware는 정상 응답에만 CORS 헤더 추가
  - Render 로드밸런서가 반환하는 502/503 에러에는 CORS 헤더 없음
  - 프론트엔드에서 에러 내용 확인 불가 (CORS 차단으로 인해)
- **Solution Applied**:
  - [x] Option C: CORSErrorHandlerMiddleware 구현 - 예외를 JSONResponse로 래핑
  - [x] Option B: 프론트엔드 CORS 에러 핸들링 가이드 작성
  - [ ] Option A: Cloudflare 프록시 (필요시 추가 검토)
- **Limitation**:
  - Render LB가 직접 반환하는 502/503은 FastAPI 도달 전이므로 처리 불가
  - 프론트엔드에서 NetworkError로 graceful 처리 필요 (가이드 참조)
- **Evidence**:
  ```
  Console: Access to fetch at '.../api/import/status/...' has been blocked by CORS policy
  Network: Status 502 → CORS 헤더 없음 → 브라우저 차단
  ```
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Notes**: Render 재배포 필요, 프론트엔드 에러 핸들링 권장

---

## 🟢 Low Priority (Long-term)

*모든 Low Priority 항목이 완료되어 Archive 섹션으로 이동되었습니다.*

---

## 📝 Low Priority - Completed Archive

### PERF-011: Import 처리 중 17분 로그 공백 원인 조사
- **Source**: Import 로그 분석 2026-01-21
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/graph/entity_extractor.py` - LLM API 호출 시간 측정 로깅 추가
  - `backend/importers/zotero_rdf_importer.py` - 논문별 처리 시간 로깅 추가
- **Description**: Import 중 10:29:56 → 10:47:20 사이 약 17분 40초 동안 로그 출력 없음
- **Possible Causes**:
  - Entity 추출 중 Groq API 레이트 리밋 대기
  - 메모리 부족으로 GC 지연
  - asyncio 이벤트 루프 블로킹
  - DB 커넥션 풀 고갈
- **Solution Applied**:
  - [x] LLM API 호출 전/후 타이밍 로그 추가 (`PERF-011:` 접두어)
  - [x] Slow API call 감지 (>10초 시 WARNING)
  - [x] 논문별 처리 시간 측정 및 로깅
  - [x] Slow paper processing 감지 (>30초 시 WARNING)
  - [x] 각 논문 처리 시작/완료 로그 추가
- **New Log Patterns**:
  ```
  PERF-011: Starting paper 1/16: 'Paper Title...'
  PERF-011: Starting LLM API call for 'Paper Title...' (attempt 1)
  PERF-011: Slow LLM API call: 15.2s for 'Paper Title...'  # WARNING if >10s
  PERF-011: Completed paper 1/16 in 18.5s: 'Paper Title...'
  PERF-011: Slow paper processing: 45.3s for 'Paper Title...'  # WARNING if >30s
  ```
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Priority Justification**: 디버깅 용이성 개선, Render 재배포 필요

---

## 📝 Completed Items Archive

### PERF-012: OpenAI를 Primary 임베딩 프로바이더로 변경
- **Source**: 비용/안정성 분석 2026-01-21
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/graph/embedding/embedding_pipeline.py` - 프로바이더 우선순위 변경
- **Description**: OpenAI가 Cohere보다 6배 저렴하고 더 안정적이므로 Primary로 변경
- **Cost Comparison**:
  | Provider | Price (per 1M tokens) | Notes |
  |----------|----------------------|-------|
  | OpenAI text-embedding-3-small | **$0.02** | 6x cheaper, more stable |
  | Cohere embed-v4 | $0.12 | Has free tier but limited |
- **Solution Applied**:
  - [x] `_get_embedding_provider()` - OpenAI 우선으로 변경
  - [x] `_get_embedding_providers()` - OpenAI Primary, Cohere Fallback
  - [x] 클래스 docstring 업데이트
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Notes**: Render 재배포 필요

---

### BUG-040: Cohere API 연결 실패 시 복원력 부족
- **Source**: Import 로그 분석 2026-01-21 (Import 86%에서 embedding 전부 실패)
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/llm/cohere_embeddings.py` - 재시도 로직 추가
  - `backend/graph/embedding/embedding_pipeline.py` - 멀티 프로바이더 폴백 추가
- **Description**: Cohere API ConnectError 발생 시 재시도 없이 즉시 실패, 전체 embedding이 0개로 손실
- **Root Cause**:
  - `ERROR:llm.cohere_embeddings:Cohere embedding error (ConnectError): (no message)`
  - 네트워크 일시 장애에 대한 복원력 없음
  - BUG-038의 slow call 감지는 동작했으나, ConnectError 재시도가 없음
- **Solution Applied**:
  - [x] Cohere API 호출에 exponential backoff 재시도 로직 추가 (최대 3회: 1s→2s→4s)
  - [x] ConnectError, TimeoutError, OSError 등 네트워크 에러 시 자동 재시도
  - [x] httpx, httpcore 예외도 재시도 대상에 포함
  - [x] 총 5회 이상 재시도 발생 시 조기 종료 (API 불안정 감지)
  - [x] `_get_embedding_providers()` 메서드 추가로 primary/fallback 프로바이더 관리
  - [x] Cohere 실패 시 OpenAI로 자동 폴백
  - [x] 폴백 실패 시에도 import 계속 진행 (embeddings 없이)
- **Evidence**:
  ```
  10:48:26 WARNING: Cohere API slow: 10.8s for batch 723
  10:48:58 WARNING: Cohere API slow: 30.1s for batch 724
  10:50:19 ERROR: Cohere embedding error (ConnectError): (no message)
  10:50:19 INFO: Created 0 embeddings  ← 이제 재시도 + 폴백으로 방지
  ```
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Notes**: Render 재배포 필요

---

### BUG-039: DB 연결 실패 시 Job 데이터 손실
- **Source**: 중단된 Import 미표시 원인 분석 2026-01-21
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/jobs/job_store.py` - 재시도 로직 추가
- **Description**: DB 연결 타임아웃 시 job이 메모리에만 저장되어 서버 재시작 시 데이터 손실
- **Root Cause**:
  - `WARNING:jobs.job_store:Failed to get job from DB: TimeoutError`
  - DB 연결 실패 시 메모리 폴백으로 저장
  - 서버 재시작 시 메모리 데이터 손실
- **Solution Applied**:
  - [x] `_db_execute_with_retry()` 헬퍼 함수 추가
  - [x] Exponential backoff (3회 재시도: 0.5s → 1s → 2s)
  - [x] `create_job()`, `update_job()` 에 재시도 로직 적용
  - [x] 재시도 실패 시에만 메모리 폴백
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Notes**: Render 재배포 필요

---

### BUG-038: Cohere Embedding 에러 메시지 누락 및 타임아웃
- **Source**: 사용자 로그 분석 2026-01-21 (Import 86%에서 멈춤)
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/llm/cohere_embeddings.py` - 타임아웃 및 느린 호출 감지 추가
  - `backend/graph/embedding/embedding_pipeline.py` - 에러 로깅 개선
- **Description**: Cohere API 호출이 점점 느려지다가 에러 발생 (빈 에러 메시지)
- **Root Cause**:
  - Cohere API 레이트 리밋 또는 네트워크 문제로 응답 지연 (0.25s → 31s)
  - 긴 API 호출이 asyncio 이벤트 루프 블로킹 → DB 커넥션 풀 고갈
  - Exception의 `str()` 반환값이 빈 문자열
- **Solution Applied**:
  - [x] Cohere API 호출에 30초 타임아웃 추가
  - [x] 3회 이상 느린 호출(>10s) 시 조기 종료
  - [x] 에러 로깅에 예외 타입 포함 (`error_type = type(e).__name__`)
  - [x] 빈 에러 메시지 처리 (`str(e) if str(e) else "(no message)"`)
  - [x] 느린 API 호출 시 배치 간 딜레이 증가 (0.1s → 0.5s)
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Notes**: Render 재배포 필요, Cohere API 상태 모니터링 권장

---

### BUG-037: ImportJobResponse metadata 필드 누락
- **Source**: UI-002 구현 중 발견 2026-01-21
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/import_.py` - ImportJobResponse에 metadata 필드 추가
- **Description**: `ImportJobResponse`에 `metadata` 필드가 없어서 프론트엔드가 project_name, checkpoint 정보를 받을 수 없음
- **Solution Applied**:
  - [x] `ImportJobResponse`에 `metadata: Optional[dict] = None` 필드 추가
  - [x] `list_import_jobs` 엔드포인트에서 metadata 반환 추가
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Notes**: BUG-036과 함께 Render 재배포 필요

---

### BUG-036: list_import_jobs INTERRUPTED 상태 누락
- **Source**: 중단된 Import 미표시 문제 분석 2026-01-21
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/import_.py` - status_map에 INTERRUPTED 추가
- **Description**: `list_import_jobs` 엔드포인트의 `status_map`에 `INTERRUPTED` 상태가 누락되어 interrupted 상태의 job이 pending으로 잘못 표시됨
- **Root Cause**:
  - `get_job_status`에는 INTERRUPTED 매핑 있음
  - `list_import_jobs`에는 INTERRUPTED 매핑 누락 (코드 복사 시 누락)
- **Solution Applied**:
  - [x] `status_map`에 `JobStatus.INTERRUPTED: ImportStatus.INTERRUPTED` 추가
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Notes**: Render 재배포 필요

---

### BUG-035: Resume Checkpoint project_id 누락
- **Source**: 사용자 리포트 2026-01-21 (Resume 400 Bad Request)
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/routers/import_.py` - checkpoint project_id 업데이트 로직 추가
- **Description**: Resume 시도 시 "Cannot resume: Checkpoint is missing project_id" 에러 발생
- **Root Cause**:
  - checkpoint는 import 진행 중 매번 저장됨
  - 하지만 project_id는 import 완료 후에야 설정됨
  - 첫 번째 checkpoint에 project_id가 None으로 저장됨
- **Solution Applied**:
  - [x] import 완료 후 checkpoint를 명시적으로 업데이트하여 project_id 설정
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Notes**: Render 재배포 필요

---

### UI-002: 중단된 Import 목록 표시 기능
- **Source**: 사용자 요청 2026-01-21
- **Status**: ✅ Completed
- **Assignee**: Frontend Team
- **Files**:
  - `frontend/app/projects/page.tsx` - InterruptedImportsSection 컴포넌트 추가
  - `frontend/lib/api.ts` - getImportJobs() API 메서드 추가
  - `frontend/types/graph.ts` - ImportJob 타입에 created_at, updated_at, metadata 추가
- **Description**: 프로젝트 목록 페이지에서 중단된 Import를 확인하고 Resume 할 수 있어야 함
- **Features Implemented**:
  - [x] 중단된 Import 목록 표시 (amber 색상 경고 박스)
  - [x] Resume 버튼으로 재시작 가능
  - [x] 날짜 + 시간(HH:MM) 표시
  - [x] 진행률 표시
  - [x] 한국어 UI
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Notes**: Vercel 자동 배포

---

### PERF-010: 추가 메모리 최적화 (512MB 재초과)
- **Source**: PERF-009 적용 후에도 메모리 초과 발생 2026-01-21
- **Status**: ✅ Completed
- **Assignee**: Backend Team
- **Files**:
  - `backend/llm/cohere_embeddings.py` - batch_size 20 → 5
  - `backend/llm/openai_embeddings.py` - batch_size 20 → 5
  - `backend/graph/embedding/embedding_pipeline.py` - batch_size 20 → 5
  - `backend/graph/graph_store.py` - batch_size 20 → 5
  - `backend/config.py` - llm_cache_max_size 100 → 50
- **Description**: PERF-009 (batch_size=20) 적용 후에도 여전히 메모리 초과 발생
- **Solution Applied**:
  - [x] 모든 embedding batch_size를 5로 추가 감소
  - [x] LLM 캐시 max_size를 50으로 추가 감소
- **Created**: 2026-01-21
- **Completed**: 2026-01-21
- **Notes**: 문제 지속 시 Render 인스턴스 업그레이드 필요 ($15/월 for 1GB RAM)

---

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
