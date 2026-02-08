# TDD (Test Design Document)

## 1. Test Objective

코어 기능을 유지한 채 신뢰성 강화 변경이 회귀 없이 동작하는지 검증한다.

## 2. Test Scope

- 포함
  - importer Entity Resolution 적용
  - import API 계약(`reliability_summary`)
  - 프론트 타입/렌더링(ImportProgress 신뢰성 카드)
  - Semantic Scholar 연계 실패 대응
- 제외
  - 대규모 부하 시험(별도 성능 테스트 트랙)

## 3. Test Levels

### Unit

1. Entity Resolution 서비스
   - 입력 엔티티 0개 처리
   - 동의어/오타 병합
   - `(entity_type, canonical_name)` 기준 중복 제거

### Integration

1. Importer 경로
   - ScholaRAG/PDF/Zotero 각각에서 resolution 통계 누적 확인
2. API Router
   - `/api/import/status/{job_id}`, `/api/import/jobs`
   - `reliability_summary` 존재/계산 규칙 확인

### Contract

1. 응답 스키마 정합성
   - `ImportJobResponse` optional/required 필드 검증
2. 프론트 타입 정합성
   - `ImportJob`/`ImportReliabilitySummary` 타입과 API payload 일치

### UI/Component

1. Import 완료 화면
   - summary text fallback
   - project 이동 경로 fallback (`result.project_id` → `project_id`)
   - reliability 카드 렌더링

## 4. Test Scenarios

### S1. Canonicalization Basic

- Given: `["LLM", "Large Language Model", "거대언어모델"]`
- When: resolution 수행
- Then:
  - 대표 canonical 1개
  - aliases/alias_count 기록

### S2. Import Status Contract

- Given: 완료된 import job
- When: status API 조회
- Then:
  - `reliability_summary` 필드 존재
  - `canonicalization_rate`가 0~1 범위

### S3. UI Completion Fallback

- Given: `status=completed`, `result.project_id=null`, `project_id` 존재
- When: ImportProgress 완료 렌더링
- Then:
  - "Open Project" 이동이 정상 동작

### S4. Semantic Scholar Rate Limit

- Given: 추천 API 429
- When: GapPanel 재시도 로직 작동
- Then:
  - countdown 표시
  - 자동 재시도 후 사용자 메시지 일관성 유지

## 5. Commands

### Backend

```bash
make test-backend-core
```

### Frontend (targeted)

```bash
make test-frontend-core
```

### Frontend (full check, known issues may fail)

```bash
cd frontend
npm run type-check
```

## 6. Acceptance Criteria

1. 백엔드 계약/기본 importer 테스트 통과
2. import 완료 시 신뢰성 지표가 API와 UI에서 동일 의미로 표시
3. `project_id` fallback 이동 로직이 누락 없이 동작
4. 테스트 실패 시 원인이 변경분인지 기존 인프라 이슈인지 구분 기록

## 7. Known Test Debt

1. Playwright 그래프 테스트는 `NEXT_PUBLIC_E2E_MOCK_3D=1` 기반이므로 실제 WebGL 물리 흔들림 회귀는 별도 브라우저 트랙 필요
2. 시각 회귀 baseline은 현재 Chromium 단일 브라우저 기준이며 cross-browser 편차(Firefox/WebKit)는 미커버

## 8. Immediate Next Test Work

1. Firefox/WebKit 시각 회귀 프로젝트 추가
2. 실제 3D 렌더 경로(비 mock) 야간 회귀 잡 분리
3. Playwright trace/video artifact를 PR 코멘트에 자동 링크
