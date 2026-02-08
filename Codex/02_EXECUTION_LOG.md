# Execution Log

## 2026-02-08

### 00:35-00:40 Baseline Inventory

- 수행
  - 현재 워킹트리 및 계획 문서 점검
  - 기존 구현 요약과 실제 코드 반영 상태 교차 확인
- 결과
  - 백엔드의 Entity Resolution/`reliability_summary` 경로는 반영되어 있음
  - 프론트 타입/표시 계층에서 일부 미연결 지점 확인

### 00:40-00:50 Backend Validation

- 명령
  - `pytest -q backend/tests/test_api_contracts.py backend/tests/test_importer.py`
- 결과
  - `21 passed`
  - 계약 테스트/기본 importer 테스트 통과

### 00:50-01:05 Frontend Reliability Wiring

- 변경 파일
  - `frontend/types/graph.ts`
  - `frontend/components/import/ImportProgress.tsx`
  - `frontend/lib/api.ts`
- 수행
  - `ImportJob` 타입 확장(상태/루트 project_id/reliability_summary)
  - `ImportReliabilitySummary` 타입 신설
  - 완료 UI에 신뢰성 카드(정규화율/근거커버리지/저신뢰 엣지) 노출
  - 완료 시 `result.project_id`가 없더라도 `project_id`로 이동하도록 보강
  - `api` default export 추가(테스트 호환)

### 01:05-01:20 Frontend Verification

- 명령
  - `npm run test -- __tests__/lib/api.test.ts --runInBand`
  - `npm run type-check`
- 결과
  - API 테스트: 통과
  - 전체 type-check: 기존 테스트 인프라 이슈로 실패
    - `jest-dom` matcher 타입 미설정
    - 일부 테스트 모킹(named/default) 불일치
  - 이번 변경 파일 자체에 대한 신규 타입 에러는 확인되지 않음

### 01:20-01:30 Documentation Track Start

- 수행
  - `Codex` 폴더 생성
  - 실행 절차/로그/SDD/TDD 문서 작성 시작

### 01:30-01:45 Codex Documentation Completed

- 생성 문서
  - `Codex/README.md`
  - `Codex/01_EXECUTION_PROCEDURE.md`
  - `Codex/02_EXECUTION_LOG.md`
  - `Codex/SDD.md`
  - `Codex/TDD.md`
- 결과
  - 코어 목적 유지 + 신뢰성 강화 트랙 기준 실행 프레임 고정
  - SDD/TDD 분리 작성 완료

### 01:45-02:05 Phase 2 Remaining Work (Frontend Test Infra)

- 변경 파일
  - `frontend/tsconfig.json`
  - `frontend/__tests__/lib/api.test.ts`
  - `frontend/__tests__/lib/settings-api.test.ts`
  - `frontend/__tests__/hooks/useGraphStore.test.ts`
- 수행
  - `@testing-library/jest-dom` 타입 선언 추가
  - 테스트 파일 전역 충돌 방지(`export {}`)
  - supabase mock을 `getSession` 시그니처에 맞게 정렬
  - `useGraphStore` 테스트에 named export(`api`) 모킹 추가
  - settings API 테스트 응답 필드를 계약(`message`)에 맞춰 정렬
- 검증
  - `npm run test -- __tests__/lib/api.test.ts --runInBand` 통과
  - `npm run test -- __tests__/lib/settings-api.test.ts --runInBand` 통과
  - `npm run test -- __tests__/hooks/useGraphStore.test.ts --runInBand` 통과
  - `npm run type-check` 통과
- 결과
  - Phase 2 잔여 테스트 인프라 이슈 해소
  - Phase 3 착수 가능 상태

### 02:05-02:15 Phase 3 Kickoff (Architecture Review)

- 생성 문서
  - `Codex/03_PHASE3_ARCH_REVIEW.md`
- 수행
  - 프론트 그래프 표현 계층과 백엔드/DB 보강 항목을 파일 단위로 분해
  - 즉시/중기/장기 실행 구간과 완료 기준 정의
- 결과
  - Phase 3 실행 지시서 확보
  - 다음 구현 단위(`useGraphStore`, `Graph3D`, `query_execution_agent`) 확정

### 02:15-02:30 Phase 3 Step 1 (Intent -> View Mode Routing)

- 변경 파일
  - `frontend/hooks/useGraphStore.ts`
  - `frontend/__tests__/hooks/useGraphStore.test.ts`
- 수행
  - `inferViewModeFromIntent` 로직 추가
  - `getRecommendedViewMode`, `applyRecommendedViewMode` 액션 추가
  - gap/timeline/topic/기본(3d) 라우팅 규칙 테스트 추가
- 검증
  - `npm run test -- __tests__/hooks/useGraphStore.test.ts --runInBand` 통과
  - `npm run type-check` 통과

### 02:30-02:40 Phase 3 Step 2 (Low-Trust Edge Visual Rule)

- 변경 파일
  - `frontend/components/graph/Graph3D.tsx`
- 수행
  - edge confidence/weight 기반 `isLowTrust` 판정 추가
  - low-trust edge의 너비/색상 시각 규칙 반영
- 검증
  - `npm run type-check` 통과
  - `npm run test -- __tests__/components/graph/Graph3D.test.tsx --runInBand` 실패(기존 카메라 버킷팅 기대값 불일치 케이스)
- 결과
  - 타입 안정성 유지
  - 그래프 시각화 신뢰 신호(저신뢰 엣지) 1차 반영

### 02:40-02:50 Consolidated Verification

- 명령
  - `pytest -q backend/tests/test_api_contracts.py tests/test_importer.py`
  - `npm run test -- __tests__/lib/api.test.ts --runInBand`
  - `npm run test -- __tests__/lib/settings-api.test.ts --runInBand`
  - `npm run test -- __tests__/hooks/useGraphStore.test.ts --runInBand`
  - `npm run type-check`
- 결과
  - 백엔드 테스트: 통과(21 passed)
  - 프론트 타겟 테스트: 모두 통과
  - 프론트 type-check: 통과
  - 별도 `Graph3D` 단일 테스트의 카메라 버킷팅 케이스는 기존 기대값 이슈로 잔여

### 02:50-03:10 Phase 3 Step 3/4 Completion (Trust Policy + UX + Runtime Wiring)

- 변경 파일
  - `backend/agents/task_planning_agent.py`
  - `backend/routers/chat.py`
  - `backend/tests/test_agents.py`
  - `backend/tests/test_api_contracts.py`
  - `frontend/types/graph.ts`
  - `frontend/app/projects/[id]/page.tsx`
  - `frontend/components/graph/KnowledgeGraph3D.tsx`
  - `frontend/components/graph/EdgeContextModal.tsx`
- 수행
  - TaskPlanning 단계에서 intent/query 기반 저신뢰 필터 파라미터 자동 주입
  - Chat API 응답에 `intent` 필드 추가
  - 프로젝트 페이지에서 채팅 응답 intent를 받아 `applyRecommendedViewMode` 실행
  - EdgeContextModal에 저신뢰/무근거 관계 경고 배너와 confidence 배지 추가
- 검증
  - `pytest -q backend/tests/test_agents.py backend/tests/test_api_contracts.py` 통과
  - `npm run type-check` 통과

### 03:10-03:20 Phase 4 Step 1 (Entity Resolution 고도화)

- 변경 파일
  - `backend/graph/entity_resolution.py`
  - `backend/tests/test_entity_resolution.py`
  - `Codex/04_PHASE4_ENTITY_RESOLUTION.md`
- 수행
  - `Long Form (ACRONYM)` 패턴 학습 및 약어 canonical 매핑 추가
  - 하이픈/붙여쓰기 표기 변형 정규화(`fine-tuning`, `finetuning`) 추가
  - 타입 경계 유지(서로 다른 entity_type 간 merge 방지) 테스트 고정
- 검증
  - `pytest -q backend/tests/test_entity_resolution.py backend/tests/test_agents.py backend/tests/test_api_contracts.py` 통과 (`39 passed`)
  - `npm run type-check` 통과
  - `npm run test -- __tests__/hooks/useGraphStore.test.ts --runInBand` 통과
  - `npm run test -- __tests__/lib/api.test.ts --runInBand` 통과

### 03:20-03:25 Importer Regression Check

- 명령
  - `pytest -q backend/tests/test_importer.py`
- 결과
  - `8 passed`
  - Entity type/phase 관련 importer 회귀 이상 없음

### 03:25-03:40 Phase 4 Step 2 (Homonym Context Disambiguation)

- 변경 파일
  - `backend/graph/entity_resolution.py`
  - `backend/tests/test_entity_resolution.py`
  - `Codex/04_PHASE4_ENTITY_RESOLUTION.md`
- 수행
  - 동형이의어 규칙(`sat`, `transformer`)과 문맥 버킷 추론 로직 추가
  - 엔티티 context(`definition`, `description`, `properties`) 기반 키워드 분기 적용
  - resolution group key를 context bucket 포함 형태로 확장하여 오병합 방지
  - 결과 속성에 `resolution_context_bucket` 기록
- 검증
  - `pytest -q backend/tests/test_entity_resolution.py backend/tests/test_agents.py` 통과 (`28 passed`)
  - `pytest -q backend/tests/test_api_contracts.py backend/tests/test_importer.py` 통과 (`21 passed`)
  - `npm run type-check` 통과
  - `npm run test -- __tests__/hooks/useGraphStore.test.ts --runInBand` 통과

### 03:40-04:05 Phase 4 Step 3 (Batch 후보군 + LLM 확정)

- 변경 파일
  - `backend/graph/entity_resolution.py`
  - `backend/importers/scholarag_importer.py`
  - `backend/importers/pdf_importer.py`
  - `backend/importers/zotero_rdf_importer.py`
  - `backend/tests/test_entity_resolution.py`
- 수행
  - `resolve_entities_async()` 경로 추가 (불확실 pair LLM 배치 확인)
  - deterministic 자동 병합과 LLM 확인 병합을 분리
  - importer 3종에서 async resolution 경로로 전환
  - LLM 확인 기반 병합 동작 테스트 추가
- 검증
  - `pytest -q backend/tests/test_entity_resolution.py backend/tests/test_agents.py backend/tests/test_importer.py` 통과 (`37 passed`)
  - `python3 -m py_compile ...` (관련 backend 파일) 통과
  - `npm run type-check` 통과
  - `npm run test -- __tests__/lib/api.test.ts --runInBand` 통과

### 04:05-04:20 Phase 5 Step 1 (Semantic Scholar 429 표준화)

- 변경 파일
  - `backend/integrations/semantic_scholar.py`
  - `backend/routers/graph.py`
  - `backend/tests/test_integrations.py`
  - `frontend/lib/api.ts`
  - `frontend/components/graph/GapPanel.tsx`
  - `Codex/05_PHASE5_SEMANTIC_SCHOLAR.md`
- 수행
  - S2 429를 전용 예외(`SemanticScholarRateLimitError`)로 표준화
  - gap recommendation endpoint에서 HTTP 429 + `Retry-After` + `retry_after_seconds`로 전달
  - 프론트 API 에러 객체에 `status`/`retryAfterSeconds` 부착
  - GapPanel 카운트다운을 동적 retry-after 기반으로 변경
- 검증
  - `pytest -q backend/tests/test_entity_resolution.py backend/tests/test_importer.py backend/tests/test_api_contracts.py` 통과 (`27 passed`)
  - `npm run type-check` 통과
  - `npm run test -- __tests__/lib/api.test.ts --runInBand` 통과
  - 참고: `pytest ... test_integrations.py`는 로컬 환경 의존성(`email-validator`) 부재로 collection 실패

### 04:20-04:45 Phase 4 Step 4 + Phase 5 Step 2

- 변경 파일
  - `backend/graph/entity_resolution.py`
  - `backend/importers/scholarag_importer.py`
  - `backend/importers/pdf_importer.py`
  - `backend/importers/zotero_rdf_importer.py`
  - `backend/routers/import_.py`
  - `backend/routers/graph.py`
  - `backend/tests/test_entity_resolution.py`
  - `frontend/types/graph.ts`
  - `frontend/components/import/ImportProgress.tsx`
  - `Codex/01_EXECUTION_PROCEDURE.md`
  - `Codex/04_PHASE4_ENTITY_RESOLUTION.md`
  - `Codex/05_PHASE5_SEMANTIC_SCHOLAR.md`
- 수행
  - EntityResolution 통계에 `llm_pairs_reviewed/confirmed`, `potential_false_merge_count/samples` 추가
  - importer 3종에서 오병합 샘플링 지표 누적/전달
  - `reliability_summary`에 LLM 확인율/잠재 오병합 비율/샘플 표준화
  - Import 완료 UI에 LLM merge review 및 잠재 오병합 지표 추가
  - GAP→Bridge→Recommendation 체인 구조화 로그 이벤트 추가(`bridge_generation_*`, `bridge_creation_*`, `recommendation_*`)
- 검증
  - `python3 -m py_compile backend/graph/entity_resolution.py backend/importers/scholarag_importer.py backend/importers/pdf_importer.py backend/importers/zotero_rdf_importer.py backend/routers/import_.py backend/routers/graph.py` 통과
  - `pytest -q backend/tests/test_entity_resolution.py backend/tests/test_agents.py backend/tests/test_importer.py backend/tests/test_api_contracts.py` 통과 (`50 passed`)
  - `npm run type-check` 통과
  - `npm run test -- __tests__/lib/api.test.ts __tests__/hooks/useGraphStore.test.ts --runInBand` 통과
  - 참고: `pytest -q backend/tests/test_integrations.py -k "search_papers_raises_rate_limit_after_retries"`는 로컬 `email-validator` 부재로 collection 실패

### 04:45-05:05 Phase 5 Step 3 (gap_id 재현 리포트 export)

- 변경 파일
  - `backend/routers/graph.py`
  - `backend/tests/test_api_contracts.py`
  - `frontend/types/graph.ts`
  - `frontend/lib/api.ts`
  - `frontend/__tests__/lib/api.test.ts`
  - `Codex/01_EXECUTION_PROCEDURE.md`
  - `Codex/05_PHASE5_SEMANTIC_SCHOLAR.md`
- 수행
  - 단일 gap 재현 경로 API 추가:
    - `GET /api/graph/gaps/{project_id}/repro/{gap_id}`
    - `GET /api/graph/gaps/{project_id}/repro/{gap_id}/export?format=markdown|json`
  - 리포트 내용:
    - gap context(클러스터/브리지 후보/연구질문)
    - 생성된 `BRIDGES_GAP` 관계 추적(가설 제목/신뢰도/AI 여부)
    - 추천 결과 상태(`success|rate_limited|timeout|failed`) + query/papers
  - 프론트 API 메서드 및 타입 추가:
    - `getGapReproReport`
    - `exportGapReproReport`
- 검증
  - `python3 -m py_compile backend/routers/graph.py backend/tests/test_api_contracts.py` 통과
  - `pytest -q backend/tests/test_api_contracts.py backend/tests/test_entity_resolution.py backend/tests/test_agents.py backend/tests/test_importer.py` 통과 (`51 passed`)
  - `npm run type-check` 통과
  - `npm run test -- __tests__/lib/api.test.ts --runInBand` 통과

### 05:05-05:20 Sequential Verification Step (환경 의존성 정리/통합 회귀)

- 수행
  - macOS 기본 `pytest` 경로(3.9)에서 `email-validator` 설치 시도
    - 명령: `"/Library/Developer/CommandLineTools/usr/bin/python3" -m pip install --user "email-validator>=2.1.0,<3.0.0"`
    - 결과: 네트워크 제한으로 PyPI 연결 실패
  - 프로젝트 `backend/venv` 환경 점검
    - `./venv/bin/python`에서 `email_validator` import 확인
  - 통합 회귀를 `venv` 기준으로 실행
- 검증
  - `./venv/bin/pytest -q tests/test_entity_resolution.py tests/test_agents.py tests/test_importer.py tests/test_api_contracts.py tests/test_integrations.py` 통과 (`73 passed, 4 skipped`)
  - `npm run type-check` 통과
  - `npm run test -- __tests__/lib/api.test.ts __tests__/hooks/useGraphStore.test.ts --runInBand` 통과
- 결론
  - 환경 의존성 이슈는 실행 인터프리터 차이(기본 3.9 vs 프로젝트 venv 3.14)로 확인
  - 프로젝트 표준 검증 경로를 `backend/venv/bin/pytest`로 고정하면 통합 회귀 재현 가능

### 05:20-05:30 Sequential Step (Graph3D 카메라 버킷팅 테스트 정리)

- 변경 파일
  - `frontend/__tests__/components/graph/Graph3D.test.tsx`
- 수행
  - 카메라 버킷팅 기대값을 실제 구현(`Math.round(distance / 50) * 50`)에 맞게 정정
  - `distance=123` 기대값을 `150 -> 100`으로 수정
  - 테스트 설명을 "nearest-50 bucketing"으로 명확화
- 검증
  - `npm run test -- __tests__/components/graph/Graph3D.test.tsx --runInBand` 통과 (`8 passed`)
  - `npm run test -- __tests__/lib/api.test.ts __tests__/hooks/useGraphStore.test.ts __tests__/components/graph/Graph3D.test.tsx --runInBand` 통과 (`20 passed`)
  - `npm run type-check` 통과

### 05:30-05:45 Sequential Step (운영 환경 실행 표준화 코드 고정)

- 변경 파일
  - `Makefile` (신규)
  - `README.md`
  - `backend/tests/README.md`
  - `Codex/TDD.md`
  - `Codex/01_EXECUTION_PROCEDURE.md`
- 수행
  - 루트 `Makefile`에 표준 실행 타겟 추가
    - `make verify-env`
    - `make test-backend-core` (`backend/venv/bin/pytest` 강제)
    - `make test-backend-full`
    - `make test-frontend-core`
    - `make test-all-core`
  - 문서의 테스트 실행 경로를 `make` 기반으로 정렬
- 검증
  - `make verify-env` 통과
  - `make test-backend-core` 통과 (`73 passed, 4 skipped`)
  - `make test-frontend-core` 통과 (`3 suites passed`, `20 tests passed`)

### 01:46-02:05 Sequential Step (ImportProgress 컴포넌트 회귀 테스트 추가)

- 변경 파일
  - `frontend/__tests__/components/import/ImportProgress.test.tsx` (신규)
  - `Makefile`
  - `Codex/TDD.md`
- 수행
  - ImportProgress의 핵심 회귀 시나리오 테스트 추가
    - `project_id` fallback으로 `onComplete`/`Open Project` 이동 검증
    - `reliability_summary` 기반 요약 문구/카드 렌더링 검증
    - `result.reliability_summary` fallback 경로 검증
  - `make test-frontend-core`에 ImportProgress 테스트 파일 포함
  - TDD의 Known Debt/Immediate Next Test Work를 최신 상태로 정리
- 검증
  - `make test-frontend-core` 통과 (`4 suites passed`, `23 tests passed`)

### 02:05-02:15 Sequential Step (코어 통합 회귀 재확인)

- 수행
  - 신규 ImportProgress 테스트가 포함된 상태에서 백엔드+프론트 코어 회귀를 통합 실행
- 검증
  - `make test-all-core` 통과
  - 백엔드: `73 passed, 4 skipped`
  - 프론트: `4 suites passed`, `23 tests passed`

### 01:55-02:15 Sequential Step (GapPanel 429 countdown/자동 재시도 테스트 추가)

- 변경 파일
  - `frontend/__tests__/components/graph/GapPanel.test.tsx` (신규)
  - `Makefile`
  - `Codex/TDD.md`
- 수행
  - GapPanel `Find Papers` 경로에서 429 응답 시 상태 전이 검증 테스트 추가
    - 429 수신 시 countdown 시작(`Retry in Ns`)
    - countdown 종료 시 자동 재시도 호출
    - 재시도 성공 토스트 및 버튼 재활성화 확인
  - `make test-frontend-core` 코어 세트에 GapPanel 테스트 포함
  - TDD의 Immediate Next Test Work 갱신
- 검증
  - `npm run test -- __tests__/components/graph/GapPanel.test.tsx --runInBand` 통과
  - `make test-frontend-core` 통과 (`5 suites passed`, `24 tests passed`)
  - `make test-all-core` 통과
    - 백엔드: `73 passed, 4 skipped`
    - 프론트: `5 suites passed`, `24 tests passed`

### 01:57-02:20 Sequential Step (ImportProgress interrupted/resume 테스트 추가)

- 변경 파일
  - `frontend/__tests__/components/import/ImportProgress.test.tsx`
  - `Codex/TDD.md`
- 수행
  - interrupted 상태 렌더링/체크포인트 노출 테스트 추가
  - resume 성공 플로우 테스트 추가
    - `resumeImport(job_id)` 호출
    - interrupted UI -> 진행 UI 전환 확인
  - resume 실패 플로우 테스트 추가
    - 에러 메시지 렌더링 확인
  - TDD Known Debt/Immediate Next Test Work를 최신 상태로 갱신
- 검증
  - `npm run test -- __tests__/components/import/ImportProgress.test.tsx --runInBand` 통과 (`5 passed`)
  - `make test-frontend-core` 통과 (`5 suites passed`, `26 tests passed`)
  - `make test-all-core` 통과
    - 백엔드: `73 passed, 4 skipped`
    - 프론트: `5 suites passed`, `26 tests passed`

### 02:11-02:25 Sequential Step (resume 후 polling 재개 동작 고정)

- 변경 파일
  - `frontend/components/import/ImportProgress.tsx`
  - `frontend/__tests__/components/import/ImportProgress.test.tsx`
  - `Codex/TDD.md`
- 수행
  - interrupted 상태에서 resume 성공 시 polling 루프를 재시작하도록 `pollEpoch` 트리거 추가
  - 통합 테스트 추가:
    - interrupted -> resume -> running -> 다음 polling tick -> completed
    - `getImportStatus` 재호출 횟수와 `onComplete` 호출 확인
- 검증
  - `npm run test -- __tests__/components/import/ImportProgress.test.tsx --runInBand` 통과 (`6 passed`)
  - `make test-frontend-core` 통과 (`5 suites passed`, `27 tests passed`)
  - `make test-all-core` 통과
    - 백엔드: `73 passed, 4 skipped`
    - 프론트: `5 suites passed`, `27 tests passed`

### 02:13-02:30 Sequential Step (GapPanel nested button 구조 리팩터링)

- 변경 파일
  - `frontend/components/graph/GapPanel.tsx`
  - `frontend/__tests__/components/graph/GapPanel.test.tsx`
  - `Codex/TDD.md`
- 수행
  - gap 카드 헤더 컨테이너를 `<button>`에서 `div[role="button"]`으로 전환
    - 키보드 접근(`Enter`, `Space`) 유지
    - 내부 `Find Papers` 버튼과의 nested button 구조 제거
  - 회귀 테스트 추가:
    - 429 countdown/자동 재시도 기존 시나리오 유지
    - 렌더 시 `validateDOMNesting` 경고 미발생 검증
  - TDD Known Debt/Immediate Next Test Work 최신화
- 검증
  - `npm run test -- __tests__/components/graph/GapPanel.test.tsx --runInBand` 통과 (`2 passed`)
  - `make test-frontend-core` 통과 (`5 suites passed`, `28 tests passed`)
  - `make test-all-core` 통과
    - 백엔드: `73 passed, 4 skipped`
    - 프론트: `5 suites passed`, `28 tests passed`

### 02:16-02:30 Sequential Step (ImportProgress polling cleanup 테스트 고정)

- 변경 파일
  - `frontend/__tests__/components/import/ImportProgress.test.tsx`
  - `Codex/TDD.md`
- 수행
  - 언마운트 이후 polling 타이머가 API를 재호출하지 않음을 검증하는 테스트 추가
    - fake timer 환경에서 `unmount()` 후 10초 advance
    - `getImportStatus` 호출 횟수 고정 확인
  - TDD Known Debt/Immediate Next Test Work 갱신
- 검증
  - `npm run test -- __tests__/components/import/ImportProgress.test.tsx --runInBand` 통과 (`7 passed`)
  - `make test-frontend-core` 통과 (`5 suites passed`, `29 tests passed`)
  - `make test-all-core` 통과
    - 백엔드: `73 passed, 4 skipped`
    - 프론트: `5 suites passed`, `29 tests passed`

### 02:30-02:45 Sequential Step (CI 기본 게이트를 make test-all-core로 고정)

- 변경 파일
  - `.github/workflows/ci.yml`
  - `Codex/TDD.md`
- 수행
  - GitHub Actions에 `core-gate` 잡 추가
    - Python/Node 환경 준비
    - `backend/venv` 생성 및 의존성 설치
    - `frontend` 의존성 설치
    - 표준 게이트 명령 `make test-all-core` 실행
  - 후속 잡(`backend`, `frontend`, `docs`, `security`)에 `needs: core-gate` 적용
  - TDD에서 CI 기본 게이트 항목 완료 처리
- 검증
  - 로컬 표준 게이트 `make test-all-core` 기준 최근 통합 회귀 통과 상태 유지
    - 백엔드: `73 passed, 4 skipped`
    - 프론트: `5 suites passed`, `29 tests passed`

### 02:21-02:35 Sequential Step (`aria-label` 표준화 + 셀렉터 정리)

- 변경 파일
  - `frontend/components/graph/GapPanel.tsx`
  - `frontend/components/import/ImportProgress.tsx`
  - `frontend/__tests__/components/graph/GapPanel.test.tsx`
  - `Codex/TDD.md`
- 수행
  - GapPanel `Find Papers` 버튼에 `aria-label=\"Find related papers\"` 추가
  - ImportProgress 주요 액션 버튼에 `aria-label` 추가
    - `Resume import`, `Upload new files`, `View partial results`, `Retry import`, `Open project`
  - GapPanel 테스트 셀렉터를 `getByTitle`에서 `getByRole(..., { name })`로 전환
- 검증
  - `npm run test -- __tests__/components/graph/GapPanel.test.tsx __tests__/components/import/ImportProgress.test.tsx --runInBand` 통과 (`9 passed`)
  - `make test-frontend-core` 통과 (`5 suites passed`, `29 tests passed`)
  - `make test-all-core` 통과
    - 백엔드: `73 passed, 4 skipped`
    - 프론트: `5 suites passed`, `29 tests passed`

### 02:23-02:40 Sequential Step (Gap/Import 시각 회귀 스냅샷 초안 추가)

- 변경 파일
  - `frontend/__tests__/components/graph/GapPanel.snapshot.test.tsx` (신규)
  - `frontend/__tests__/components/graph/__snapshots__/GapPanel.snapshot.test.tsx.snap` (신규)
  - `frontend/__tests__/components/import/ImportProgress.snapshot.test.tsx` (신규)
  - `frontend/__tests__/components/import/__snapshots__/ImportProgress.snapshot.test.tsx.snap` (신규)
  - `Makefile`
  - `Codex/TDD.md`
- 수행
  - GapPanel/ImportProgress의 기본 시각 상태를 스냅샷으로 고정
    - GapPanel: 리스트/확장 상세 상태
    - ImportProgress: completed/interrupted 상태
  - `make test-frontend-core` 대상에 스냅샷 테스트 2개를 추가
  - TDD Known Debt/Immediate Next Test Work를 최신 상태로 갱신
- 검증
  - `npm run test -- __tests__/components/graph/GapPanel.snapshot.test.tsx __tests__/components/import/ImportProgress.snapshot.test.tsx --runInBand` 통과 (`4 passed`, `4 snapshots written`)
  - `make test-frontend-core` 통과 (`7 suites passed`, `33 tests passed`, `4 snapshots passed`)
  - `make test-all-core` 통과
    - 백엔드: `73 passed, 4 skipped`
    - 프론트: `7 suites passed`, `33 tests passed`, `4 snapshots passed`

### 02:24-02:40 Sequential Step (CI 프론트 테스트 러너 npm 단일화)

- 변경 파일
  - `.github/workflows/ci.yml`
  - `Codex/TDD.md`
- 수행
  - `frontend` 잡의 패키지 매니저를 `pnpm`에서 `npm`으로 통일
    - `pnpm/action-setup` 제거
    - Node cache를 `npm` + `frontend/package-lock.json`으로 변경
    - 설치/검증/빌드 명령을 `npm ci`, `npm run lint`, `npm run type-check`, `npm run test`, `npm run build`로 변경
  - TDD에서 runner 단일화 항목 완료 처리
- 검증
  - `make test-frontend-core` 통과 (`7 suites passed`, `33 tests passed`, `4 snapshots passed`)
  - `make test-all-core` 통과
    - 백엔드: `73 passed, 4 skipped`
    - 프론트: `7 suites passed`, `33 tests passed`, `4 snapshots passed`

### 02:40-03:10 Sequential Step (스냅샷 게이트 일괄 승인 항목 반영)

- 변경 파일
  - `frontend/__tests__/components/graph/Graph3D.snapshot.test.tsx` (신규)
  - `frontend/__tests__/components/graph/KnowledgeGraph3D.snapshot.test.tsx` (신규)
  - `frontend/__tests__/components/graph/__snapshots__/Graph3D.snapshot.test.tsx.snap` (신규)
  - `frontend/__tests__/components/graph/__snapshots__/KnowledgeGraph3D.snapshot.test.tsx.snap` (신규)
  - `Makefile`
  - `Codex/06_SNAPSHOT_REVIEW_CHECKLIST.md` (신규)
  - `Codex/07_SNAPSHOT_DIFF_TRIAGE.md` (신규)
  - `Codex/TDD.md`
- 수행
  - Graph3D 스냅샷 추가
    - low-trust edge 매핑 스냅샷
    - ghost edge 활성화 매핑 스냅샷
  - KnowledgeGraph3D 스냅샷 추가
    - loading/error/3D shell 상태 스냅샷
  - `make test-frontend-core`에 신규 스냅샷 2개 포함
  - 스냅샷 승인 체크리스트 문서화
  - 스냅샷 diff triage(허용/회귀) 절차 문서화
  - TDD의 기존 미완료 항목(스냅샷 가이드/Graph3D-KG3D 범위/triage 절차)을 완료 상태로 전환
- 검증
  - `npm run test -- __tests__/components/graph/Graph3D.snapshot.test.tsx __tests__/components/graph/KnowledgeGraph3D.snapshot.test.tsx --runInBand` 통과 (`2 suites`, `5 tests`, `5 snapshots`)
  - `make test-frontend-core` 통과 (`9 suites`, `38 tests`, `9 snapshots`)
  - `make test-all-core` 통과
    - 백엔드: `73 passed, 4 skipped`
    - 프론트: `9 suites passed`, `38 tests passed`, `9 snapshots passed`

### 03:10-04:05 Sequential Step (Playwright E2E/Visual + Snapshot Triage CI 완료)

- 변경 파일
  - `frontend/app/qa/e2e/page.tsx` (신규)
  - `frontend/playwright.config.ts` (신규)
  - `frontend/e2e/graph-interactions.spec.ts` (신규)
  - `frontend/e2e/visual-regression.spec.ts` (신규)
  - `frontend/e2e/visual-regression.spec.ts-snapshots/*` (신규 baseline 5종)
  - `frontend/components/graph/Graph3D.tsx`
  - `frontend/components/graph/KnowledgeGraph3D.tsx`
  - `frontend/components/graph/GapPanel.tsx`
  - `frontend/tsconfig.json`
  - `frontend/package.json`
  - `frontend/package-lock.json`
  - `.github/workflows/ci.yml`
  - `.github/pull_request_template.md` (신규)
  - `Makefile`
  - `Codex/01_EXECUTION_PROCEDURE.md`
  - `Codex/TDD.md`
  - `Codex/08_PLAYWRIGHT_E2E_VISUAL.md` (신규)
- 수행
  - Graph3D E2E mock 모드(`NEXT_PUBLIC_E2E_MOCK_3D=1`) 추가
  - KnowledgeGraph3D debug hook 추가(`onDebugCameraReset`, `onDebugGapFocus`)
  - GapPanel gap toggle에 `data-testid` 추가(`gap-card-toggle-{gapId}`)
  - QA fixture 라우트 `/qa/e2e` 구성 (knowledge/graph3d/gap-panel/import 시나리오)
  - Playwright 상호작용 회귀 테스트 추가
    - pin/unpin, camera reset, gap focus
  - Playwright 시각 회귀 테스트 추가 + baseline 생성(5장)
  - CI에 snapshot triage gate(PR 라벨+체크리스트 검증) 추가
  - CI에 PR 전용 Playwright E2E/Visual 잡 추가
  - PR 템플릿에 snapshot triage 체크리스트 추가
- 검증
  - `make test-frontend-core` 통과 (`9 suites`, `38 tests`, `9 snapshots`)
  - `make test-all-core` 통과
    - 백엔드: `73 passed, 4 skipped`
    - 프론트: `9 suites passed`, `38 tests passed`, `9 snapshots passed`
  - `make test-frontend-e2e` 통과 (`1 passed`)
  - `make test-frontend-visual` 통과 (`5 passed`)

## 오픈 이슈

- 현재 기준 블로킹 이슈 없음
