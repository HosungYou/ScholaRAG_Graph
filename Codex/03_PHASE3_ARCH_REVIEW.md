# Phase 3 Architecture Review (Frontend Graph + Backend/DB)

## 목표

코어 기능을 유지하면서, 그래프 표현 품질과 질의 신뢰성을 동시에 높이기 위한 실행 항목을 코드 위치 기준으로 확정한다.

## A. Frontend Knowledge Graph 구조 리뷰

### 대상 파일

- `frontend/components/graph/KnowledgeGraph3D.tsx`
- `frontend/components/graph/Graph3D.tsx`
- `frontend/components/graph/GapPanel.tsx`
- `frontend/components/graph/EdgeContextModal.tsx`
- `frontend/hooks/useGraphStore.ts`
- `frontend/lib/layout.ts`

### 현재 강점

1. 뷰 모드 분리(3D/topic/gaps/temporal) 구조 존재
2. GAP 분석 UI와 추천 논문 흐름이 이미 연결됨
3. import 신뢰성 지표를 완료 화면에서 보여줄 수 있게 됨

### 보강 필요점

1. 질의 유형 기반 뷰 라우팅 규칙이 명시적으로 없음
2. low-trust edge 가시화 강도가 뷰별로 일관되지 않음
3. 관계 근거(provenance) 접근이 탐색 동선의 기본값이 아님

### 실행 항목

1. `useGraphStore`에 `queryIntent -> recommendedViewMode` 매핑 추가
2. `Graph3D`에서 low-trust edge 시각 규칙(두께/투명도/색상) 표준화
3. `EdgeContextModal` 우선 노출 조건 강화(근거 없는 관계 경고)

## B. Backend 및 DB 아키텍처 리뷰

### 대상 파일

- `backend/routers/graph.py`
- `backend/agents/query_execution_agent.py`
- `backend/agents/reasoning_agent.py`
- `backend/graph/graph_store.py`
- `backend/importers/*`

### 현재 강점

1. concept-centric 추출/관계/갭 분석 경로가 작동함
2. import 단계에서 Entity Resolution 통합됨
3. API 계약에 신뢰성 요약 필드가 포함됨

### 보강 필요점

1. 다중 hop/조인 경로의 성능 계측 기준이 없음
2. 저신뢰 관계를 질의 단계에서 필터링하는 정책이 약함
3. provenance coverage를 응답 정책과 직접 연결하지 않음

### 실행 항목

1. `graph.py` 주요 조회 API에 query timing/row count 로깅 추가
2. `query_execution_agent.py`에 low-trust edge 필터 옵션 도입
3. `reasoning_agent.py` 응답 생성 시 provenance 경고 템플릿 추가

## C. DB 전략 (PostgreSQL 유지 전제)

### 단기 (즉시)

1. 병목 SQL 후보 수집
2. 인덱스/쿼리 힌트 개선
3. 결과 캐시 범위 확정

### 중기

1. read-model/projection 분리(그래프 탐색 전용)
2. 관계 탐색 API와 분석 API 분리

### 장기

1. Native GraphDB 전환 여부를 계측 데이터로 판단
2. 마이그레이션 대상 엔터티/관계 우선순위 정의

## D. Phase 3 완료 기준

1. 그래프 표현 규칙 문서화 + 코드 반영 1차 완료
2. 백엔드 질의 신뢰성 정책(저신뢰 필터/근거 경고) 반영
3. DB 병목 계측 지표 1세트 수집 가능

## E. 실행 순서 (Phase 3 내부)

1. 표현 규칙 구현: `useGraphStore` + `Graph3D`
2. 근거 우선 UX 구현: `EdgeContextModal` + 관련 패널
3. 백엔드 필터/경고 반영: `query_execution_agent` + `reasoning_agent`
4. SQL 계측 반영: `graph.py`

## F. 실행 상태 (2026-02-08)

- 완료: `useGraphStore` intent 기반 view mode 라우팅 + 테스트
- 완료: `Graph3D` low-trust edge 시각 규칙(두께/색상) 반영
- 완료: `EdgeContextModal` 저신뢰/무근거 경고 배너 반영
- 완료: `query_execution_agent` low-trust 필터(search/retrieve/gap) 반영
- 완료: `reasoning_agent` provenance 기반 Reliability note 반영
- 완료: `graph.py` 주요 조회 API query timing/row count 로깅 반영
