# ScholaRAG Graph v0.9.0 Release Notes

**Release Date**: 2026-02-04
**Focus**: Graph Physics & UX Critical Fixes

---

## Summary

v0.9.0 addresses 6 critical issues identified after v0.8.0 deployment, focusing on graph interaction quality, AI response accuracy, and gap detection reliability. This release completes the InfraNodus-style labeling implementation and removes unnecessary visual effects.

---

## Breaking Changes

### Particle Effects Removed
- **Lightning/Particle toggle** has been removed from the toolbar
- `showParticles` and `particleSpeed` state removed from `useGraph3DStore`
- If you had custom code using these properties, remove the references

---

## New Features

### InfraNodus-Style Labeling (PR-02)
- **Centrality-based visibility**: Top 20% nodes by betweenness centrality always show labels
- **Dynamic font sizing**: Labels scale 10-28px based on node centrality
- **Opacity gradient**: 0.3-1.0 opacity based on centrality (highlighted nodes always 1.0)
- **Shadow-only rendering**: Removed background boxes, using text shadow for readability
- **Label configuration**:
  ```typescript
  const LABEL_CONFIG = {
    minFontSize: 10,
    maxFontSize: 28,
    minOpacity: 0.3,
    maxOpacity: 1.0,
    alwaysVisiblePercentile: 0.8,  // Top 20%
    hoverRevealPercentile: 0.5,     // Top 50% on hover
  };
  ```

### Improved UI Tooltips (PR-06)
- All 14 toolbar buttons now have descriptive Korean tooltips
- Clear indication of current state (e.g., "라벨: important (클릭하여 none/important/all 전환)")

---

## Bug Fixes

### Graph Shrinkage Fixed (PR-01)
- **Problem**: Graph contracted rapidly after any interaction
- **Cause**: Excessive velocity decay (0.9 = 90% friction per tick)
- **Fix**: Reduced `d3VelocityDecay` from 0.9 to 0.4 for natural float
- **Additional**: Increased `cooldownTicks` from 200 to 1000 for proper stabilization

### Node Drag Release (PR-01)
- **Problem**: Dragged nodes remained pinned (fx/fy/fz fixed)
- **Fix**: Now sets fx/fy/fz to `undefined` on drag end
- **Result**: Nodes naturally reintegrate into force simulation after 2 seconds

### AI Explain UUID Response (PR-03)
- **Problem**: AI explanations showed raw UUIDs like "2e2d2e13-..."
- **Cause**: Node name not passed to backend, no DB fallback
- **Fix**:
  - Frontend now passes `nodeName` and `nodeType` in API call
  - Backend falls back to DB lookup if name not provided
  - If all else fails, uses "this concept" instead of UUID

### No Gaps Detected (PR-04)
- **Problem**: Large graphs (641+ nodes) showed "No Gaps Detected" despite multiple clusters
- **Cause**:
  1. Frontend didn't call refresh on initial load
  2. Adaptive threshold too conservative
- **Fix**:
  - Auto-refresh when gaps=0 but clusters>1
  - Minimum 3 gaps returned if candidates exist
  - Added `no_gaps_reason` field for debugging

### Relationship Evidence 500 Errors (PR-05)
- **Problem**: 500 errors when querying evidence for special character names
- **Fix**:
  - Added SQL LIKE escaping for `%`, `_`, `\`, `'`
  - Classified exception handling (table missing, permission denied, query failed)
  - User-friendly error messages in EdgeContextModal

---

## Technical Changes

### Frontend

| File | Changes |
|------|---------|
| `Graph3D.tsx` | Physics params (0.4 decay, 1000 cooldown), drag release, LABEL_CONFIG, centrality percentile map, removed particle props |
| `KnowledgeGraph3D.tsx` | Removed Lightning button, improved 14 button tooltips |
| `useGraph3DStore.ts` | Removed `showParticles`, `particleSpeed` state and actions |
| `useGraphStore.ts` | Auto-refresh gap analysis when 0 gaps but clusters>1 |
| `api.ts` | Extended `explainNode()` with optional `nodeName`, `nodeType` |
| `NodeDetails.tsx` | Pass `node.name`, `node.entity_type` to API |
| `EdgeContextModal.tsx` | Error code handling, user-friendly messages |
| `GapsViewMode.tsx` | Removed `showParticles` prop |
| `types/graph.ts` | Added `error_code` to RelationshipEvidence |

### Backend

| File | Changes |
|------|---------|
| `graph.py` | `escape_sql_like()` function, `no_gaps_reason` field, `error_code` in evidence response, classified exceptions |
| `chat.py` | DB fallback for node name in explain endpoint |
| `gap_detector.py` | Stronger `min_gaps` enforcement (returns top 3 if threshold too strict) |

---

## Migration Guide

### No Breaking Changes (mostly)

v0.9.0 is backward compatible except for particle effects removal.

### If Using Custom Particle Code

Remove references to:
- `showParticles` state
- `particleSpeed` state
- `toggleParticles()` action
- Any `linkDirectionalParticles*` props

### Clear Browser Cache

For UI changes to take effect immediately, clear browser cache or hard refresh (Cmd+Shift+R).

---

## Deployment

### Automatic Deployment
- **Frontend**: Vercel auto-deploys on push to main
- **Backend**: Render Docker auto-deploys on push to main (if enabled)

### Verification
```bash
# Frontend health
curl https://schola-rag-graph.vercel.app

# Backend health
curl https://scholarag-graph-docker.onrender.com/health
```

---

## Testing Checklist

### PR-01 Verification
- [ ] Click on graph: No rapid shrinkage
- [ ] Drag node: Releases and floats back naturally within 2 seconds
- [ ] No yellow particles visible anywhere
- [ ] Lightning button removed from toolbar

### PR-02 Verification
- [ ] Top 20% centrality nodes always show labels
- [ ] Font size varies 10-28px by centrality
- [ ] Label opacity varies 0.3-1.0
- [ ] No black background boxes on labels
- [ ] Highlighted nodes have full opacity labels

### PR-03 Verification
- [ ] Click "AI Explain" on any node
- [ ] Response uses actual concept name, not UUID

### PR-04 Verification
- [ ] Large project (500+ nodes) shows at least 3 gaps
- [ ] If 0 gaps with multiple clusters, auto-refresh triggers
- [ ] Console shows refresh log message

### PR-05 Verification
- [ ] Click edge with special characters in name
- [ ] No 500 error, shows friendly message if no evidence
- [ ] Evidence displays correctly when available

### PR-06 Verification
- [ ] Hover over each toolbar button
- [ ] All show descriptive Korean tooltips

---

## Known Issues

None introduced in this release.

---

## Next Release (v0.10.0 Preview)

Planned features:
- Entity Extraction V2 (all 8 entity types)
- AI Chat data-based fallback
- Semantic diversity metrics
- Next.js 14.2+ security upgrade
