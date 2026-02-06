# Release Notes - v0.11.1 Production Bug Fixes

**Release Date**: 2026-02-06
**Type**: Patch (stability + production bug fixes)

---

## 1. Summary

이번 릴리즈는 프로덕션 환경에서 발견된 5가지 핵심 버그를 수정하고, 메모리 안정화 가드레일을 포함합니다.

**프로덕션 버그 수정 (5건)**:
1. [P0] LLM 채팅 - GraphStore 초기화 실패 → 갭 분석 불가
2. [P0] 연구 갭 미탐지 - 임베딩 없을 때 갭 분석 건너뜀
3. [P1] Topics 탭 시각적으로 보이지 않음
4. [P1] 노드 호버 시 물리 시뮬레이션 떨림
5. [P2] UI 패널 드래그 이동 불가

**메모리 안정화 (기존 패치 포함)**:
- Visualization edge cap, centrality cache LRU, gap auto-refresh 단일 시도

---

## 2. Production Bug Fixes

### 2.1 [P0] GraphStore 초기화 + 갭 분석 에이전트

**문제**: `chat.py`에서 `GraphStore(db=db)` 초기화 예외를 `logger.warning`으로 무시 → 오케스트레이터가 `graph_store=None`으로 생성 → 채팅에서 "graph store is currently unavailable" 반환

**수정**:
- `chat.py`: `logger.warning` → `logger.error` + `traceback.format_exc()` 상세 로깅
- `query_execution_agent.py`: 스텁 구현을 실제 DB 쿼리로 교체
  - `structural_gaps` 테이블에서 탐지된 갭 조회
  - `entities` + `relationships` JOIN으로 저빈도 개념 조회 (HAVING COUNT <= 2)
  - `entity_type = 'Method'` 필터로 방법론 갭 조회
  - 갭 데이터 기반 맞춤 추천 생성

**Files**:
- `backend/routers/chat.py`
- `backend/agents/query_execution_agent.py`

### 2.2 [P0] 임베딩 실패 시 TF-IDF 폴백

**문제**: OpenAI API 키 없거나 실패 시 개념이 임베딩 없이 저장 → 갭 탐지 쿼리 `WHERE embedding IS NOT NULL` → 적격 개념 0개 → 갭 미탐지

**수정**:
- `zotero_rdf_importer.py`: 임베딩 실패 `logger.warning` → `logger.error` 격상 + 프론트엔드 상태 업데이트
- `zotero_rdf_importer.py`: 임베딩 개념 < 10개 시 TF-IDF 폴백
  - 전체 개념 재조회 (임베딩 필터 없이)
  - `TfidfVectorizer(max_features=100, stop_words='english')` 기반 pseudo-embedding 생성
- `graph.py`: 갭 새로고침 엔드포인트에 TF-IDF 폴백 경로 추가
  - `no_gaps_reason` 필드: `"insufficient_concepts"` 또는 `"embedding_unavailable"`

**Files**:
- `backend/importers/zotero_rdf_importer.py`
- `backend/routers/graph.py`

### 2.3 [P1] Topics 탭 가시성 개선

**문제**: 탭 바 배경 `bg-ink/5` (5% 불투명도) → 거의 안 보임, 비활성 탭 `text-muted` → 어두운 배경에서 회색

**수정**:
- 탭 바 배경: `bg-ink/5` → `bg-ink/15` + `border border-ink/20 dark:border-paper/20`
- 비활성 탭 텍스트: `text-muted` → `text-ink/70 dark:text-paper/70`
- 호버 상태 개선

**File**:
- `frontend/components/graph/KnowledgeGraph3D.tsx`

### 2.4 [P1] 노드 호버 떨림 제거

**문제**: d3 물리 시뮬레이션이 `cooldownTicks=1000`, `d3VelocityDecay=0.4`로 설정되어 ~300틱 동안 미세 움직임 지속

**수정**:
- `cooldownTicks`: 1000 → 200 (빠른 안정화)
- `d3VelocityDecay`: 0.4 → 0.75 (강한 감쇠)
- `onEngineStop`: 모든 노드를 `fx/fy/fz`로 고정하여 완전 동결

**File**:
- `frontend/components/graph/Graph3D.tsx`

### 2.5 [P2] DraggablePanel 드래그 이동

**문제**: GapPanel, CentralityPanel, ClusterPanel, InsightHUD 모두 고정 위치 → 겹침 발생, 이동 불가

**수정**:
- 새 `DraggablePanel` 컴포넌트 생성
  - `mousedown` → `mousemove` → `mouseup` 기반 드래그
  - `localStorage` 위치 저장 (키: `panel-pos-{projectId}-{panelId}`)
  - 화면 경계 제한 (viewport clamping)
  - `DragHandle` 시각적 드래그 표시
- GapPanel, InsightHUD, KnowledgeGraph3D에 DraggablePanel 래퍼 적용

**Files**:
- `frontend/components/ui/DraggablePanel.tsx` (신규)
- `frontend/components/graph/GapPanel.tsx`
- `frontend/components/graph/InsightHUD.tsx`
- `frontend/components/graph/KnowledgeGraph3D.tsx`

---

## 3. Memory Stabilization (Earlier Patch)

### 3.1 Backend - Graph API Memory Guard
- `max_edges` 파라미터 추가 (기본값 15000, 범위 1000~50000)

### 3.2 Backend - Centrality Cache Bounding
- LRU 캐시 최대 20 엔트리

### 3.3 Frontend - Gap Auto-Refresh Single Attempt
- 동일 `projectId`에 대해 세션 내 1회만 auto-refresh

### 3.4 Test Environment Stabilization
- `requirements-dev.txt` 의존성 상속 정리
- `@types/jest` devDependency 추가

---

## 4. Documentation Updates

- SDD v0.11.1 버전 업데이트 + 변경 로그 추가
  - `DOCS/architecture/SDD.md`
- TDD v0.11.1 회귀 설계 섹션 5.7 추가 + 테스트 실행 정책 업데이트
  - `DOCS/testing/TDD.md`

---

## 5. Verification Status

- `python3 -m py_compile`: 4개 백엔드 파일 모두 통과
  - `chat.py`, `query_execution_agent.py`, `zotero_rdf_importer.py`, `graph.py`
- `npm run build`: 프론트엔드 빌드 성공 (타입 에러 없음)

---

## 6. Deployment Checklist (Manual)

1. Git commit + push to main
2. Backend: Render Dashboard → `scholarag-graph-docker` → Manual Deploy → Deploy latest commit
3. 배포 후 검증:
   - `GET /health`
   - 채팅에서 "연구 갭 분석" 질문 → DB 데이터 기반 응답 확인
   - Research Gaps 패널 → 갭 탐지 표시 확인
   - Topics 탭 가시성 확인
   - 노드 호버 떨림 없음 확인
   - 패널 드래그 이동 확인

---

## 7. Changed Files Summary

| File | Change Type | Issue |
|------|------------|-------|
| `backend/routers/chat.py` | Modified | #1 GraphStore init |
| `backend/agents/query_execution_agent.py` | Modified | #1 Gap analysis agent |
| `backend/importers/zotero_rdf_importer.py` | Modified | #2 TF-IDF fallback |
| `backend/routers/graph.py` | Modified | #2 Gap refresh TF-IDF |
| `frontend/components/graph/KnowledgeGraph3D.tsx` | Modified | #3 Tab visibility, #5 DraggablePanel |
| `frontend/components/graph/Graph3D.tsx` | Modified | #4 Physics freeze |
| `frontend/components/ui/DraggablePanel.tsx` | **New** | #5 Draggable panels |
| `frontend/components/graph/GapPanel.tsx` | Modified | #5 DragHandle |
| `frontend/components/graph/InsightHUD.tsx` | Modified | #5 DragHandle |
| `DOCS/architecture/SDD.md` | Modified | Documentation |
| `DOCS/testing/TDD.md` | Modified | Documentation |
