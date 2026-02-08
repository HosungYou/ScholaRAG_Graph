# SDD (System Design Document)

## 1. Design Goal

- 코어 목적 유지:
  - 학술 논문 도메인의 개념 중심(GraphRAG) 구조
  - GAP 분석과 관계 기반 탐색
- 신뢰성 강화:
  - Entity Resolution으로 노드 중복/분절 최소화
  - 관계/응답의 근거(provenance) 가시화
  - import 품질 지표 표준화

## 2. Scope

- 포함
  - Import pipeline 신뢰성 계층
  - 프론트 그래프/진행 UI의 신뢰성 표상
  - 백엔드 API 계약 정합성
  - Semantic Scholar 연계 운영 규칙
- 제외
  - 즉시 GraphDB 전면 전환
  - 대규모 데이터 마이그레이션 자동화

## 3. Current Architecture Summary

### Frontend

- 주요 모듈
  - `KnowledgeGraph3D`, `GapPanel`, `ImportProgress`
- 책임
  - 그래프 시각화
  - GAP 탐색/추천 논문 인터랙션
  - import 상태/품질 결과 표시

### Backend

- 주요 모듈
  - importers: `scholarag_importer`, `pdf_importer`, `zotero_rdf_importer`
  - graph: `entity_resolution`, `entity_extractor`, `relationship_builder`
  - router: `import_`, `graph`
- 책임
  - 데이터 수집/추출/정규화/저장
  - 갭 분석 및 추천 연동
  - API 계약 제공

### Database

- PostgreSQL + pgvector 기반
- 핵심 성격
  - 관계형 스키마 위에 그래프 연산/검색 기능 결합
  - 다중 hop/고밀도 조인에서 병목 가능성 존재

## 4. Reliability-Critical Design Decisions

1. Entity canonicalization 우선 적용
   - 기준 키: `(entity_type, canonical_name)`
   - alias/원천 paper ID를 속성으로 보존
2. Import 품질 지표 표준화
   - `raw_entities_extracted`
   - `entities_after_resolution`
   - `merges_applied`
   - `canonicalization_rate`
   - `provenance_coverage`
   - `low_trust_edge_ratio`
3. UI에서 지표 직접 노출
   - import 완료 시 정규화율/근거커버리지/저신뢰 엣지 표시

## 5. Public Interfaces

### Import Status/Jobs Response Contract (요약)

```json
{
  "job_id": "string",
  "status": "pending|extracting|processing|building_graph|completed|failed|interrupted",
  "project_id": "string|null",
  "result": {
    "project_id": "string|null",
    "nodes_created": 0,
    "edges_created": 0
  },
  "reliability_summary": {
    "raw_entities_extracted": 0,
    "entities_after_resolution": 0,
    "merges_applied": 0,
    "canonicalization_rate": 0.0,
    "relationships_created": 0,
    "evidence_backed_relationships": 0,
    "provenance_coverage": 0.0,
    "low_trust_edges": 0,
    "low_trust_edge_ratio": 0.0
  }
}
```

## 6. Frontend Knowledge Graph Representation Methodology

1. 질문 유형 기반 뷰 라우팅
   - 관계 추적: 그래프 중심 뷰
   - GAP 탐색: gap 패널 중심 뷰
   - 시계열 변화: temporal 뷰
2. 관계 신뢰 표시 규칙
   - low-trust edge 비율이 높을수록 시각적 경고 강화
3. provenance 우선 탐색
   - 관계를 클릭하면 근거 텍스트/출처를 우선 제시

## 7. Backend/DB Evolution Strategy

1. 단기
   - Postgres 기반 유지
   - 병목 쿼리 계측 및 인덱스/쿼리 튜닝
2. 중기
   - 그래프 탐색 전용 read-model(또는 projection) 분리 검토
3. 장기
   - Native GraphDB 전환 여부를 실제 부하 지표로 결정

## 8. Academic Entity Resolution Design (Domain-Fit)

1. 동의어/표기 변형 통합
   - 예: `Fine-tuning`, `Finetuning`, `fine tuning`
2. 약어 문맥 해소
   - 문서 내 "Full Name (Acronym)" 패턴 우선
3. 동형이의어 분리
   - 도메인 제약(컴퓨터과학/AI)으로 의미 경계 고정
4. 하이브리드 검증
   - 임베딩 후보군 → LLM 최종 판정(비용 절감)

## 9. Observability

- 수집 지표
  - import 소요 시간
  - canonicalization rate
  - provenance coverage
  - low-trust edge ratio
  - S2 추천 API 실패율/429 빈도

## 10. Open Risks

1. 프론트 테스트 인프라 불안정(`jest-dom` 타입)
2. Postgres 다중 hop 성능 저하 가능성
3. 대규모 ER 처리 시 LLM 호출비/지연 증가
