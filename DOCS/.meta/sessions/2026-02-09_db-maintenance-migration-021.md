# Session Log: Database Maintenance & Migration 021

| Field | Value |
|-------|-------|
| **Session ID** | 2026-02-09_db-maintenance-migration-021 |
| **Date** | 2026-02-09 |
| **Agent** | Opus 4.6 |
| **Type** | infrastructure-maintenance |
| **Duration** | ~25 minutes |

---

## Context

### User Request
- Supabase Free Plan 용량 초과 (671.55 MB / 500 MB 한도) 해결
- 2026년 1월 테스트 프로젝트 26개 삭제
- Migration 021_cross_paper_links.sql 적용 (v0.15.0)
- Render DATABASE_URL을 Session Pooler로 교체

### Related Decisions
- INFRA-006: Auto-Deploy OFF 정책 유지
- v0.15.0: Cross-paper entity linking (SAME_AS) 마이그레이션 필요

---

## Summary

Supabase Free Plan 용량 초과 문제를 해결하기 위해 2026년 1월 테스트 프로젝트 26개와 관련 데이터(~104만 행)를 FK 순서대로 삭제하고, VACUUM FULL로 디스크 공간을 회수했습니다. 동시에 v0.15.0에서 추가된 Migration 021을 적용하고, Render DATABASE_URL을 Transaction Pooler에서 Session Pooler로 교체했습니다.

### Phase 1: 환경 설정
- psql 설치 (`brew install libpq`)
- Render MCP로 서비스 목록 조회 (scholarag-graph-docker: `srv-d5nen956ubrc73aqko8g`)
- Supabase DB 연결 테스트 성공 (PostgreSQL 17.6)
- 프로젝트 루트에 Supabase MCP `.mcp.json` 설정 추가

### Phase 2: 1월 데이터 삭제 (FK 순서)
| 테이블 | 삭제 행수 |
|--------|-----------|
| relationships | 995,787 |
| entities | 42,905 |
| semantic_chunks | 4,779 |
| paper_metadata | 375 |
| messages | 34 |
| projects | 26 |
| structural_gaps | 21 |
| conversations | 16 |
| concept_clusters | 10 |
| **Total** | **~1,043,953** |

### Phase 3: VACUUM & 공간 회수
- `VACUUM ANALYZE` → 통계 업데이트 (session pooler, port 5432)
- `VACUUM FULL` → 실제 디스크 공간 회수
  - relationships: 404 MB → 8.4 MB (**395.6 MB 회수**)
  - semantic_chunks: 174 MB → 127 MB (47 MB 회수)
  - entities: 65 MB → 31 MB (34 MB 회수)
- **Total DB: 671 MB → 181 MB (490 MB 회수, 73% 감소)**

### Phase 4: Migration 021 적용
- `ALTER TYPE relationship_type ADD VALUE IF NOT EXISTS 'SAME_AS'` → 성공
- `CREATE INDEX idx_entities_name_type` → 성공
- `CREATE INDEX idx_relationships_same_as` → 성공
- Migration marker NOTICE 출력 확인

### Phase 5: Render 인프라 변경
- DATABASE_URL: Transaction Pooler (port 6543) → **Session Pooler (port 5432)**
- Render MCP `update_environment_variables` 사용
- 자동 배포 트리거됨 (`dep-d6533q24d50c73dlrid0`)

---

## Action Items

- [x] INFRA-008: 1월 테스트 데이터 삭제 (26 프로젝트, ~104만 행)
- [x] INFRA-009: VACUUM FULL로 공간 회수 (671 MB → 181 MB)
- [x] INFRA-010: Migration 021_cross_paper_links.sql 적용
- [x] INFRA-011: Render DATABASE_URL Session Pooler로 교체
- [x] INFRA-012: 프로젝트 루트 Supabase MCP 설정

---

## Session Statistics

| Metric | Value |
|--------|-------|
| Files created | 1 (`.mcp.json`) |
| Files modified | 0 |
| DB rows deleted | ~1,043,953 |
| Disk space recovered | 490 MB (73%) |
| Migration applied | 021_cross_paper_links.sql |
| Indexes created | 2 |
| Enum values added | 1 (SAME_AS) |
| Infrastructure changes | 1 (DATABASE_URL) |
| Deployments triggered | 1 |
| February projects preserved | 4 |
