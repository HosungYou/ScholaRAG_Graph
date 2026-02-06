# Test Design Document (TDD)

**Project**: ScholaRAG_Graph
**Version**: 0.11.1
**Last Updated**: 2026-02-06  
**Status**: Active  
**Document Type**: Test Design & Verification Specification

---

## 1. Purpose

본 문서는 ScholaRAG_Graph의 테스트 설계 기준을 정의합니다.
핵심 목적은 다음과 같습니다.

1. SDD(Software Design Document)와 테스트 전략의 추적 가능성 확보
2. Unit → Integration → E2E 3계층 검증 체계 표준화
3. 안정성 이슈(재진입, 메모리, 백그라운드 작업) 회귀 테스트 강화

---

## 2. Scope

### In Scope
- Backend API/Service/Importer 테스트
- Frontend component/store/API client 테스트
- 운영 안정성 회귀 테스트 (reopen, polling, background jobs)
- CI/CD 게이팅 기준

### Out of Scope
- 성능 벤치마크의 절대 수치 보장
- 외부 인프라(Render/Vercel/Supabase) 내부 상태의 완전 재현
- 프로덕션 실데이터 기반 카나리 테스트

---

## 3. Test Architecture

본 프로젝트는 3계층 테스트 구조를 기본으로 사용합니다.

1. Unit
- 목적: 비즈니스 로직/헬퍼 함수의 빠른 검증
- 특징: 외부 I/O 최소화, mocking 기반
- 예시: `backend/tests/test_importer.py`, `frontend/__tests__/hooks/useGraphStore.test.ts`

2. Integration
- 목적: DB/라우터/서비스 간 경계 통합 검증
- 특징: async DB, API route, importer 흐름 검증
- 예시: `backend/tests/test_api_integration.py`, `backend/tests/test_graph_router.py`

3. E2E
- 목적: 사용자 워크플로우 관점의 종단 검증
- 특징: API-UI-상태 전이 포함
- 예시: `DOCS/testing/infranodus-e2e-test-cases.md` (manual E2E 기준)

---

## 4. SDD-TDD Traceability

| SDD 영역 | 설계 포인트 | 테스트 유형 | 테스트 자산 |
|---|---|---|---|
| Multi-Agent Pipeline | 의도 분류/응답 생성 | Unit/Integration | `backend/tests/test_agents.py` |
| Graph Router | 탐색/분석/evidence 조회 | Integration | `backend/tests/test_graph_router.py` |
| Import Pipeline | PDF/Zotero import 상태 전이 | Unit/Integration | `backend/tests/test_importer.py`, `backend/tests/test_zotero_rdf_importer.py` |
| Frontend Graph UX | 3D 렌더/상태 갱신 | Unit (component) | `frontend/__tests__/components/graph/Graph3D.test.tsx` |
| Auth/Policy | 접근 제어 | Unit/Integration | `backend/tests/test_auth.py`, `backend/tests/test_auth_policies.py` |
| InfraNodus Features | Gap/Evidence/Temporal UX | E2E | `DOCS/testing/infranodus-e2e-test-cases.md` |
| Visualization API | max_nodes 확대/ORDER BY 우선순위 | Integration | `backend/tests/test_graph_router.py` |
| Zotero Gap Detection | import 후 clustering/gap/centrality | Integration | `backend/tests/test_zotero_rdf_importer.py` |
| Evidence AI Fallback | LLM 기반 관계 설명 생성 | Unit/Integration | `backend/tests/test_graph_router.py` |
| Gap Panel UX | 리사이즈/UUID 라벨 처리 | Unit (component) | `frontend/__tests__/components/graph/GapPanel.test.tsx` |
| Chat Dynamic Questions | 그래프 데이터 기반 질문 생성 | Unit (component) | `frontend/__tests__/components/chat/ChatInterface.test.tsx` |
| Hover Debounce | 50ms 디바운스/ref 기반 최적화 | Unit (component) | `frontend/__tests__/components/graph/Graph3D.test.tsx` |

---

## 5. v0.10.2 Regression Design

### 5.1 Backend Stability

1. Import progress update backpressure
- 대상: `backend/routers/import_.py`
- 목적: progress callback 폭주 시 task 누적 방지
- 전략:
  - 콜백 1000회 burst를 모의하고 update 호출 수가 bounded/coalesced 되는지 검증
  - terminal transition 시 `flush_and_close()`가 final progress를 반영하는지 확인

2. Checkpoint write serialization
- 대상: `backend/routers/import_.py`
- 목적: Zotero resume checkpoint 저장이 순차적으로 반영되는지 검증
- 전략:
  - paper_id 순서가 뒤섞인 이벤트 입력 시 queue 기반 직렬 처리 보장 확인

3. Maintenance lifecycle
- 대상: `backend/main.py`
- 목적: 주기 정리 및 shutdown cleanup 동작 검증
- 전략:
  - quota flush, legacy job cleanup, old job cleanup 호출 여부 검증
  - 예외 발생 시 앱 종료가 중단되지 않는지 검증

### 5.2 Frontend Stability

1. Import polling single-flight
- 대상: `frontend/components/import/ImportProgress.tsx`
- 목적: 중복 polling 및 hidden-tab 불필요 호출 감소
- 전략:
  - in-flight 동안 추가 요청 미발생
  - `document.visibilityState='hidden'`에서 polling 지연 확인

2. Status polling single-flight
- 대상: `frontend/components/graph/StatusBar.tsx`
- 목적: 상태 조회의 interval 폭주/중복 호출 방지
- 전략:
  - 루프 기반 polling에서 한 번에 1요청만 진행되는지 검증

3. Graph3D interval budget
- 대상: `frontend/components/graph/Graph3D.tsx`
- 목적: 고빈도 interval 완화로 CPU/메모리 부담 감소
- 전략:
  - 위치 저장/카메라 체크 주기 및 hidden-tab skip 동작 검증

---

### 5.5 v0.11.0 Regression Design

#### 5.5.1 Backend

1. Visualization API max_nodes + ORDER BY
- 대상: `backend/routers/graph.py` (visualization endpoint)
- 목적: 기본 max_nodes=1000 동작 확인, academic entity 우선 ORDER BY 검증
- 전략:
  - 기본 호출 시 7개 entity type 반환 확인
  - Paper/Author가 Concept/Method/Finding보다 후순위인지 검증
  - max_nodes=5000 상한 동작 확인

2. Zotero importer gap detection
- 대상: `backend/importers/zotero_rdf_importer.py`
- 목적: import 완료 후 gap analysis 자동 실행 확인
- 전략:
  - 10개 이상 concept 추출 시 GapDetector 호출 확인
  - concept_clusters 테이블에 클러스터 저장 확인
  - structural_gaps 테이블에 gap 저장 확인
  - centrality 메트릭(degree, betweenness, pagerank) 업데이트 확인

3. Relationship evidence AI fallback
- 대상: `backend/routers/graph.py` (evidence endpoint)
- 목적: text evidence 없을 때 AI explanation 생성 확인
- 전략:
  - CO_OCCURS_WITH 관계에 대해 통계 기반 설명 반환 확인
  - LLM provider 사용 가능 시 AI explanation 생성 확인
  - ai_explanation 필드가 응답에 포함되는지 확인

#### 5.5.2 Frontend

1. Gap Panel resize
- 대상: `frontend/components/graph/GapPanel.tsx`
- 목적: 드래그 리사이즈 동작 검증
- 전략:
  - 마우스 드래그로 패널 너비 변경 가능 확인 (256-500px 범위)
  - 최소화/복원 시 너비 유지 확인

2. Chat dynamic questions
- 대상: `frontend/components/chat/ChatInterface.tsx`
- 목적: graphStats 기반 동적 질문 생성 확인
- 전략:
  - graphStats prop 전달 시 맥락 기반 질문 표시 확인
  - topConcepts 정보 활용 여부 확인

3. Hover debounce
- 대상: `frontend/components/graph/Graph3D.tsx`
- 목적: 노드 호버 시 jitter 제거 확인
- 전략:
  - 빠른 호버 이동 시 50ms 디바운스 동작 확인
  - hoveredNodeRef를 통한 중복 업데이트 방지 확인

4. View mode tab UI + panel layout
- 대상: `frontend/components/graph/KnowledgeGraph3D.tsx`
- 목적: 탭 스타일 뷰 전환 및 패널 겹침 방지
- 전략:
  - 3D/Topics/Gaps 탭 전환 동작 확인
  - 우측 패널들이 flex 레이아웃으로 겹침 없이 표시 확인

5. Cluster label UUID detection
- 대상: `frontend/components/graph/GapPanel.tsx`, `GapQueryPanel.tsx`
- 목적: UUID 형태 라벨을 키워드 이름으로 대체 확인
- 전략:
  - UUID 패턴 감지 시 concept_names fallback 동작 확인

---

### 5.6 v0.11.1 Memory Stabilization Regression Design

1. Visualization edge cap
- 대상: `backend/routers/graph.py` (`/api/graph/visualization/{project_id}`)
- 목적: 대규모/고밀도 그래프에서 응답 메모리 상한 확보
- 전략:
  - `max_edges` 기본값(15000) 적용 여부 검증
  - `max_edges` 파라미터 조정 시 edge 개수 상한 준수 확인

2. Centrality cache bound
- 대상: `backend/graph/centrality_analyzer.py`
- 목적: 프로젝트 수 증가 시 중앙성 캐시 무한 증가 방지
- 전략:
  - 20개 초과 cache key 입력 후 LRU eviction 동작 확인
  - 동일 key 재호출 시 cache hit + recency 갱신 확인

3. Gap auto-refresh single-attempt
- 대상: `frontend/hooks/useGraphStore.ts`
- 목적: 프로젝트 재진입 시 `/gaps/{id}/refresh` 과호출 방지
- 전략:
  - 동일 projectId에서 auto-refresh 1회만 실행되는지 검증
  - gap refresh 실패 시에도 무한 재시도되지 않는지 확인

---

### 5.7 v0.11.1 Production Bug Fix Regression Design

#### 5.7.1 Backend

1. GraphStore initialization + gap analysis agent
- 대상: `backend/routers/chat.py`, `backend/agents/query_execution_agent.py`
- 목적: GraphStore 초기화 실패 시 상세 로깅 확인, 갭 분석이 실제 DB 쿼리 기반으로 동작 확인
- 전략:
  - GraphStore 초기화 예외 시 `logger.error` + traceback 출력 확인
  - `graph_store` 미초기화 상태에서도 direct DB fallback 경로로 갭 질의가 수행되는지 확인
  - `_execute_gap_analysis()`가 `structural_gaps` 테이블에서 갭 조회 확인
  - `entities` + `relationships` JOIN으로 저빈도 개념 조회 확인
  - `entity_type = 'Method'` 필터로 방법론 갭 조회 확인
  - 갭 데이터 기반 맞춤 추천 생성 확인 (하드코딩 아님)

2. Embedding TF-IDF fallback
- 대상: `backend/importers/zotero_rdf_importer.py`, `backend/routers/graph.py`
- 목적: 임베딩 없을 때 TF-IDF 폴백으로 갭 탐지 가능 확인
- 전략:
  - 임베딩 실패 시 `logger.error` 격상 확인
  - `concepts_for_gap < 10` 시 TF-IDF 벡터 생성 확인
  - `TfidfVectorizer(max_features=64, dtype=float32)` 기반 pseudo-embedding 생성 확인
  - TF-IDF 경로에서 concept cap(1200) 적용 확인
  - TF-IDF 폴백 경로에서 갭 새로고침 정상 동작 확인
  - `no_gaps_reason` 필드가 `"insufficient_concepts"` 또는 `"embedding_unavailable"` 반환 확인

#### 5.7.2 Frontend

1. Topics 탭 가시성
- 대상: `frontend/components/graph/KnowledgeGraph3D.tsx`
- 목적: 탭 바가 시각적으로 명확하게 보이는지 확인
- 전략:
  - 탭 바 배경 `bg-ink/15` + `border border-ink/20` 적용 확인
  - 비활성 탭 텍스트 `text-ink/70 dark:text-paper/70` 적용 확인
  - 3D/Topics/Gaps 탭 전환 정상 동작 확인

2. 노드 호버 떨림 제거
- 대상: `frontend/components/graph/Graph3D.tsx`
- 목적: 시뮬레이션 안정화 후 노드 움직임 완전 정지 확인
- 전략:
  - `cooldownTicks=200` 설정 확인
  - `d3VelocityDecay=0.75` 설정 확인
  - `onEngineStop`에서 모든 노드 `fx/fy/fz` 고정 확인
  - 안정화 후 호버 시 시뮬레이션 재가열 미발생 확인

3. DraggablePanel 드래그 이동
- 대상: `frontend/components/ui/DraggablePanel.tsx`, 래핑된 패널들
- 목적: 패널 드래그 이동 및 위치 저장 확인
- 전략:
  - mousedown → mousemove → mouseup 드래그 동작 확인
  - 화면 경계 밖으로 이동 불가 확인 (viewport clamping)
  - `localStorage` 키 `panel-pos-{projectId}-{panelId}` 저장 확인
  - 페이지 새로고침 후 위치 복원 확인
  - GapPanel, InsightHUD에 DragHandle 표시 확인

---

### 5.8 Post-Release Consistency Review (magical-exploring-hamster.md)

1. Plan-to-code consistency
- 대상: v0.11.1 구현 변경 전체
- 목적: 계획 대비 실제 구현 누락/과구현 식별
- 검증 포인트:
  - P0(이슈 4, 5) 기능 경로가 실제 런타임 코드로 연결되는지
  - P1(이슈 1, 2) UX 변경이 시각적/행동적으로 재현되는지
  - P2(이슈 3) 드래그 패널 위치 저장/복원이 프로젝트 단위로 동작하는지

2. Residual risk checks
- 대상: `frontend/components/graph/KnowledgeGraph3D.tsx`, `backend/agents/query_execution_agent.py`
- 목적: 릴리즈 이후 회귀 가능성 최소화
- 검증 포인트:
  - 드래그 패널 default position이 클라이언트 런타임에서 안정적으로 계산되는지
  - Gap analysis 경로에서 DB 미연결/빈 데이터 시 오류 메시지가 구체적으로 노출되는지
  - 기존 테스트 스위트가 새 쿼리/폴백 경로를 최소 1개 이상 커버하는지

---

## 6. Test Execution Policy

### Required Local Checks (for release candidates)

```bash
# Backend syntax (v0.11.1)
python3 -m py_compile backend/routers/graph.py backend/routers/chat.py backend/importers/zotero_rdf_importer.py backend/agents/query_execution_agent.py

# Backend regression tests
pytest -q backend/tests/test_graph_router.py backend/tests/test_zotero_rdf_importer.py

# Frontend changed-file lint (v0.11.1)
cd frontend
npm run -s lint -- --file components/graph/GapPanel.tsx --file components/graph/Graph3D.tsx --file components/graph/KnowledgeGraph3D.tsx --file components/graph/InsightHUD.tsx --file components/ui/DraggablePanel.tsx
```

### Recommended Extended Checks

```bash
# Backend router regression
pytest -q backend/tests/test_graph_router.py

# Frontend related tests
npm run -s test -- --runInBand __tests__/components/graph/Graph3D.test.tsx __tests__/hooks/useGraphStore.test.ts
```

---

## 7. Known Test Environment Gaps

1. Python dependency gap
- 증상: 일부 backend 테스트 실행 시 `email-validator` 누락 오류
- 영향: `backend/tests/test_graph_router.py` 일부 케이스
- 상태: **완화** (`backend/requirements-dev.txt`에서 `-r requirements.txt` 상속)

2. Frontend type environment gap
- 증상: `npm run type-check`에서 Jest global type 미설정 오류
- 영향: `frontend/__tests__/*` 전반
- 상태: **진행 중** (`frontend/package.json`에 `@types/jest` 추가, 로컬 install 필요)

3. Existing test expectation drift
- 증상: 일부 기존 테스트는 현재 코드 동작과 기대값이 불일치
- 영향: 컴포넌트 테스트 일부 케이스 재정렬 필요

---

## 8. Quality Gates

Release note 작성 전 최소 충족 조건:

1. 변경 파일 lint/syntax 통과
2. 해당 기능의 핵심 회귀 테스트 1개 이상 통과
3. known gap을 릴리즈 노트에 명시

---

## 9. Ownership

| Area | Owner | Review Cycle |
|---|---|---|
| Backend test design | Backend Team | 매 릴리즈 |
| Frontend test design | Frontend Team | 매 릴리즈 |
| E2E/Operations test | Platform Team | 월간 |
| TDD 문서 유지보수 | Core Maintainers | 매 릴리즈 |

---

## 10. Related Documents

- `DOCS/architecture/SDD.md`
- `backend/tests/README.md`
- `DOCS/testing/infranodus-e2e-test-cases.md`
- `RELEASE_NOTES_v0.11.1.md`
- `RELEASE_NOTES_v0.11.0.md`
- `RELEASE_NOTES_v0.10.2.md`
