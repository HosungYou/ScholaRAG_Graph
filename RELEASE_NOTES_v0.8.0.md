# ScholaRAG Graph v0.8.0 Release Notes

**Release Date**: 2026-02-04
**Focus**: InfraNodus UI/UX Parity & Critical Bug Fixes

---

## Summary

v0.8.0 achieves InfraNodus feature parity for core UI/UX patterns while fixing critical accessibility and stability issues. This release focuses on user experience improvements without changing core functionality.

---

## New Features

### Adaptive Label Visibility Toggle (P0-1)
- **New toolbar button** cycles through three label modes:
  - `none`: No labels shown
  - `important`: Labels on high-centrality nodes (default)
  - `all`: Labels on all nodes
- **Icons**: Tags (all) → Tag (important) → Type (none)
- **Location**: Top toolbar, next to Bloom toggle

### Node Removal Preview UX (P1-2)
- **Preview mode**: See which nodes will be removed before applying
- **Visual indicators**: Amber badges mark nodes for removal
- **Toggle**: Eye icon to show/hide preview
- **Clearer workflow**: "Apply Slicing" button with reset hints

### InsightHUD Repositioning (P2-1)
- **New position**: Right side, below other panels (InfraNodus-style)
- **Dynamic stacking**: Adjusts based on visible panels
- **Old position**: Was bottom-left

---

## Bug Fixes

### EdgeContextModal Accessibility (P0-2)
- **ESC key**: Press ESC to close modal
- **Focus trap**: Tab key cycles within modal
- **ARIA attributes**: `role="dialog"`, `aria-modal`, proper labeling
- **User-friendly errors**: 500 errors show "Evidence not available" instead of technical message

### Relationship Evidence API Stability (P0-3)
- **Table check**: Verifies `relationship_evidence` table exists before querying
- **Graceful fallback**: Returns empty results instead of 500 error
- **RLS handling**: Catches permission errors without crashing

### Cluster Color Stability (P1-1)
- **Hash-based assignment**: Same cluster always gets same color
- **Before**: Colors changed based on array order
- **After**: Colors stable across page refreshes

---

## Technical Changes

### Frontend

| File | Changes |
|------|---------|
| `useGraph3DStore.ts` | Added `labelVisibility` state, `cycleLabelVisibility()` action |
| `KnowledgeGraph3D.tsx` | Label toggle button, InsightHUD positioning |
| `Graph3D.tsx` | `hashClusterId()` function for stable colors |
| `EdgeContextModal.tsx` | ESC handler, focus trap, ARIA attributes |
| `CentralityPanel.tsx` | Preview mode UI, visual indicators |
| `InsightHUD.tsx` | Dynamic positioning support |

### Backend

| File | Changes |
|------|---------|
| `routers/graph.py` | Table existence check in evidence API |

---

## Migration Guide

### No Breaking Changes
v0.8.0 is fully backward compatible.

### Optional Actions
- Clear browser cache for UI changes to take effect immediately
- No database migrations required

---

## Deployment

### Automatic Deployment
- **Frontend**: Vercel auto-deploys on push to main
- **Backend**: Render Docker auto-deploys on push to main

### Verification
```bash
# Frontend health
curl https://schola-rag-graph.vercel.app

# Backend health
curl https://scholarag-graph-docker.onrender.com/health
```

---

## Testing Checklist

### P0 Verification
- [ ] Label toggle button: Click cycles none → important → all
- [ ] EdgeContextModal: ESC key closes modal
- [ ] EdgeContextModal: Tab key stays within modal
- [ ] Evidence API: No 500 error when table doesn't exist

### P1 Verification
- [ ] Cluster colors: Same after page refresh
- [ ] Node removal: Preview shows amber badges
- [ ] Node removal: Apply Slicing works, Reset restores

### P2 Verification
- [ ] InsightHUD: Shows on right side
- [ ] InsightHUD: Stacks below CentralityPanel when both visible

---

## Known Issues

None introduced in this release.

---

## Next Release (v0.9.0 Preview)

Planned features:
- Entity Extraction V2 (all 8 entity types)
- AI Chat data-based fallback
- Adaptive gap detection threshold
- Semantic diversity metrics
