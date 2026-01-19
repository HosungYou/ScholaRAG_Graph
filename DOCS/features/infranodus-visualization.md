# InfraNodus-Style Visualization

> **Version**: 0.2.0
> **Status**: Implemented
> **Reference**: [InfraNodus](https://infranodus.com/)

---

## Overview

InfraNodus 스타일 시각화 기능은 Knowledge Graph에서 **구조적 빈틈(Structural Gaps)**을 시각적으로 탐색할 수 있게 합니다.

### Key Features

1. **Ghost Edge Visualization**: 클러스터 간 잠재적 연결을 점선으로 표시
2. **Cluster-Based Edge Coloring**: 클러스터 멤버십에 따른 엣지 색상 구분
3. **Insight HUD**: 실시간 그래프 품질 메트릭 표시
4. **Main Topics Panel**: 클러스터 비율 시각화 및 인터랙션

---

## 1. Ghost Edge Visualization

### 개념

**Ghost Edge**는 현재 연결되지 않았지만 **의미론적으로 유사한** 개념 쌍을 점선으로 표시합니다. 이는 연구자가 "빠진 연결"을 발견하고 새로운 연구 방향을 찾는 데 도움을 줍니다.

### 작동 방식

```
Cluster A                    Cluster B
┌─────────┐                  ┌─────────┐
│ Node A1 │╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌►│ Node B1 │
│ Node A2 │                  │ Node B2 │
│ Node A3 │╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌►│ Node B3 │
└─────────┘                  └─────────┘
          Ghost Edges (점선)
```

### 사용 방법

1. **Gap Panel**에서 Structural Gap 선택
2. 자동으로 관련 Ghost Edge가 점선으로 표시됨
3. 점선의 투명도는 유사도에 비례 (높을수록 진함)

### 기술 세부사항

- **유사도 계산**: Cosine similarity between concept embeddings
- **임계값**: `min_similarity = 0.3`
- **최대 표시 수**: Gap당 5개
- **색상**: Amber (`#FFAA00`)

```typescript
// Three.js LineDashedMaterial
const material = new THREE.LineDashedMaterial({
  color: 0xffaa00,
  dashSize: 3,
  gapSize: 2,
  opacity: 0.4 + similarity * 0.4,
  transparent: true,
});
```

---

## 2. Cluster-Based Edge Coloring

### 개념

엣지 색상이 연결된 노드의 **클러스터 멤버십**을 반영합니다. 이를 통해 클러스터 구조를 직관적으로 파악할 수 있습니다.

### 색상 규칙

| Edge Type | Color | Opacity |
|-----------|-------|---------|
| 같은 클러스터 내 | 클러스터 색상 | 35% |
| 다른 클러스터 간 | 블렌딩 색상 | 15% |
| Ghost Edge | Amber | 40-80% |
| Highlighted | Gold | 80% |

### 클러스터 색상 팔레트

```typescript
const CLUSTER_COLORS = [
  '#FF6B6B', // Coral Red
  '#4ECDC4', // Turquoise
  '#45B7D1', // Sky Blue
  '#96CEB4', // Sage Green
  '#FFEAA7', // Soft Yellow
  '#DDA0DD', // Plum
  '#98D8C8', // Mint
  '#F7DC6F', // Gold
  '#BB8FCE', // Lavender
  '#85C1E9', // Light Blue
  '#F8B500', // Amber
  '#82E0AA', // Light Green
];
```

### 헬퍼 함수

```typescript
// Hex to RGBA 변환
hexToRgba(hex: string, alpha: number): string

// 두 색상 블렌딩
blendColors(color1: string, color2: string, ratio: number): string

// 노드 → 클러스터 매핑
nodeClusterMap: Map<string, number>
```

---

## 3. Insight HUD

### 개념

**Insight HUD (Heads-Up Display)**는 그래프 품질 메트릭을 실시간으로 표시합니다. 연구자가 Knowledge Graph의 구조적 특성을 빠르게 파악할 수 있습니다.

### UI 위치

좌측 하단 (Collapsible)

### 표시 메트릭

| Metric | Description | Good Value |
|--------|-------------|------------|
| **Modularity** | 클러스터 분리 품질 | 0.4-0.7 |
| **Diversity** | 클러스터 크기 균형 | > 0.5 |
| **Density** | 연결 밀도 | Context-dependent |

### 통계 그리드

- **Nodes**: 총 노드 수
- **Edges**: 총 엣지 수
- **Clusters**: 클러스터 수
- **Components**: 연결 컴포넌트 수

### API

```
GET /api/graph/metrics/{project_id}

Response:
{
  "modularity": 0.65,
  "diversity": 0.82,
  "density": 0.12,
  "avg_clustering": 0.45,
  "num_components": 3,
  "node_count": 150,
  "edge_count": 420,
  "cluster_count": 5
}
```

### 메트릭 계산

```python
# Modularity (NetworkX)
modularity = nx.algorithms.community.quality.modularity(G, communities)

# Diversity (Normalized entropy)
diversity = -sum(p * log(p) for p in cluster_sizes) / log(num_clusters)

# Density
density = 2 * num_edges / (num_nodes * (num_nodes - 1))
```

---

## 4. Main Topics Panel

### 개념

**Main Topics Panel**은 InfraNodus 스타일로 클러스터 비율을 시각화합니다. 연구자가 어떤 주제가 Knowledge Graph에서 큰 비중을 차지하는지 한눈에 파악할 수 있습니다.

### UI 위치

좌측 하단 (Insight HUD 위)

### Features

1. **퍼센티지 바**: 각 클러스터의 상대적 크기
2. **색상 인디케이터**: 클러스터 색상 표시
3. **레이블**: 클러스터 이름
4. **Hover 인터랙션**: 해당 클러스터 노드 하이라이트
5. **Click 인터랙션**: 카메라 포커스 이동

### 인터랙션 흐름

```
┌─────────────────────────────────────┐
│ Main Topics              (3)        │
├─────────────────────────────────────┤
│ ● AI Chatbots          ████████ 42% │  ← Hover: Highlight nodes
│ ● Language Learning    █████░░░ 28% │  ← Click: Focus camera
│ ● Educational Tech     ███░░░░░ 30% │
├─────────────────────────────────────┤
│ Total Concepts                  150 │
└─────────────────────────────────────┘
```

---

## UI Controls

### 토글 버튼 (Top-Right Control Bar)

| Icon | Component | Default |
|------|-----------|---------|
| `BarChart3` | Insight HUD | ON |
| `PieChart` | Main Topics | OFF |

### 키보드 단축키 (Future)

| Key | Action |
|-----|--------|
| `I` | Toggle Insight HUD |
| `M` | Toggle Main Topics |
| `G` | Toggle Ghost Edges |

---

## Future Enhancements

### Phase 5: Topic View Mode

2D 블록 뷰로 클러스터를 간략화하여 표시:

```
┌──────────┐     ┌──────────┐
│          │     │          │
│ Cluster  │╌╌╌╌►│ Cluster  │
│    A     │     │    B     │
│          │     │          │
└──────────┘     └──────────┘
```

### Phase 6: Bloom Effect

UnrealBloomPass를 사용한 네온 효과 (optional)

---

## Files Reference

### Backend
- `backend/graph/gap_detector.py` - PotentialEdge 계산
- `backend/graph/centrality_analyzer.py` - Graph metrics
- `backend/routers/graph.py` - API endpoints

### Frontend
- `frontend/components/graph/Graph3D.tsx` - 3D 렌더링
- `frontend/components/graph/InsightHUD.tsx` - HUD 컴포넌트
- `frontend/components/graph/MainTopicsPanel.tsx` - Topics 패널
- `frontend/components/graph/KnowledgeGraph3D.tsx` - Integration

### Database
- `database/migrations/009_potential_edges.sql`

---

## Related Documentation

- [Gap Detection](../user-guide/gap-detection.md)
- [Graph Visualization Architecture](../architecture/graph-visualization.md)
- [Release Notes v0.2.0](../../RELEASE_NOTES_v0.2.0.md)
