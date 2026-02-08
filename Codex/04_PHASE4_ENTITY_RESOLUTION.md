# Phase 4 Entity Resolution Upgrade

## 목표

학술 논문 도메인에서 동의어/약어/표기 변형으로 인해 그래프가 파편화되는 문제를 줄이고, canonical 기반 연결성을 강화한다.

## 이번 반영 (Step 1 + Step 2 완료)

- `backend/graph/entity_resolution.py`
  - `Long Form (ACRONYM)` 패턴 학습 추가
  - 약어 키 정규화(`G.C.N.` -> `gcn`) 기반 canonical 매핑 추가
  - 표기 변형 정규화(`fine-tuning`, `finetuning` -> `fine tuning`) 추가
  - 기존 타입 경계(동일 이름이라도 `entity_type` 다르면 분리) 유지
- `backend/tests/test_entity_resolution.py`
  - 약어 병합
  - 하이픈/붙여쓰기 병합
  - 타입 경계 유지 테스트 추가
  - 동형이의어(`SAT`) 문맥 분기 테스트 추가
  - 동일 문맥(`SAT` logic) 병합 테스트 추가

## Step 2 상세 (문맥 해소)

- `backend/graph/entity_resolution.py`
  - `homonym_context_rules` 추가 (`sat`, `transformer`)
  - 엔티티 `definition/description/properties` 기반 context text 생성
  - 키워드 점수 기반 context bucket 추론(`logic`, `education`, `attention`, `deep_learning`, `electrical`)
  - 그룹 키를 `(entity_type, canonical_name, context_bucket)`로 확장하여 오병합 방지
  - 결과 properties에 `resolution_context_bucket` 기록

## Step 3 상세 (Batch 후보군 + LLM 확정)

- `backend/graph/entity_resolution.py`
  - `resolve_entities_async()` 추가
  - 후보군 생성: `(entity_type, context_bucket)` 내부 유사도 스코어 기반 pair 생성
  - 고신뢰(auto) 병합과 불확실(LLM review) 병합을 분리
  - LLM 배치 확정: pair 리스트를 JSON decision으로 받아 최종 병합
  - 안전장치:
    - `auto_merge_threshold`, `llm_review_threshold`
    - `max_llm_pair_checks`, `llm_batch_size`
    - LLM 실패 시 deterministic 경로로 fallback
- importer 연동
  - `backend/importers/scholarag_importer.py`
  - `backend/importers/pdf_importer.py`
  - `backend/importers/zotero_rdf_importer.py`
  - `await resolve_entities_async(..., use_llm_confirmation=True)`로 전환
- 테스트
  - `backend/tests/test_entity_resolution.py`
  - 불확실 pair를 LLM 확인으로 병합하는 async 테스트 추가

## Step 4 상세 (오병합 샘플링/지표화)

- `backend/graph/entity_resolution.py`
  - `EntityResolutionStats` 확장:
    - `llm_pairs_reviewed`
    - `llm_pairs_confirmed`
    - `potential_false_merge_count`
    - `potential_false_merge_samples`
  - 불확실 구간(LLM 확정 필요 pair) 중 실제 확정된 pair를 샘플링해 수동 검수용 payload 생성
- importer 반영
  - `backend/importers/scholarag_importer.py`
  - `backend/importers/pdf_importer.py`
  - `backend/importers/zotero_rdf_importer.py`
  - 공통 누적 지표(`llm_pairs_*`, `potential_false_merge_*`)를 `stats`에 집계
- API 요약 반영
  - `backend/routers/import_.py`
  - `reliability_summary`에 아래 항목 표준화:
    - `llm_pairs_reviewed`
    - `llm_pairs_confirmed`
    - `llm_confirmation_accept_rate`
    - `potential_false_merge_count`
    - `potential_false_merge_ratio`
    - `potential_false_merge_samples`
- 프론트 표시 반영
  - `frontend/types/graph.ts`
  - `frontend/components/import/ImportProgress.tsx`
  - 완료 카드에서 LLM merge 검토/확정 비율 및 잠재 오병합 비율 노출

## 상태

- Phase 4 구현 완료
