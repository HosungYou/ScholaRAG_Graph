# Session Log: BUG-028-EXT Checkpoint & Resume Implementation

> **Session ID**: 2026-01-21_bug-028-ext-checkpoint-resume
> **Date**: 2026-01-21
> **Agent**: Claude Code (Opus 4.5)
> **Type**: Feature Implementation
> **Duration**: ~45 minutes

---

## Context

### User Request
BUG-028 수정 커밋(7c91d76) 리뷰 후 향후 개선 방향 구현:
1. Checkpoint 저장: 각 항목 처리 후 metadata에 진행 상태 저장
2. Resume endpoint: `/api/import/resume/{job_id}` - 중단 지점부터 재개
3. Worker 분리: Celery/RQ로 import task를 별도 worker로 분리

### Related Decisions
- **BUG-028**: INTERRUPTED 상태 감지 (이미 구현됨)
- **INFRA-006**: Auto-Deploy 비활성화 (이미 적용됨)

---

## Summary

BUG-028의 확장 기능으로 Checkpoint 저장 및 Resume 기능을 구현했습니다.

### Design Decisions (Brainstorming Session)

1. **Checkpoint 저장 범위**: Paper 단위 (Recommended)
   - LLM 비용이 가장 비싼 작업이므로 중복 호출 최소화
   - 논문 간 독립성 (의존성 없음)
   - 기존 루프 구조에 추가 용이

2. **Resume 시 처리 방식**: Skip 방식
   - 이미 처리된 paper_id 목록을 checkpoint에 저장
   - 재개 시 해당 논문들 스킵
   - 구현 간단, 기존 로직 수정 최소화

3. **Worker 분리**: 현재 구조 유지
   - Auto-Deploy OFF + Checkpoint/Resume으로 대부분 상황 커버
   - Celery/Redis 추가 인프라 비용 불필요
   - 필요 시 향후 과제로 연기

### Implementation Summary

| Component | File | Changes |
|-----------|------|---------|
| Backend Job Store | `job_store.py` | `update_job()`에 metadata 파라미터 추가 |
| Backend Import Router | `import_.py` | Checkpoint 헬퍼, Resume endpoints 추가 |
| Backend Importer | `zotero_rdf_importer.py` | skip_paper_ids, existing_project_id 지원 |
| Frontend Types | `graph.ts` | ImportCheckpoint, ImportResumeInfo 타입 |
| Frontend API | `api.ts` | getResumeInfo(), resumeImport() 함수 |
| Frontend UI | `ImportProgress.tsx` | Interrupted 상태 UI 강화 |

---

## Action Items

### Completed
- [x] **BUG-028-EXT**: Checkpoint 저장 및 Resume 기능 구현

### No New Issues Found
기존 BUG-028 구현이 잘 되어 있어 확장 작업만 진행함.

---

## Session Statistics

| Metric | Value |
|--------|-------|
| Files Modified | 6 |
| Lines Added | ~300 |
| Lines Changed | ~50 |
| Tests Added | 0 (향후 추가 권장) |
| Documentation Updated | Yes |

---

## Technical Details

### Checkpoint Data Structure
```python
metadata = {
    "checkpoint": {
        "processed_paper_ids": ["paper_1", "paper_2", ...],
        "total_papers": 16,
        "last_processed_index": 5,
        "project_id": "uuid-...",
        "stage": "importing",
        "updated_at": "2026-01-21T06:46:37Z"
    }
}
```

### New API Endpoints
- `GET /api/import/resume/{job_id}/info` - Checkpoint 정보 조회
- `POST /api/import/resume/{job_id}` - Import 재개 (파일 재업로드 필요)

### Frontend UX Flow
```
[Import 진행 중] → [서버 재시작] → [INTERRUPTED]
                                       ↓
                              [Checkpoint 정보 표시]
                              - 처리된 논문: 5/16
                              - 프로젝트 ID 표시
                                       ↓
                              [파일 다시 업로드] or [부분 결과 보기]
                                       ↓
                              [Skip 처리된 논문 → 나머지 처리]
```

---

## Notes

- Zotero Import의 경우 파일 재업로드가 필요함 (서버에 파일 미저장)
- Checkpoint은 jobs 테이블의 metadata JSONB 컬럼 활용
- 별도 스키마 변경 없음
