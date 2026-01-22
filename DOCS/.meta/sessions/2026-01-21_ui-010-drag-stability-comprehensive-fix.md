# Session: UI-010 Comprehensive Drag Stability Fix

> **Session ID**: 2026-01-21-ui-010-drag-stability
> **Date**: 2026-01-21
> **Agent**: Claude Code (Opus 4.5)
> **Type**: Bug Fix
> **Duration**: ~1.5 hours

---

## Context

### User Request
이전 세션에서 UI-010 드래그 지터 수정이 효과가 없다는 피드백을 받아 근본 원인 분석 및 종합 수정 요청.

### Problem Symptoms
1. **스냅백 (Snap-back)**: 드래그 후 원위치로 복귀
2. **고주파 진동 (Jitter)**: 노드가 파르르 떨림
3. **그래프 리셋 (Explosion)**: 하이라이트 변경 시 전체 그래프 재배치

### Related Issues
- UI-010: Force Simulation Drag Jitter (이전 수정 불완전)
- UI-011: Relationship Evidence Modal (완료)
- UI-012: Topics View Button (완료)

---

## Root Cause Analysis

### 핵심 발견

**graphData useMemo의 의존성 문제**

```typescript
// 문제 코드 (수정 전)
const graphData = useMemo<ForceGraphData>(() => {
  const forceNodes: ForceGraphNode[] = nodes.map(node => {
    return {
      id: node.id,
      name: node.name,
      // ... 매번 새 객체 생성 → fx/fy/fz 손실!
    };
  });
  // ...
}, [nodes, edges, ..., highlightedNodeSet, ...]);  // ← highlightedNodeSet 변경 시마다 실행
```

**문제 원인**:
1. `highlightedNodeSet`이 변경될 때마다 `graphData` useMemo가 재실행
2. 새로운 노드 객체가 생성되어 `fx`, `fy`, `fz` (고정 위치) 값이 손실
3. ForceGraph3D 시뮬레이션이 새 객체를 받아 재시작
4. 모든 노드가 초기 위치로 리셋되는 "폭발" 효과 발생

---

## Solution Implementation

### 1. Position Persistence via useRef

```typescript
// UI-010 FIX: Store node positions to persist across re-renders
const nodePositionsRef = useRef<Map<string, {
  x: number; y: number; z: number;
  fx?: number; fy?: number; fz?: number
}>>(new Map());
```

### 2. Position Restoration in graphData

```typescript
const graphData = useMemo<ForceGraphData>(() => {
  const forceNodes: ForceGraphNode[] = nodes.map(node => {
    // UI-010 FIX: Restore position from ref if available
    const savedPosition = nodePositionsRef.current.get(node.id);

    const forceNode: ForceGraphNode = {
      id: node.id,
      name: node.name,
      // ... other properties
    };

    // Restore saved positions to prevent simulation restart
    if (savedPosition) {
      forceNode.x = savedPosition.x;
      forceNode.y = savedPosition.y;
      forceNode.z = savedPosition.z;
      if (savedPosition.fx !== undefined) forceNode.fx = savedPosition.fx;
      if (savedPosition.fy !== undefined) forceNode.fy = savedPosition.fy;
      if (savedPosition.fz !== undefined) forceNode.fz = savedPosition.fz;
    }

    return forceNode;
  });
  // ...
}, [nodes, edges, ..., highlightedNodeSet, ...]);
```

### 3. Periodic Position Saving

```typescript
// UI-010 FIX: Save node positions periodically
useEffect(() => {
  const savePositions = () => {
    if (fgRef.current) {
      const currentNodes = fgRef.current.graphData()?.nodes;
      if (currentNodes) {
        currentNodes.forEach((node: ForceGraphNode) => {
          if (node.x !== undefined && node.y !== undefined && node.z !== undefined) {
            nodePositionsRef.current.set(node.id, {
              x: node.x, y: node.y, z: node.z,
              fx: node.fx, fy: node.fy, fz: node.fz,
            });
          }
        });
      }
    }
  };

  // Save every 500ms while simulation runs
  const intervalId = setInterval(savePositions, 500);
  return () => clearInterval(intervalId);
}, []);
```

### 4. Enhanced Drag Handlers

```typescript
onNodeDrag={(node) => {
  // Pin node to cursor position during drag
  node.fx = node.x;
  node.fy = node.y;
  node.fz = node.z;

  // Save to ref for persistence across re-renders
  const nodeId = String(node.id);
  if (nodeId && node.x !== undefined && node.y !== undefined && node.z !== undefined) {
    nodePositionsRef.current.set(nodeId, {
      x: node.x, y: node.y, z: node.z,
      fx: node.fx, fy: node.fy, fz: node.fz,
    });
  }
}}
onNodeDragEnd={(node) => {
  // Keep node pinned after drag - prevents snap-back!
  node.fx = node.x;
  node.fy = node.y;
  node.fz = node.z;

  // Save final position
  const nodeId = String(node.id);
  if (nodeId && node.x !== undefined && node.y !== undefined && node.z !== undefined) {
    nodePositionsRef.current.set(nodeId, {
      x: node.x, y: node.y, z: node.z,
      fx: node.fx, fy: node.fy, fz: node.fz,
    });
  }
}}
```

---

## Commit

```
bbe3554 fix(frontend): UI-010 comprehensive drag stability fix
```

**Files Changed**: 1
**Lines Changed**: +110, -20

---

## Deployment

| Service | Platform | Status | Notes |
|---------|----------|--------|-------|
| Frontend | Vercel | ✅ Auto-deployed | Push triggers deployment |
| Backend | Render | ⏸️ Not needed | UI-010 is frontend-only |

---

## Verification Checklist

배포 후 확인 사항:

- [ ] 노드 드래그 시 스냅백 없음
- [ ] 노드 드래그 시 고주파 진동 없음
- [ ] 채팅 응답으로 하이라이트 변경 시 그래프 리셋 없음
- [ ] 더블클릭으로 노드 핀 해제 가능

---

## View Modes Analysis

사용자 질문에 대한 분석: "Topics, Concepts, Gaps 모드에 따라 라벨이 다르게 나타나는가?"

### 현재 구현된 뷰 모드

| 모드 | 설명 | 라벨 스타일 |
|------|------|-------------|
| **3D View** (`viewMode='3d'`) | 개별 노드 3D 그래프 | 중심성 기반 폰트 크기 (10px-22px) |
| **Topic View** (`viewMode='topic'`) | 2D 클러스터 블록 시각화 | 클러스터 이름 + "X concepts" |

### "Concepts"와 "Gaps"는 별도 모드가 아님

- **Concepts**: Entity Type 필터 (Concept, Method, Finding 등 토글)
- **Gaps**: Ghost Edges 토글 (구조적 갭의 잠재 연결선 표시)

별도의 "Concepts 모드" 또는 "Gaps 모드"는 존재하지 않음.

---

## Lessons Learned

### 1. useMemo 의존성과 객체 동일성

- useMemo가 새 객체를 반환하면 하위 컴포넌트/라이브러리가 "새 데이터"로 인식
- ForceGraph3D는 새 노드 배열을 받으면 시뮬레이션을 재시작
- **해결책**: useRef로 위치를 외부에 저장하고 새 객체에 복원

### 2. React와 D3-Force의 상호작용

- React의 상태 기반 렌더링과 D3-Force의 연속적 시뮬레이션은 충돌 가능
- 매 re-render마다 fx/fy/fz를 보존해야 드래그 위치가 유지됨
- **해결책**: 주기적 위치 저장 (interval) + 드래그 핸들러에서 즉시 저장

### 3. 이전 수정이 불완전했던 이유

- UI-005 수정: 물리 파라미터만 조정 (alphaDecay, velocityDecay)
- 근본 원인(graphData 재생성)을 해결하지 않아 증상이 지속
- **교훈**: 물리 파라미터 튜닝은 근본 원인 해결 후에 미세 조정용

---

## Session Statistics

| Metric | Value |
|--------|-------|
| Files Modified | 1 |
| Lines Changed | ~130 |
| Commits | 1 |
| Issues Fixed | 1 (UI-010 comprehensive) |
| Deployment | Frontend: Auto |

---

## Related Documents

- [UI-003/004/005/006 Session](./2026-01-21_ui-003-004-005-006-visualization-fixes.md)
- [Action Items](../project-management/action-items.md)
- [Graph Visualization Architecture](../architecture/graph-visualization.md)

---

*Generated by Claude Code on 2026-01-21*
