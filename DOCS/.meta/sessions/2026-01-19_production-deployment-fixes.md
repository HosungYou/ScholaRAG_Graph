# Session Log: Production Deployment Fixes

**Session ID**: 2026-01-19_production-deployment-fixes
**Date**: 2026-01-19
**Agent**: Claude Code (Opus 4.5)
**Type**: Bug Fix / Production Debugging
**Duration**: ~2 hours

---

## Context

### User Request
Fix production deployment issues after v0.2.0 release:
- 3D graph showing "NO GRAPH DATA AVAILABLE"
- Gap analysis returning 500/503 errors
- 0 nodes and 0 edges in graph visualization

### Related Decisions
- ADR-001: Concept-Centric Graph (entities must be visualized)
- v0.2.0: InfraNodus-style visualization features

---

## Summary

Successfully debugged and fixed 4 critical production issues that prevented the 3D knowledge graph from displaying data and gap analysis from working.

### Issues Fixed

| Issue | Root Cause | Solution |
|-------|------------|----------|
| Cohere embedding failure | `AsyncClient` doesn't support `output_dimension` | Switched to `AsyncClientV2` |
| ConceptCluster AttributeError | Wrong attribute names (`cluster_id` vs `id`) | Fixed attribute references |
| Missing potential_edges column | Migration 009 not applied | Applied via Supabase MCP |
| UUID validation error | PostgreSQL returns UUID objects | Added `str()` conversion |

### Final Results
- **Nodes**: 144 (was 0)
- **Edges**: 352 (was 0)
- **Clusters**: 4
- **Structural Gaps**: 6

---

## Detailed Error Analysis

### Error 1: Cohere SDK

**Log**:
```
TypeError: AsyncClient.embed() got an unexpected keyword argument 'output_dimension'
```

**Investigation**:
- Checked Cohere SDK documentation
- Found that `embed-v4.0` model with `output_dimension` requires V2 API
- V2 API uses `AsyncClientV2` class

**Fix** (`backend/llm/cohere_embeddings.py`):
```python
# Line 39-40
from cohere import AsyncClientV2
self._client = AsyncClientV2(api_key=self.api_key)
```

---

### Error 2: ConceptCluster Attributes

**Log**:
```
AttributeError: 'ConceptCluster' object has no attribute 'cluster_id'
```

**Investigation**:
- Read `gap_detector.py` to find actual dataclass definition
- Found `ConceptCluster` uses `id` and `concept_ids`
- Different from `ClusterResult` which uses `cluster_id` and `node_ids`

**Fix** (`backend/routers/graph.py`):
```python
# Changed: cluster.cluster_id → cluster.id
# Changed: cluster.concepts → cluster.concept_ids
```

---

### Error 3: Missing Column

**Log**:
```
asyncpg.exceptions.UndefinedColumnError: column "potential_edges" does not exist
```

**Investigation**:
- Migration 009 creates `potential_edges` column
- Migration was in codebase but not applied to production

**Fix**: Applied migration via Supabase MCP tool
```sql
ALTER TABLE structural_gaps
ADD COLUMN IF NOT EXISTS potential_edges JSONB DEFAULT '[]'::jsonb;
```

---

### Error 4: UUID Type Mismatch

**Log**:
```
pydantic_core._pydantic_core.ValidationError:
  Input should be a valid string [type=string_type, input_value=UUID('...'), input_type=UUID]
```

**Investigation**:
- asyncpg returns UUID columns as Python `UUID` objects
- Pydantic `ConceptClusterResponse.concepts` expects `List[str]`
- TEXT[] columns also require string conversion on INSERT

**Fix** (`backend/routers/graph.py`):
```python
# GET endpoint
concepts=[str(c) for c in (row["concepts"] or [])]

# INSERT statements
[str(cid) for cid in cluster.concept_ids]
[str(cid) for cid in gap.concept_a_ids]
```

---

## Commits

| Hash | Message | Files |
|------|---------|-------|
| `bb9221f` | docs: Update progress tracker | 1 |
| `53cfea6` | fix(backend): convert UUID objects to strings | 1 |

---

## Deployments

| Deploy ID | Commit | Status | Time |
|-----------|--------|--------|------|
| `dep-d5n78doqo81c73dtr6k0` | `67c2519` | Deactivated | 18:13-18:28 |
| `dep-d5n7bbq9mqds73b9urog` | `bb9221f` | Deactivated | 18:19-18:41 |
| `dep-d5n7nvmmcj7s73cvgdcg` | `53cfea6` | **Live** | 18:46-18:59 |

---

## Action Items

- [x] SEC-001: Fix Cohere SDK version
- [x] BUG-001: Fix ConceptCluster attribute names
- [x] BUG-002: Apply migration 009
- [x] BUG-003: Fix UUID to string conversion
- [ ] FUNC-001: Add LLM panel resize functionality
- [ ] FUNC-002: Add LLM panel toggle button

---

## Session Statistics

| Metric | Value |
|--------|-------|
| Files Modified | 2 |
| Lines Changed | ~20 |
| Deployments | 3 |
| Migrations Applied | 2 |
| Errors Fixed | 4 |
| API Tests | 5 |

---

## Key Learnings

1. **Cohere SDK versioning**: V2 API is required for newer model features
2. **Dataclass naming**: Similar dataclasses with different attribute names can cause confusion
3. **Migration ordering**: Always apply migrations before deploying dependent code
4. **Type safety**: asyncpg UUID handling requires explicit conversion for Pydantic

---

## Related Documents

- `RELEASE_NOTES_v0.2.1.md`: Full release documentation
- `database/migrations/009_potential_edges.sql`: Applied migration
- `database/migrations/010_fix_structural_gaps_columns.sql`: Applied migration
