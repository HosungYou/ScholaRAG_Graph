# Release Notes v0.16.1

> **Version**: 0.16.1 | **Date**: 2026-02-13
> **Type**: Bug Fix Release

---

## Summary

Fixes two production issues discovered in v0.16.0: a 401 Unauthorized polling loop flooding server logs, and OpenAI embedding token limit errors for chunk embeddings.

---

## Bug Fixes

### BUG-043: 401 Unauthorized Polling Loop (Frontend)

**Problem**: When a user's Supabase auth token expired, multiple components with `useQuery` continued firing API requests. React-query's default retry (3 attempts) caused repeated 401 errors across `/api/import/jobs`, `/api/projects/`, and `/api/projects/:id`. With 2+ users, this created a continuous flood of 401 errors in production logs.

**Root Cause**:
- `useQuery` calls ran regardless of auth state (no `enabled` guard)
- React-query retried 401 errors (auth errors should not be retried)
- `ProtectedRoute` renders children during redirect (user state lag)
- Project detail and compare pages had no auth protection at all

**Fix** (5 files):

| File | Change |
|------|--------|
| `frontend/app/projects/page.tsx` | `InterruptedImportsSection` + `ProjectsContent`: `enabled: !!user` guard + custom `retry` that skips 401/403 |
| `frontend/app/projects/[id]/page.tsx` | Added `useAuth`, `enabled: !!user` guard + custom `retry` |
| `frontend/app/projects/compare/page.tsx` | Added `useAuth`, `enabled: !!user` guard + custom `retry` |
| `frontend/lib/api.ts` | 401 responses now throw immediately, breaking the retry loop |

**Impact**: Eliminates 401 log spam across all project pages; reduces unnecessary Supabase auth verification calls.

---

### E2-v2: OpenAI Embedding Token Limit Fix (Backend)

**Problem**: The E2 fix from v0.16.0 used `MAX_CHARS = 30000` (character-based truncation) assuming ~4 chars/token ratio. For academic/multilingual text, the actual ratio is ~2-3 chars/token, causing texts to exceed OpenAI's 8192 token limit.

**Production errors** (Feb 6-7, 2026):
- `11413 tokens` (limit 8192) - chunk embedding failed
- `16653 tokens` - failed
- `9677 tokens` - failed
- `8818 tokens` - failed

**Root Cause**: Character-to-token ratio varies by text type:
- English prose: ~4 chars/token (30000 chars = ~7500 tokens - OK)
- Academic text: ~2.6 chars/token (30000 chars = ~11500 tokens - OVER)
- Korean/multilingual: ~2 chars/token (30000 chars = ~15000 tokens - OVER)

**Fix**: Replaced character-based truncation with **tiktoken-based token counting**.

| File | Change |
|------|--------|
| `backend/llm/openai_embeddings.py` | Added `_truncate_to_max_tokens()` using tiktoken `cl100k_base` encoder with 8000 token limit |

**Before**:
```python
MAX_CHARS = 30000  # Unreliable, fails for academic text
cleaned_batch = [(t.strip()[:MAX_CHARS] if t.strip() else "empty") for t in batch]
```

**After**:
```python
def _truncate_to_max_tokens(text, max_tokens=8000):
    tokens = _encoder.encode(text.strip())
    if len(tokens) > max_tokens:
        return _encoder.decode(tokens[:max_tokens])
    return text.strip()
```

**Impact**: Eliminates all OpenAI 8192 token limit errors for chunk embeddings. Entity embeddings (short text) are unaffected.

---

## Technical Details

### Files Changed

| File | Lines | Change |
|------|-------|--------|
| `backend/llm/openai_embeddings.py` | +33/-4 | tiktoken import, `_truncate_to_max_tokens()`, updated `get_embeddings()` |
| `frontend/app/projects/page.tsx` | +22/-2 | `useAuth()` hook, `enabled` guard, custom `retry` on both queries |
| `frontend/app/projects/[id]/page.tsx` | +10/-1 | `useAuth` import + `enabled` guard + custom `retry` |
| `frontend/app/projects/compare/page.tsx` | +10/-1 | `useAuth` import + `enabled` guard + custom `retry` |
| `frontend/lib/api.ts` | +10/-0 | 401 early-exit in `request()` method |

### Dependencies

- **tiktoken** (already in `requirements.txt` v0.6.0+) - used for precise token counting
- No new dependencies added

### Migration

- No database migrations required
- No environment variable changes
- No breaking changes

### Deployment Notes

- Backend: Push to `render` remote triggers auto-deploy on Render Docker
- Frontend: Push to `origin` triggers auto-deploy on Vercel
- No manual intervention required

---

## Verification

After deployment, verify:

1. **401 Loop Fix**: Open Projects page without auth → no repeated 401 errors in Render logs
2. **Embedding Fix**: Import a project with long academic text → chunk embeddings complete without token limit errors
3. **Health Check**: `GET /health` returns `{"status": "healthy"}`

---

## What's NOT Changed

- OpenAI `text-embedding-3-small` remains the primary embedding provider
- Cohere remains the fallback provider (BUG-040)
- Entity embeddings pipeline unchanged (already working correctly)
- No changes to LLM provider (Groq), database, or auth system
