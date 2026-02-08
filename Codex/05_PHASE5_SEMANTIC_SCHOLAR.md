# Phase 5 Semantic Scholar Operations

## 목표

GAP 기반 논문 추천 경로에서 Semantic Scholar 장애/429 상황을 예측 가능하게 다루고, 프론트 재시도 동작을 서버 정책과 일치시킨다.

## Step 1 반영 (429 표준화)

- `backend/integrations/semantic_scholar.py`
  - `SemanticScholarRateLimitError` 추가
  - `_request()`에서 429가 max retry를 초과하면 예외 발생
  - `Retry-After`를 예외 필드(`retry_after`)로 전달
- `backend/routers/graph.py`
  - gap recommendation endpoint에서 `SemanticScholarRateLimitError`를 HTTP 429로 변환
  - 응답 detail에 `retry_after_seconds` 포함
  - `Retry-After` header 전달
- `frontend/lib/api.ts`
  - API 에러 객체에 `status`, `retryAfterSeconds`, `detail` 부착
- `frontend/components/graph/GapPanel.tsx`
  - 429 시 하드코드 60s 대신 `retryAfterSeconds` 기반 카운트다운/토스트 적용

## Step 2 반영 (GAP→Bridge→Recommendation 구조화 로그)

- `backend/routers/graph.py`
  - 공통 구조화 로거 `_log_gap_chain_event()` 추가(JSON payload)
  - 다음 이벤트를 단계별로 기록:
    - `bridge_generation_requested`
    - `bridge_generation_completed`
    - `bridge_generation_failed`
    - `bridge_creation_requested`
    - `bridge_creation_resolved_concepts`
    - `bridge_creation_completed`
    - `bridge_creation_failed`
    - `recommendation_query_built`
    - `recommendation_fetch_completed`
    - `recommendation_fetch_rate_limited`
    - `recommendation_fetch_timeout`
    - `recommendation_fetch_failed`
  - 각 로그에 `project_id`, `gap_id`, query/bridge/cluster terms, 결과 개수, 에러 정보를 포함

## Step 3 반영 (gap_id 재현 리포트 export)

- `backend/routers/graph.py`
  - `GET /api/graph/gaps/{project_id}/repro/{gap_id}`
    - 단일 gap의 재현 가능한 체인 데이터(JSON) 반환
    - 포함 항목:
      - gap context(클러스터/브리지 후보/질문)
      - 실제 생성된 `BRIDGES_GAP` 관계 추적
      - Semantic Scholar 추천 status(`success|rate_limited|timeout|failed`)
  - `GET /api/graph/gaps/{project_id}/repro/{gap_id}/export?format=markdown|json`
    - Markdown/JSON export 지원
- `frontend/lib/api.ts`
  - `getGapReproReport(projectId, gapId, limit)`
  - `exportGapReproReport(projectId, gapId, format, limit)`

## 상태

- Phase 5 구현 완료

## 남은 항목(환경/운영)

1. integrations 테스트 환경 의존성 정리
   - 네트워크 제한으로 기본 3.9 경로 설치 실패 시 `backend/venv/bin/pytest`를 표준 실행 경로로 사용
