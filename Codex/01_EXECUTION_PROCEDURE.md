# Execution Procedure (Core-Preserving Reliability Track)

## 목적

코어 기능(학술 개념 중심 GraphRAG, GAP 분석, 관계 시각화)을 유지한 상태로 신뢰성(정합성, 근거성, 재현성)을 강화한다.

## 단계별 절차

### Phase 0. 베이스라인 고정

- 입력
  - 현재 워킹트리 상태
  - 기존 계획 문서 (`DOCS/plans/*`)
  - 구현 요약 (`IMPLEMENTATION_SUMMARY.md`)
- 수행
  - 현재 구현/테스트 상태 점검
  - 이미 적용된 항목과 미적용 항목 분리
- 출력
  - 실행 로그 초기화
  - 단계별 체크리스트 확정
- 완료 기준
  - "무엇이 이미 됐고 무엇이 남았는지"가 파일 단위로 명시됨

### Phase 1. 신뢰성 파이프라인 정착 (Importer + API)

- 입력
  - ScholaRAG/PDF/Zotero importer 경로
  - Entity Resolution 서비스
- 수행
  - Entity Resolution 공통 적용
  - `reliability_summary`를 import API 응답으로 표준화
- 출력
  - importer 통계 + API 계약 반영
- 완료 기준
  - import status/jobs 응답에서 신뢰성 요약 필드 확인 가능

### Phase 2. 프론트엔드 표현 계층 연결

- 입력
  - import status/jobs API 응답
  - import 진행 UI/타입 정의
- 수행
  - 타입 안전성 정비 (`ImportJob`, `ImportReliabilitySummary`)
  - 완료 화면에서 신뢰성 지표 노출
  - 완료 후 project 이동 경로 안정화
- 출력
  - 사용자 가시성 확보(정규화율/근거커버리지/저신뢰 엣지)
- 완료 기준
  - 프론트에서 신뢰성 카드가 실제 API 데이터로 렌더링됨

### Phase 3. 그래프 표현/아키텍처 정교화

- 입력
  - 3D 그래프 뷰, GAP 패널, 관계근거 모달
  - 백엔드 graph/query/agent 경로
- 수행
  - 뷰 라우팅 기준 정리(질의 유형별: 탐색/추적/갭)
  - 근거 없는 관계의 표시/필터링 정책 고정
  - DB 병목 구간(다중 hop, 조인 집중) 계측 포인트 설정
- 출력
  - 표현 방법론 + 아키텍처 보강안
- 완료 기준
  - SDD 기준으로 구현 우선순위와 변경 지점 확정

### Phase 4. 도메인 특화 Entity Resolution 고도화

- 입력
  - 학술 도메인 온톨로지
  - 동의어/약어/동형이의어 사례
- 수행
  - canonical 규칙 + alias 정책 확정
  - 약어 문맥 해소(문서/섹션 provenance 기반) 추가
  - 배치 처리 전략(임베딩 후보군 + LLM 확정) 적용
- 출력
  - 중복 노드 감소, 연결성 개선
- 완료 기준
  - canonicalization rate, merge count, 오병합률 지표 추적 가능

### Phase 5. Semantic Scholar 연계 운영화

- 입력
  - Gap 기반 추천 로직
  - Semantic Scholar adapter
- 수행
  - 실패/429 대응 표준화
  - 추천근거(쿼리/브리지 컨셉) 기록
- 출력
  - GAP→논문탐색 루프 운영 지표
- 완료 기준
  - 사용자 질문에서 갭-브리지-추천 결과를 재현 가능하게 제공

### Phase 6. E2E/시각회귀 + PR Triage 자동화

- 입력
  - Graph3D/KnowledgeGraph3D/GapPanel/ImportProgress 핵심 시나리오
  - CI 워크플로우 + PR 템플릿
- 수행
  - Playwright 상호작용 회귀(`pin/unpin`, `camera reset`, `gap focus`) 추가
  - Playwright 시각 baseline 추가(4개 컴포넌트 시나리오)
  - snapshot triage 라벨/체크리스트 자동 게이트 추가
- 출력
  - 브라우저 기반 회귀 테스트와 PR triage 자동 판정 루프
- 완료 기준
  - `make test-frontend-e2e`, `make test-frontend-visual` 통과
  - PR에서 snapshot 변경 시 triage 요건 미충족이면 CI 실패

## 진행 순서 규칙

1. 각 Phase 시작 전에 `02_EXECUTION_LOG.md`에 시작 기록
2. 코드 변경 후 테스트/검증 명령을 로그에 남김
3. 완료 기준을 통과한 경우에만 다음 Phase로 이동
4. 실패 시 원인/대응안을 로그에 남기고 같은 Phase에서 재시도

## 현재 상태(2026-02-08)

- Phase 0: 완료
- Phase 1: 완료(백엔드 반영됨)
- Phase 2: 완료(프론트 타입/표시/테스트 인프라 정리 반영)
- Phase 3: 완료(뷰 라우팅/저신뢰 시각 규칙/근거 경고/쿼리 계측 반영)
- Phase 4: 완료(약어/표기 변형 + homonym + batch/LLM 확정 + 오병합 샘플링 지표 반영)
- Phase 5: 완료(429/Retry-After + GAP 체인 구조화 로그 + gap_id 재현 리포트 export 반영)
- Phase 6: 완료(Playwright E2E/visual + snapshot triage CI/PR 자동화 반영)
- 통합 회귀 검증: 완료(`backend/venv/bin/pytest` 기준)
- 표준 실행 진입점: 완료(`Makefile` 기반 `make test-backend-core`, `make test-frontend-core`)
