# Release Notes - v0.2.1 Production Deployment Fixes

**Release Date**: 2026-01-19
**Type**: Bug Fix Release

---

## Overview

This release addresses critical production deployment issues discovered after v0.2.0 deployment. The fixes resolve embedding generation failures, gap analysis errors, and database schema mismatches that caused the 3D graph to show "NO GRAPH DATA AVAILABLE" and gap analysis to return 500/503 errors.

---

## Issues Fixed

### Issue 1: Cohere SDK `output_dimension` Not Supported

**Symptom**: Rebuild endpoint failing with `output_dimension` parameter error

**Root Cause**: The original Cohere SDK (`AsyncClient`) doesn't support the `output_dimension` parameter required for embed-v4.0 model to output 1536-dimensional vectors matching our pgvector schema.

**Error Log**:
```
TypeError: AsyncClient.embed() got an unexpected keyword argument 'output_dimension'
```

**Solution**: Migrated to `AsyncClientV2` which supports the `output_dimension` parameter for embed-v4.0.

**File Changed**: `backend/llm/cohere_embeddings.py`

```python
# Before (broken)
from cohere import AsyncClient
self._client = AsyncClient(api_key=self.api_key)

# After (fixed)
from cohere import AsyncClientV2
self._client = AsyncClientV2(api_key=self.api_key)
```

**Verification**:
```bash
curl -X POST ".../api/graph/.../rebuild"
# Result: 144 embeddings created, 352 relationships generated
```

---

### Issue 2: ConceptCluster Attribute Mismatch

**Symptom**: Gap analysis refresh returning 500 error

**Root Cause**: Code in `routers/graph.py` used incorrect attribute names for `ConceptCluster` dataclass.

**Error Log**:
```
AttributeError: 'ConceptCluster' object has no attribute 'cluster_id'
AttributeError: 'ConceptCluster' object has no attribute 'concepts'
```

**Actual Dataclass Definition** (`gap_detector.py:15-24`):
```python
@dataclass
class ConceptCluster:
    id: int                    # NOT cluster_id
    name: str = ""
    color: str = "#808080"
    concept_ids: list[str]     # NOT concepts
    centroid: Optional[np.ndarray] = None
    keywords: list[str] = field(default_factory=list)
    avg_centrality: float = 0.0
```

**Solution**: Updated attribute references in INSERT statement.

**File Changed**: `backend/routers/graph.py` (lines 1069-1092)

```python
# Before (broken)
await database.execute(
    "INSERT INTO concept_clusters ...",
    cluster.cluster_id,          # Wrong attribute
    cluster.concepts,            # Wrong attribute
    ...
)

# After (fixed)
await database.execute(
    "INSERT INTO concept_clusters ...",
    cluster.id,                  # Correct attribute
    [str(cid) for cid in cluster.concept_ids],  # Correct + string conversion
    ...
)
```

---

### Issue 3: Missing `potential_edges` Column

**Symptom**: Gap analysis INSERT failing after ConceptCluster fix

**Root Cause**: Migration 009 (potential_edges column) was not applied to production database.

**Error Log**:
```
asyncpg.exceptions.UndefinedColumnError: column "potential_edges" of relation "structural_gaps" does not exist
```

**Solution**: Applied migration 009 to production Supabase database.

**Migration Applied**: `database/migrations/009_potential_edges.sql`

```sql
ALTER TABLE structural_gaps
ADD COLUMN IF NOT EXISTS potential_edges JSONB DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_structural_gaps_potential_edges
ON structural_gaps USING gin(potential_edges);
```

---

### Issue 4: UUID Type Mismatch for TEXT[] Columns

**Symptom**: Gap analysis INSERT/SELECT failing with Pydantic validation error

**Root Cause**: PostgreSQL returns UUID columns as Python `UUID` objects, but Pydantic models expect `List[str]`. TEXT[] columns require explicit string conversion.

**Error Log**:
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for ConceptClusterResponse
concepts.0
  Input should be a valid string [type=string_type, input_value=UUID('8646b122-396c-...'), input_type=UUID]
```

**Solution**: Added explicit `str()` conversion in three locations:

**File Changed**: `backend/routers/graph.py`

**Location 1 - GET endpoint** (line 871-881):
```python
# Before
concepts=row["concepts"] or [],

# After
concepts=[str(c) for c in (row["concepts"] or [])],
```

**Location 2 - INSERT concept_clusters** (line 1080):
```python
# Before
cluster.concept_ids,

# After
[str(cid) for cid in cluster.concept_ids],
```

**Location 3 - INSERT structural_gaps** (lines 1109-1133):
```python
# Before
gap.concept_a_ids,
gap.concept_b_ids,

# After
concept_a_ids_str = [str(cid) for cid in gap.concept_a_ids]
concept_b_ids_str = [str(cid) for cid in gap.concept_b_ids]
```

---

## Deployment Timeline

| Time (UTC) | Action | Commit | Status |
|------------|--------|--------|--------|
| 18:13 | v0.2.0 deployed | `67c2519` | Live |
| 18:26 | ConceptCluster fix pushed | `bb9221f` | - |
| 18:41 | ConceptCluster fix deployed | `bb9221f` | Live |
| 18:45 | Migration 009 applied via Supabase | - | Applied |
| 18:46 | UUID conversion fix pushed | `53cfea6` | - |
| 18:59 | UUID conversion fix deployed | `53cfea6` | Live |

---

## Verification Results

### Graph Data API
```bash
GET /api/graph/visualization/359fbd62-8712-4d8a-a2ad-86f5e34102cb

Response:
{
  "nodes": 144,    # Previously: 0
  "edges": 352     # Previously: 0
}
```

### Gap Analysis API
```bash
POST /api/graph/gaps/359fbd62-8712-4d8a-a2ad-86f5e34102cb/refresh

Response:
{
  "clusters": 4,   # Previously: 500 error
  "gaps": 6,       # 6 structural gaps detected
  "potential_edges": [...]  # Ghost edges included
}
```

### Sample Gap Data
```json
{
  "id": "0c13ecf6-7815-4c55-8be8-82b8a551df07",
  "cluster_a_id": 1,
  "cluster_b_id": 0,
  "cluster_a_names": ["human intelligence", "interplay", "synthesis", "substitution", "limits of ai"],
  "cluster_b_names": ["literature review", "expert opinions", "case studies", "interviews"],
  "research_questions": [
    "How does human intelligence relate to literature review?",
    "What are the connections between human intelligence, interplay and literature review, expert opinions?"
  ],
  "potential_edges": [
    {"source_name": "interplay", "target_name": "interviews", "similarity": 0.49},
    {"source_name": "interplay", "target_name": "case studies", "similarity": 0.47}
  ]
}
```

---

## Files Changed

| File | Changes | Description |
|------|---------|-------------|
| `backend/llm/cohere_embeddings.py` | +2, -2 | AsyncClient → AsyncClientV2 |
| `backend/routers/graph.py` | +12, -8 | Attribute names + UUID conversion |
| `database/migrations/009_potential_edges.sql` | Applied | potential_edges column |
| `database/migrations/010_fix_structural_gaps_columns.sql` | Applied | Additional gap columns |

---

## Commits

| Hash | Message |
|------|---------|
| `bb9221f` | docs: Update progress tracker with InfraNodus Phase 6.5 completion |
| `53cfea6` | fix(backend): convert UUID objects to strings for TEXT[] columns |

---

## Root Cause Analysis

### Why These Bugs Occurred

1. **Cohere SDK Version**: The Cohere SDK has two client versions (`AsyncClient` and `AsyncClientV2`). The v4 embedding model features like `output_dimension` are only available in V2 API.

2. **Dataclass Naming Inconsistency**: Two similar dataclasses exist:
   - `ConceptCluster` (gap_detector.py): uses `id`, `concept_ids`
   - `ClusterResult` (centrality_analyzer.py): uses `cluster_id`, `node_ids`

   The code mistakenly used `ClusterResult` attribute names for `ConceptCluster`.

3. **Migration Not Applied**: Migration 009 was created but not run on production database before deploying the code that depends on it.

4. **PostgreSQL UUID Handling**: asyncpg returns UUID columns as Python `UUID` objects, not strings. When these are passed to Pydantic models expecting `List[str]`, validation fails.

---

## Lessons Learned

1. **Always apply migrations before deploying code that depends on them**
2. **Use consistent naming conventions across similar dataclasses**
3. **Add explicit type conversions when interfacing between PostgreSQL and Pydantic**
4. **Test embedding providers with actual API calls, not just mocks**

---

## Testing Recommendations

1. **Rebuild Test**:
   ```bash
   curl -X POST "https://scholarag-graph-api.onrender.com/api/graph/{project_id}/rebuild"
   ```
   Expected: Success with embedding/relationship counts

2. **Graph Data Test**:
   ```bash
   curl "https://scholarag-graph-api.onrender.com/api/graph/visualization/{project_id}"
   ```
   Expected: Non-zero nodes and edges

3. **Gap Analysis Test**:
   ```bash
   curl -X POST "https://scholarag-graph-api.onrender.com/api/graph/gaps/{project_id}/refresh"
   ```
   Expected: Clusters and gaps with all fields populated

---

## Breaking Changes

None. All changes are backward-compatible.

---

## Credits

Bug analysis and fixes implemented with Claude Code (Opus 4.5).
Production debugging session: 2026-01-19

---

## Additional Feature: Resizable Chat Panel

**Commit**: `79d4b88`

Added in follow-up to improve user experience:

### Features Added

1. **Resizable Chat Panel**
   - Drag handle between chat and graph panels
   - Min width: 320px, Max width: 800px (or 70% of container)
   - Width persisted in localStorage

2. **Collapsible Chat Panel**
   - Collapse button in panel header
   - Vertical "Chat" label shown when collapsed
   - Click to expand panel
   - Collapse state persisted in localStorage

### Files Added/Modified

| File | Description |
|------|-------------|
| `frontend/components/ui/ResizeHandle.tsx` | NEW - Draggable resize handle component |
| `frontend/components/ui/index.ts` | Export ResizeHandle |
| `frontend/app/projects/[id]/page.tsx` | Panel state, toggle button, resize integration |

### Usage

- **Resize**: Drag the grip handle between panels
- **Collapse**: Click the panel close icon in header
- **Expand**: Click the collapsed "Chat" tab on left edge

---

## Additional Fix: 3D Graph Node Stabilization & Labels

**Commit**: `63f3467`

### Issues Addressed

1. **Wobbly Nodes**: Nodes were moving erratically, making them impossible to click
2. **Missing Labels**: No visible labels on nodes - couldn't identify relationships

### Root Cause

1. Force simulation damping was too low (`d3VelocityDecay=0.3`)
2. Text labels only appeared on hover (tooltip), no persistent labels

### Solution

1. **Node Stabilization**
   - `d3VelocityDecay`: 0.3 → 0.7 (faster damping)
   - `d3AlphaDecay`: 0.02 → 0.05 (faster simulation convergence)

2. **Persistent Labels for Top 20% Centrality Nodes**
   - Calculate centrality threshold (top 20%)
   - Render Three.js CanvasTexture sprites as labels
   - Position labels above nodes
   - Truncate long names to 20 characters with ellipsis

### Files Modified

| File | Changes |
|------|---------|
| `frontend/components/graph/Graph3D.tsx` | +85 lines - stabilization params + label sprites |

### Technical Details

```typescript
// Stabilization parameters
d3AlphaDecay={0.05}    // Was 0.02
d3VelocityDecay={0.7}  // Was 0.3

// Label display logic
const shouldShowLabel = nodeCentrality >= labelCentralityThreshold;
// Creates CanvasTexture sprite positioned above node
```

### User Experience Improvement

- **Before**: Nodes constantly moving, no way to identify concepts
- **After**: Nodes quickly stabilize, top 20% most important nodes have visible labels
