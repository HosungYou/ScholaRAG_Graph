# Codex Execution Workspace

이 폴더는 "코어 기능/목적 유지 + GraphRAG 신뢰성 강화" 실행을 위한 전용 작업 공간이다.

## 문서 구성

- `01_EXECUTION_PROCEDURE.md`
  - 단계별 실행 절차, 입력/출력, 완료 기준
- `02_EXECUTION_LOG.md`
  - 실제 수행 이력(타임스탬프, 결과, 이슈)
- `SDD.md`
  - 시스템 설계 문서(아키텍처/인터페이스/의사결정)
- `TDD.md`
  - 테스트 설계 문서(검증 항목/시나리오/명령/합격 기준)
- `03_PHASE3_ARCH_REVIEW.md`
  - 프론트 그래프 표현/백엔드 계측/신뢰성 정책 점검 및 완료 상태
- `04_PHASE4_ENTITY_RESOLUTION.md`
  - 학술 도메인 Entity Resolution 고도화(약어/표기 변형) 실행 기록
- `05_PHASE5_SEMANTIC_SCHOLAR.md`
  - Semantic Scholar 운영화(429/재시도/추천 경로 안정화) 실행 기록
- `06_SNAPSHOT_REVIEW_CHECKLIST.md`
  - 스냅샷 승인/리뷰 체크리스트
- `07_SNAPSHOT_DIFF_TRIAGE.md`
  - 스냅샷 diff triage 절차(허용/회귀/분리)
- `08_PLAYWRIGHT_E2E_VISUAL.md`
  - Playwright 상호작용/E2E/시각회귀 실행 가이드

## 현재 목표

1. 프로젝트의 코어 목적(학술 도메인 개념 중심 GraphRAG) 유지
2. Entity Resolution 및 근거 기반 지표를 통한 신뢰성 가시화
3. 프론트 지식그래프 표현/백엔드-DB 구조를 실무형으로 정리
