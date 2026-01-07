# Graph Visualization 시스템 스펙 (React Flow)

## 서비스 개요

| 항목 | 내용 |
|------|------|
| **역할** | Knowledge Graph 인터랙티브 시각화 |
| **라이브러리** | React Flow 11.10.0 |
| **위치** | Frontend (브라우저 렌더링) |
| **대안 (미사용)** | Neo4j Bloom, D3.js, Cytoscape.js |

---

## React Flow 선택 이유

| 기준 | React Flow | D3.js | Cytoscape.js | Neo4j Bloom |
|------|-----------|-------|--------------|-------------|
| React 통합 | ✅ 네이티브 | ⚠️ 래퍼 필요 | ⚠️ 래퍼 필요 | ❌ 별도 앱 |
| 커스텀 노드 | ✅ JSX/CSS | ⚠️ SVG | ⚠️ CSS | ❌ 제한적 |
| 번들 크기 | ~150KB | ~300KB | ~500KB | N/A |
| 학습 곡선 | 낮음 | 높음 | 중간 | 낮음 |
| 비용 | 무료 | 무료 | 무료 | 유료 |

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    KnowledgeGraph Component                      │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    ReactFlow Canvas                         ││
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       ││
│  │  │ Paper   │──│ Author  │  │ Concept │──│ Method  │       ││
│  │  │  Node   │  │  Node   │  │  Node   │  │  Node   │       ││
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘       ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   MiniMap    │  │   Controls   │  │     Background       │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ FilterPanel  │  │  SearchBar   │  │    NodeDetails       │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 노드 타입

### 엔티티별 스타일

| 타입 | 색상 | 아이콘 | 크기 |
|------|------|--------|------|
| **Paper** | `#3B82F6` (파랑) | 📄 FileText | 150×60 |
| **Author** | `#10B981` (초록) | 👤 User | 120×50 |
| **Concept** | `#8B5CF6` (보라) | 💡 Lightbulb | 130×50 |
| **Method** | `#F59E0B` (주황) | ⚙️ Settings | 130×50 |
| **Finding** | `#EF4444` (빨강) | 🎯 Target | 140×55 |

### CustomNode 구현

```typescript
// components/graph/CustomNode.tsx
interface CustomNodeData {
  label: string;
  entityType: 'Paper' | 'Author' | 'Concept' | 'Method' | 'Finding';
  properties?: Record<string, any>;
  isHighlighted?: boolean;
}

const nodeStyles: Record<string, { bg: string; border: string; icon: LucideIcon }> = {
  Paper: { bg: 'bg-blue-50', border: 'border-blue-500', icon: FileText },
  Author: { bg: 'bg-green-50', border: 'border-green-500', icon: User },
  Concept: { bg: 'bg-purple-50', border: 'border-purple-500', icon: Lightbulb },
  Method: { bg: 'bg-amber-50', border: 'border-amber-500', icon: Settings },
  Finding: { bg: 'bg-red-50', border: 'border-red-500', icon: Target },
};
```

---

## 엣지 타입

### 관계별 스타일

| 관계 | 스타일 | 애니메이션 |
|------|--------|-----------|
| `AUTHORED_BY` | Solid, Green | None |
| `CITES` | Dashed, Blue | None |
| `DISCUSSES_CONCEPT` | Solid, Purple | Highlighted |
| `USES_METHOD` | Solid, Orange | None |
| `HAS_FINDING` | Solid, Red | None |
| `RELATED_TO` | Dotted, Gray | None |

### 엣지 설정

```typescript
const edgeStyles: Record<string, Partial<Edge>> = {
  AUTHORED_BY: { style: { stroke: '#10B981' }, animated: false },
  CITES: { style: { stroke: '#3B82F6', strokeDasharray: '5,5' } },
  DISCUSSES_CONCEPT: { style: { stroke: '#8B5CF6' }, animated: true },
  USES_METHOD: { style: { stroke: '#F59E0B' } },
  HAS_FINDING: { style: { stroke: '#EF4444' } },
  RELATED_TO: { style: { stroke: '#9CA3AF', strokeDasharray: '2,2' } },
};
```

---

## 레이아웃 알고리즘

### 현재 구현: Grid + Random

```typescript
function layoutNodes(nodes: Node[]): Node[] {
  // 타입별 그룹화
  const groups = groupBy(nodes, 'data.entityType');

  // 각 그룹을 그리드 레이아웃
  let yOffset = 0;
  return Object.entries(groups).flatMap(([type, typeNodes]) => {
    const cols = Math.ceil(Math.sqrt(typeNodes.length));
    return typeNodes.map((node, i) => ({
      ...node,
      position: {
        x: (i % cols) * 200 + Math.random() * 50,
        y: Math.floor(i / cols) * 150 + yOffset,
      },
    }));
  });
}
```

### 향후 계획: Force-Directed

```typescript
// TODO: d3-force 또는 elkjs 통합
import { forceSimulation, forceLink, forceManyBody, forceCenter } from 'd3-force';

function forceDirectedLayout(nodes: Node[], edges: Edge[]): Node[] {
  const simulation = forceSimulation(nodes)
    .force('link', forceLink(edges).id(d => d.id))
    .force('charge', forceManyBody().strength(-300))
    .force('center', forceCenter(400, 300));

  // 시뮬레이션 실행
  simulation.tick(300);

  return nodes.map(node => ({
    ...node,
    position: { x: node.x, y: node.y },
  }));
}
```

---

## 인터랙션

### 지원 기능

| 기능 | 상태 | 설명 |
|------|------|------|
| 줌 인/아웃 | ✅ 완료 | 마우스 휠, 버튼 |
| 패닝 | ✅ 완료 | 드래그 |
| 노드 클릭 | ✅ 완료 | 상세 패널 표시 |
| 노드 드래그 | ✅ 완료 | 위치 변경 |
| 노드 선택 | ✅ 완료 | 하이라이트 |
| 멀티 선택 | ⚠️ 부분 | Shift+클릭 |
| 엣지 클릭 | ❌ 미구현 | 관계 상세 |
| 미니맵 | ✅ 완료 | 전체 보기 |
| Fit View | ✅ 완료 | 전체 화면 맞춤 |

### 이벤트 핸들러

```typescript
// KnowledgeGraph.tsx
<ReactFlow
  nodes={nodes}
  edges={edges}
  nodeTypes={nodeTypes}
  onNodeClick={(event, node) => {
    setSelectedNode(node);
    onNodeClick?.(node);
  }}
  onNodeDragStop={(event, node) => {
    updateNodePosition(node.id, node.position);
  }}
  onSelectionChange={({ nodes }) => {
    setHighlightedNodes(nodes.map(n => n.id));
  }}
  fitView
  minZoom={0.1}
  maxZoom={2}
>
```

---

## 하이라이팅 시스템

### 챗봇 연동

```typescript
// 채팅 응답에서 하이라이트 적용
interface ChatResponse {
  content: string;
  highlighted_nodes: string[];  // 강조할 노드 ID 목록
  highlighted_edges: string[];  // 강조할 엣지 ID 목록
}

// 하이라이트 스타일 적용
function applyHighlights(nodes: Node[], highlightIds: string[]): Node[] {
  return nodes.map(node => ({
    ...node,
    data: {
      ...node.data,
      isHighlighted: highlightIds.includes(node.id),
    },
    style: highlightIds.includes(node.id)
      ? { boxShadow: '0 0 20px rgba(59, 130, 246, 0.5)' }
      : {},
  }));
}
```

---

## 필터링

### FilterPanel 기능

| 필터 | 타입 | 상태 |
|------|------|------|
| 엔티티 타입 | Multi-select | ✅ 완료 |
| 연도 범위 | Range slider | ✅ 완료 |
| 관계 타입 | Multi-select | ⚠️ 부분 |
| 키워드 | Text search | ✅ 완료 |

### 필터 로직

```typescript
function filterGraph(
  nodes: Node[],
  edges: Edge[],
  filters: GraphFilters
): { nodes: Node[]; edges: Edge[] } {
  // 노드 필터링
  const filteredNodes = nodes.filter(node => {
    if (!filters.entityTypes.includes(node.data.entityType)) return false;
    if (node.data.year && (
      node.data.year < filters.yearRange[0] ||
      node.data.year > filters.yearRange[1]
    )) return false;
    return true;
  });

  // 연결된 엣지만 유지
  const nodeIds = new Set(filteredNodes.map(n => n.id));
  const filteredEdges = edges.filter(
    edge => nodeIds.has(edge.source) && nodeIds.has(edge.target)
  );

  return { nodes: filteredNodes, edges: filteredEdges };
}
```

---

## 검색

### SearchBar 기능

```typescript
interface SearchResult {
  id: string;
  entity_type: string;
  name: string;
  properties?: Record<string, any>;
}

// 검색 결과 처리
const handleSelect = (result: SearchResult) => {
  // 노드로 포커스 이동
  fitView({ nodes: [result.id], duration: 500 });
  // 하이라이트
  setHighlightedNodes([result.id]);
  // 상세 패널 표시
  setSelectedNode(result);
};
```

---

## 구현 진행률

### 전체: 90%

```
[██████████████████████░░] 90%
```

| 기능 | 진행률 | 상태 |
|------|--------|------|
| 노드 렌더링 | 100% | ✅ |
| 엣지 렌더링 | 100% | ✅ |
| 커스텀 스타일 | 100% | ✅ |
| 줌/패닝 | 100% | ✅ |
| 미니맵 | 100% | ✅ |
| 필터링 | 95% | ✅ |
| 검색 | 95% | ✅ |
| 하이라이팅 | 90% | ⚠️ |
| Force-Directed | 0% | ❌ |
| 내보내기 | 0% | ❌ |

---

## 향후 요구사항

### 우선순위 높음
- [ ] Force-directed 레이아웃 (d3-force 또는 elkjs)
- [ ] 엣지 클릭 → 관계 상세

### 우선순위 중간
- [ ] PNG/SVG 내보내기
- [ ] 클러스터링 (동일 주제 그룹화)
- [ ] 시간 기반 애니메이션 (연도별)

### 우선순위 낮음
- [ ] 3D 시각화 (Three.js)
- [ ] VR/AR 지원
- [ ] 협업 편집 (실시간 동기화)

---

## 성능 최적화

### 현재 적용

- React Flow 가상화 (대량 노드 처리)
- 메모이제이션 (`useMemo`, `useCallback`)
- 지연 로딩 (Intersection Observer)

### 권장 설정

```typescript
<ReactFlow
  // 대량 노드 성능
  nodesDraggable={nodes.length < 500}
  nodesConnectable={false}
  elementsSelectable={true}

  // 렌더링 최적화
  fitViewOptions={{ padding: 0.2 }}
  defaultViewport={{ x: 0, y: 0, zoom: 1 }}

  // 메모리 관리
  deleteKeyCode={null}
  selectionKeyCode={null}
/>
```

---

## 의존성

| 컴포넌트 | 의존 관계 |
|----------|----------|
| Backend API | `/api/graph/subgraph` 데이터 |
| Zustand Store | 그래프 상태 관리 |
| Chat Interface | 하이라이팅 연동 |
