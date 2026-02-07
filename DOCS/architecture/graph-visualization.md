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

### 전체 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                    KnowledgeGraph3D Component                    │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  View Mode Selector                        │ │
│  │  [3D Mode] [Topic Mode] [Gaps Mode]                       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  3D Mode: Graph3D (Three.js/react-three-fiber)            │ │
│  │  ├─ 3D force-directed layout                              │ │
│  │  ├─ Camera controls (orbit, pan, zoom)                    │ │
│  │  ├─ Node sizing by centrality                             │ │
│  │  └─ Edge weighted rendering                               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Topic Mode: TopicViewMode (D3.js Force Simulation)       │ │
│  │  ├─ Concept clusters as force-grouped nodes               │ │
│  │  ├─ Cluster-level relationships                           │ │
│  │  ├─ Main topic identification                             │ │
│  │  └─ Research direction indicators                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Gaps Mode: GapsViewMode (3D + Ghost Edges)               │ │
│  │  ├─ Actual edges (solid)                                  │ │
│  │  ├─ Ghost edges (potential relationships - dotted)        │ │
│  │  ├─ Bridge candidates highlighted                         │ │
│  │  ├─ Research gap visualization                            │ │
│  │  └─ AI-generated bridge hypotheses                        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Controls   │  │  Side Panels │  │   Node Details       │  │
│  │   Legend     │  │  Gap Panel   │  │   Modals             │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 컴포넌트 계층 구조

```
KnowledgeGraph3D (루트 컴포넌트)
├── View Mode Selection (상단 우측 컨트롤)
├── Graph Renderer (현재 viewMode에 따라)
│   ├── Graph3D (viewMode === '3d')
│   ├── TopicViewMode (viewMode === 'topic')
│   └── GapsViewMode (viewMode === 'gaps')
├── Side Panels
│   ├── GapPanel (연구 갭 분석)
│   ├── CentralityPanel (노드 슬라이싱/필터링)
│   └── ClusterPanel (클러스터 분석)
├── Overlays
│   ├── GraphLegend (범례)
│   ├── NodeDetails (선택된 노드 상세정보)
│   ├── EdgeContextModal (관계 상세정보)
│   ├── InsightHUD (통계)
│   └── MainTopicsPanel (주요 주제)
└── Status Bar (하단 우측)
```

---

## View Modes 아키텍처 (UI-012)

네 가지 상호 보완적인 시각화 모드로 지식 그래프를 탐색합니다.

### 1. 3D Mode (Graph3D)

**용도**: 전체 그래프의 3D 공간 시각화 및 네트워크 구조 이해

**기술 스택**:
- `react-force-graph-3d`: 3D force-directed layout
- `three.js`: 3D 렌더링 엔진
- `react-three-fiber`: React Three.js 바인딩

**주요 기능**:
| 기능 | 설명 |
|------|------|
| Force-Directed Layout | 노드와 엣지의 물리 시뮬레이션 |
| Node Sizing | 중심성(Centrality)에 따른 동적 크기 |
| Camera Control | Orbit, Pan, Zoom 인터랙션 |
| Particle Effect | 주변 입자 효과 (토글 가능) |
| Bloom Effect | 글로우 이펙트 (토글 가능) |
| Level of Detail (LOD) | 대규모 그래프의 성능 최적화 |
| Node Highlighting | 선택/연결된 노드 강조 |
| Edge Weighting | 관계 강도로 엣지 두께 결정 |

**코드 구조**:
```typescript
// frontend/components/graph/Graph3D.tsx
interface Graph3DProps {
  nodes: GraphEntity[];
  edges: GraphEdge[];
  clusters: ConceptCluster[];
  centralityMetrics: CentralityMetrics;
  highlightedNodes: string[];
  highlightedEdges: string[];
  selectedGap?: StructuralGap;
  bloomEnabled?: boolean;
  bloomIntensity?: number;
  glowSize?: number;
  showParticles?: boolean;
  particleSpeed?: number;
}

export const Graph3D = forwardRef<Graph3DRef, Graph3DProps>((props) => {
  // Three.js 렌더링 로직
  // Force simulation, collision detection, camera control
});
```

**사용 시나리오**:
- 전체 그래프 구조 파악
- 노드 간 거리 관계 이해
- 클러스터 시각적 확인
- 네트워크 밀도 분석

---

### 2. Topic Mode (TopicViewMode)

**용도**: 연구 주제별 클러스터 중심 분석

**기술 스택**:
- `d3-force`: D3.js 포스 시뮬레이션
- `d3-scale`: 색상 및 크기 스케일
- Canvas/SVG 렌더링

**주요 기능**:
| 기능 | 설명 |
|------|------|
| Cluster Grouping | 개념들을 주제별로 그룹화 |
| Force Simulation | 클러스터 간 척력/인력 시뮬레이션 |
| Main Topic Identification | 가장 중요한 주제 강조 |
| Cluster Relationships | 클러스터 간 연결 시각화 |
| Topic Statistics | 각 클러스터의 논문 수, 주요 키워드 |
| Research Directions | 클러스터 성장 추세 표시 |

**코드 구조**:
```typescript
// frontend/components/graph/TopicViewMode.tsx
interface TopicViewModeProps {
  clusters: ConceptCluster[];
  gaps: StructuralGap[];
  edges: GraphEdge[];
  onClusterClick: (clusterId: number) => void;
  onClusterHover: (clusterId: number | null) => void;
}

export function TopicViewMode({
  clusters,
  gaps,
  edges,
  onClusterClick,
  onClusterHover,
}: TopicViewModeProps) {
  // D3 force simulation
  // Cluster-level rendering
}
```

**InfraNodus 스타일 분석**:
- 주요 주제(Main Topics) 식별
- 클러스터 간 다리(Bridges) 감지
- 변질되는 주제(Peripheral) 식별

**사용 시나리오**:
- 연구 분야의 주요 주제 파악
- 주제 간 연관성 분석
- 연구 방향 추세 파악
- 학제 간 연구 기회 발견

---

### 3. Gaps Mode (GapsViewMode)

**용도**: 구조적 연구 갭 탐색 및 AI 기반 가설 생성

**기술 스택**:
- `Graph3D` (기반): 3D 렌더링 재사용
- Ghost edges (잠재 엣지): 점선으로 표현
- AI LLM (Groq llama-3.3-70b): 브리지 가설 생성

**주요 기능**:
| 기능 | 설명 | 구현 상태 |
|------|------|----------|
| Structural Gap Detection | 두 클러스터 간 연결 부족 감지 | ✅ 완료 |
| Ghost Edges | 잠재적 관계 (가상 엣지) 시각화 | ✅ 완료 |
| Bridge Candidates | 두 갭을 연결할 수 있는 노드 | ✅ 완료 |
| AI Bridge Hypotheses | Groq를 사용한 자동 가설 생성 | ✅ 완료 |
| Gap Statistics | 갭의 크기, 영향도, 관련 논문 수 | ✅ 완료 |
| Gap Query Panel | 갭별 상세 쿼리 인터페이스 | ✅ 완료 |

**구조적 갭의 정의**:
```python
# backend/graph/gap_detector.py
class StructuralGap:
    cluster_a_id: int          # 첫 번째 클러스터
    cluster_b_id: int          # 두 번째 클러스터
    cluster_a_concepts: list[str]  # 클러스터 A의 개념들
    cluster_b_concepts: list[str]  # 클러스터 B의 개념들

    gap_size: int              # 클러스터 간 거리 (엣지 수)
    bridge_candidates: list[str]   # 두 클러스터를 연결할 수 있는 노드
    potential_edges: list[PotentialEdge]  # 잠재적 관계들

    ai_hypothesis: str         # Groq가 생성한 브리지 가설
    confidence: float          # 가설의 신뢰도 (0-1)
```

**AI 브리지 가설 생성 (Groq llama-3.3-70b)**:
```python
# backend/graph/gap_detector.py의 GapDetector 클래스

async def generate_bridge_hypothesis(
    gap: StructuralGap,
    all_nodes: list[GraphEntity],
    context: str = None
) -> str:
    """
    두 클러스터를 연결하는 가설을 AI로 생성

    Groq를 통해:
    1. 클러스터 A의 주요 개념 분석
    2. 클러스터 B의 주요 개념 분석
    3. 브리지 후보 노드의 역할 검토
    4. 가설 생성 (예: "클러스터 A의 '기계학습'과
       클러스터 B의 '교육학'을 잇는 '학습 과학' 개념이 필요함")

    Returns: "AI 생성 가설 텍스트"
    """
```

**코드 구조**:
```typescript
// frontend/components/graph/GapsViewMode.tsx
interface GapsViewModeProps {
  nodes: GraphEntity[];
  edges: GraphEdge[];
  clusters: ConceptCluster[];
  centralityMetrics: CentralityMetrics;
  gaps: StructuralGap[];
  selectedGap?: StructuralGap;
  onGapSelect: (gap: StructuralGap) => void;
  onNodeClick: (node: GraphEntity) => void;
  onBackgroundClick: () => void;
  onEdgeClick: (edge: GraphEdge) => void;
  projectId: string;
}

export const GapsViewMode = forwardRef<Graph3DRef, GapsViewModeProps>(
  (props) => {
    // 3D Graph with ghost edges
    // Gap highlighting and analysis
    // AI hypothesis display
  }
);
```

**시각적 표현**:
```
Gaps Mode Visualization:

    Cluster A              Cluster B
    (개념들)  ─ ─ ─ ─ ─  (개념들)
      ●      Ghost Edges     ●
      ●      (잠재적 관계)    ●
      ●                      ●

    Bridge Candidates:
    ├─ 노드 X (신뢰도 0.85)
    ├─ 노드 Y (신뢰도 0.72)
    └─ 노드 Z (신뢰도 0.68)

    AI 가설:
    "Cluster A의 '기계학습'과 Cluster B의 '교육'을 잇는
     '적응형 학습 시스템' 연구가 필요합니다."
```

**사용 시나리오**:
- 미개척 연구 영역 발견
- 학제 간 연구 아이디어 도출
- 논문 작성 방향 제시
- 문헌 검토 갭 분석

---

### View Mode 전환 메커니즘

```typescript
// frontend/components/graph/KnowledgeGraph3D.tsx의 View Mode 구현

const [viewMode, setViewMode] = useState<'3d' | 'topic' | 'gaps'>('3d');

return (
  <div className="relative w-full h-full">
    {/* View Mode Selector - Top Right Control */}
    <div className="absolute top-4 right-4">
      <button onClick={() => setViewMode('3d')}>3D</button>
      <button onClick={() => setViewMode('topic')}>Topics</button>
      <button onClick={() => setViewMode('gaps')}>Gaps</button>
    </div>

    {/* Conditional Rendering */}
    {viewMode === '3d' && (
      <Graph3D
        nodes={displayData.nodes}
        edges={displayData.edges}
        clusters={clusters}
        centralityMetrics={centralityMetrics}
        // ... props
      />
    )}

    {viewMode === 'topic' && (
      <TopicViewMode
        clusters={clusters}
        gaps={gaps}
        edges={displayData.edges}
        onClusterClick={handleFocusCluster}
        // ... props
      />
    )}

    {viewMode === 'gaps' && (
      <GapsViewMode
        nodes={displayData.nodes}
        edges={displayData.edges}
        clusters={clusters}
        gaps={gaps}
        selectedGap={selectedGap}
        onGapSelect={setSelectedGap}
        // ... props
      />
    )}
  </div>
);
```

### View Mode별 최적화

| 측면 | 3D Mode | Topic Mode | Gaps Mode |
|------|---------|-----------|-----------|
| 권장 그래프 크기 | 50-500 노드 | 10-100 클러스터 | 20-1000 노드 |
| 렌더링 엔진 | Three.js | D3.js + Canvas | Three.js |
| 상호작용 복잡도 | 높음 | 중간 | 높음 |
| 데이터 처리 시간 | 1-3초 | 0.5-2초 | 2-5초 (AI 포함) |
| GPU 요구사항 | 필수 | 선택 | 권장 |

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

### 전체: 95%

```
[████████████████████████░] 95%
```

| 기능 | 진행률 | 상태 |
|------|--------|------|
| **3D Mode** |  |  |
| ├─ Graph3D (Three.js) | 100% | ✅ |
| ├─ Force Layout | 100% | ✅ |
| ├─ Centrality Visualization | 100% | ✅ |
| ├─ Camera Control | 100% | ✅ |
| ├─ Particle Effect | 100% | ✅ |
| └─ Bloom Effect | 100% | ✅ |
| **Topic Mode** | 100% | ✅ |
| ├─ D3 Force Simulation | 100% | ✅ |
| ├─ Cluster Grouping | 100% | ✅ |
| ├─ Main Topic Identification | 100% | ✅ |
| └─ Cluster Statistics | 100% | ✅ |
| **Gaps Mode** | 100% | ✅ |
| ├─ Ghost Edges | 100% | ✅ |
| ├─ Gap Detection | 100% | ✅ |
| ├─ Bridge Candidates | 100% | ✅ |
| ├─ AI Hypothesis (Groq) | 100% | ✅ |
| └─ Gap Query Panel | 100% | ✅ |
| **General Features** |  |  |
| ├─ 노드 렌더링 | 100% | ✅ |
| ├─ 엣지 렌더링 | 100% | ✅ |
| ├─ 커스텀 스타일 | 100% | ✅ |
| ├─ 필터링 | 95% | ✅ |
| ├─ 검색 | 95% | ✅ |
| ├─ 하이라이팅 | 100% | ✅ |
| └─ 내보내기 | 0% | ❌ |

---

## 향후 요구사항

### 우선순위 높음
- [x] ~~Force-directed 레이아웃~~ ✅ (3D & Topic Mode에서 구현)
- [x] ~~엣지 클릭 → 관계 상세~~ ✅ (EdgeContextModal 구현 - UI-011)
- [ ] PNG/SVG 내보내기 (Graph3D 캡처)
- [ ] 시간 기반 필터링 (논문 발표년도별 애니메이션)

### 우선순위 중간
- [ ] 다중 선택 노드 비교 기능
- [ ] 갭 분석 결과 내보내기
- [ ] 동적 AI 가설 재생성 (다른 모델 사용 시)
- [ ] View Mode 간 상태 동기화 개선

### 우선순위 낮음
- [ ] VR/AR 지원
- [ ] 협업 편집 (실시간 동기화)
- [ ] 커스텀 노드 모양 (원, 사각형, 다각형 등)
- [ ] 음성 기반 그래프 탐색

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
