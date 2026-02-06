# ScholaRAG Graph v0.10.1 Release Notes

**Release Date**: 2026-02-06  
**Type**: Patch Release (Stability + Infrastructure)  
**Previous**: `v0.10.0` (2026-02-05)

---

## Summary

v0.10.1은 프로젝트 화면 재진입(여러 번 열기/닫기) 시 발생하던 간헐적 불안정성을 줄이기 위한 안정화 릴리즈입니다.

핵심 목표:
1. 프로젝트 페이지 재진입 시 불필요한 중복 데이터 로드 제거
2. `/health` 요청으로 인한 과도한 DB 헬스 쿼리/연결 churn 완화
3. Render/Supabase 환경에서 연결 풀 부담 감소

---

## Problem

재진입이 반복될수록 백엔드 DB 로그에 짧은 세션 연결/해제가 지속적으로 발생했고, 특정 시점부터 상태 확인 요청과 일반 API 요청이 겹치며 일시적 오류(503 계열) 가능성이 커졌습니다.

관찰된 패턴:
- `connection received` → `authenticated` → `authorized` → 약 3초 내 `disconnection`
- 반복 진입 시 동일 패턴이 누적

---

## Root Cause

### 1) Frontend 중복 로드

프로젝트 페이지(`frontend/app/projects/[id]/page.tsx`)와 그래프 컴포넌트(`KnowledgeGraph3D`) 양쪽에서 그래프 데이터를 로드하고 있어, 페이지 재진입 시 중복 요청이 발생할 수 있었습니다.

### 2) Backend 헬스 체크 과호출

`/health` 엔드포인트가 요청마다 DB 상태/pgvector 상태를 각각 확인하는 구조였고, 인프라 헬스체크 주기와 겹치면서 DB probe 빈도가 불필요하게 높아졌습니다.

---

## Changes

### A. DB Health Snapshot 캐시 추가

**파일**: `backend/database.py`

- `get_health_snapshot(force_refresh=False)` 신규 추가
- DB/pgvector 상태를 단일 쿼리로 수집
- 15초 TTL 캐시 적용
- `asyncio.Lock`으로 동시 다발 health refresh를 단일화(thundering herd 완화)

### B. `/health` 경로 최적화

**파일**: `backend/main.py`

- `/health`가 `db.get_health_snapshot()` 결과를 사용하도록 변경
- 기존 다중 점검 호출을 1회 스냅샷 기반으로 통합

### C. 프로젝트 페이지 중복 fetch 제거

**파일**: `frontend/app/projects/[id]/page.tsx`

- 프로젝트 페이지에서 별도로 호출하던 `fetchGraphData(projectId)` effect 제거
- 그래프 로드는 `KnowledgeGraph3D` 단일 진입점으로 유지

---

## Files Changed

| File | Type | Description |
|------|------|-------------|
| `backend/database.py` | Updated | Health snapshot cache + concurrency-safe refresh |
| `backend/main.py` | Updated | `/health` endpoint now uses cached snapshot |
| `frontend/app/projects/[id]/page.tsx` | Updated | Removed duplicate graph data fetch |

---

## Expected Impact

- 프로젝트 재진입 시 중복 API 호출 감소
- 헬스체크로 인한 DB 연결 churn 완화
- Starter-tier 환경에서 연결 풀 압박 감소

---

## Compatibility

- Breaking change 없음
- API contract 변경 없음
- 기존 데이터/마이그레이션 영향 없음

---

## Validation

- Python 문법 검증:
  - `python3 -m py_compile backend/database.py backend/main.py` ✅
- Frontend 린트(변경 파일):
  - `npm run lint -- --file 'app/projects/[id]/page.tsx'` ✅
- 참고: 전체 TypeScript type-check는 기존 테스트 타입 설정(Jest globals) 이슈로 실패 상태(이번 패치와 무관)

