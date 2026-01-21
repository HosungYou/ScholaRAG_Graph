# Session Log: BUG-040 Cohere Retry & Fallback

## Session Metadata
- **Session ID**: 2026-01-21_bug-040-cohere-retry-fallback
- **Date**: 2026-01-21
- **Agent**: Claude Code (Opus 4.5)
- **Type**: Bug Fix
- **Duration**: ~30 minutes

---

## Context

### User Request
사용자가 ScholaRAG_Graph Import 로그 분석을 요청함. Import가 86%에서 멈추고 embedding이 0개 생성되는 문제 발생.

### Related Issues
- BUG-038: Cohere timeout 및 slow call 감지 (이미 완료)
- BUG-039: DB 연결 실패 시 Job 데이터 손실 (이미 완료)

---

## Analysis

### 로그 타임라인 분석
| 시간 (UTC) | 이벤트 |
|-----------|--------|
| 10:29:56 | Import 시작 |
| 10:29:56 → 10:47:20 | **17분 40초 로그 공백** |
| 10:48:26 | Cohere API slow: 10.8s (batch 723) |
| 10:48:58 | Cohere API slow: 30.1s (batch 724) |
| 10:50:19 | **ConnectError 발생** |
| 10:50:19 | Embeddings 생성: 0개 (전체 손실) |

### 근본 원인
1. Cohere API 네트워크 연결 실패 (`ConnectError`)
2. 재시도 로직 없이 즉시 예외 발생
3. 예외 발생 시 embedding 전체 손실

### 추가 발견 이슈
- **INFRA-007**: 502/503 에러 시 CORS 헤더 누락
- **PERF-011**: 17분 로그 공백 원인 불명 (추가 조사 필요)

---

## Solution Applied

### 1. Cohere Retry Logic (cohere_embeddings.py)

```python
# RETRYABLE_EXCEPTIONS 정의
RETRYABLE_EXCEPTIONS = (
    asyncio.TimeoutError,
    ConnectionError,
    OSError,
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpcore.ConnectError,
    httpcore.ConnectTimeout,
    httpcore.ReadTimeout,
)

# Exponential backoff 재시도
for attempt in range(max_retries):  # max_retries = 3
    try:
        response = await asyncio.wait_for(...)
        break
    except RETRYABLE_EXCEPTIONS as e:
        wait_time = 2 ** attempt  # 1s, 2s, 4s
        await asyncio.sleep(wait_time)
```

### 2. OpenAI Fallback Logic (embedding_pipeline.py)

```python
def _get_embedding_providers(self) -> Tuple[Optional, Optional]:
    """Primary(Cohere)와 Fallback(OpenAI) 프로바이더 반환"""
    primary = CohereEmbeddingProvider(...)
    fallback = OpenAIEmbeddingProvider(...)
    return primary, fallback

# 사용 시:
except Exception as e:
    if fallback_provider and not provider_failed:
        logger.warning("BUG-040: Switching to fallback")
        embedding_provider = fallback_provider
        # 해당 배치 재시도
```

---

## Files Modified

| File | Change |
|------|--------|
| `backend/llm/cohere_embeddings.py` | 재시도 로직 + RETRYABLE_EXCEPTIONS 추가 |
| `backend/graph/embedding/embedding_pipeline.py` | `_get_embedding_providers()` + 폴백 로직 |
| `DOCS/project-management/action-items.md` | BUG-040, INFRA-007, PERF-011 등록 |

---

## Action Items

### Completed
- [x] BUG-040: Cohere 재시도 + OpenAI 폴백 구현

### Pending
- [ ] INFRA-007: 502/503 CORS 헤더 문제
- [ ] PERF-011: 17분 로그 공백 원인 조사

---

## Deployment Notes

**Render 재배포 필요**
```bash
# Render Dashboard에서 Manual Deploy 실행
# 또는 git push로 자동 배포 (Auto-Deploy 켜져 있는 경우)
```

**검증 방법**:
1. 새로운 Zotero Import 시작
2. 로그에서 재시도 메시지 확인: `"Cohere API ... retry 1/3 after 1s"`
3. Cohere 실패 시 폴백 메시지 확인: `"BUG-040: Switching to fallback"`

---

## Session Statistics
- Files analyzed: 5
- Files modified: 3
- New action items: 3 (BUG-040, INFRA-007, PERF-011)
- Action items completed: 1 (BUG-040)
