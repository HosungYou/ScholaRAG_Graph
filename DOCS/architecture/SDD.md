# Software Design Document (SDD)

**Project**: ScholaRAG_Graph
**Version**: 0.11.2
**Last Updated**: 2026-02-06
**Status**: Production-Ready
**Document Type**: Architecture & Design Specification

---

## Document Information

| Field | Value |
|-------|-------|
| **Document Version** | 1.5.0 |
| **Project Version** | 0.11.2 |
| **Authors** | ScholaRAG_Graph Development Team |
| **Classification** | Internal - Technical Documentation |
| **Review Cycle** | Quarterly or on major releases |
| **Related Documents** | [Architecture Overview](overview.md), [Multi-Agent System](multi-agent-system.md), [Database Schema](database-schema.md), [Test Design Document](../testing/TDD.md) |

---

## 1. System Overview

### 1.1 Purpose

ScholaRAG_Graph is an AGENTiGraph-style **Concept-Centric Knowledge Graph** platform designed for systematic literature review automation. It transforms academic paper collections into interactive knowledge graphs with multi-agent conversational exploration capabilities, following PRISMA 2020 guidelines.

### 1.2 Scope

**In Scope:**
- Concept-centric knowledge graph construction from academic papers
- Multi-agent RAG pipeline for intelligent query processing
- Three visualization modes (3D, Topic, Gaps)
- ScholaRAG folder import, PDF import, Zotero integration
- Research gap detection using InfraNodus-style algorithms
- Team collaboration features
- PRISMA 2020 diagram generation

**Out of Scope:**
- Full-text paper search (only metadata and extracted entities)
- Real-time collaborative editing
- Mobile native applications
- Paper recommendation algorithms (moved to In Scope v0.12.0 — MVP via Semantic Scholar)

### 1.3 Key Features

| Feature | Description | Status |
|---------|-------------|--------|
| **Concept-Centric Graph** | Concepts/Methods/Findings as first-class entities; Papers/Authors as metadata | ✅ Complete |
| **6-Agent RAG Pipeline** | Intent → Concept → Task → Query → Reasoning → Response | ✅ Complete |
| **3D Visualization** | Three.js-based force-directed graph with physics simulation | ✅ Complete |
| **Topic Clustering** | D3.js-based community detection with Louvain algorithm | ✅ Complete |
| **Gap Detection** | InfraNodus-style structural gap analysis with AI bridge hypotheses | ✅ Complete |
| **Zotero Integration** | Hybrid import (Local API + Web API fallback) | ✅ Complete |
| **ScholaRAG Import** | Batch import from ScholaRAG systematic review projects | ✅ Complete |
| **Team Collaboration** | Project sharing, role-based access control | ✅ Complete |
| **Node Pinning** | Pin nodes with click, multi-select with Shift+click | ✅ v0.7.0 |
| **Adaptive Labels** | Zoom-responsive label visibility based on node importance | ✅ v0.7.0 |
| **Graph-to-Prompt** | Export graph context as structured prompt for AI tools | ✅ v0.7.0 |
| **InfraNodus-Style Labels** | Centrality-based visibility with dynamic font sizing and opacity gradient | ✅ v0.9.0 |
| **Graph Physics Optimization** | Velocity decay 0.4, cooldown 1000 ticks for stable simulation | ✅ v0.9.0 |
| **Gap Auto-Refresh** | Automatic gap re-detection when clusters exist but no gaps found | ✅ v0.9.0 |
| **Evidence SQL Safety** | SQL LIKE escaping and classified error handling for evidence queries | ✅ v0.9.0 |
| **Label Visibility Toggle** | Toolbar button cycles none/important/all label modes | ✅ v0.8.0 |
| **Node Removal Preview** | Visual preview before applying centrality-based slicing | ✅ v0.8.0 |
| **InsightHUD Repositioning** | Right-side InfraNodus-style positioning | ✅ v0.8.0 |
| **Cluster Color Stability** | Hash-based cluster color assignment for consistent colors | ✅ v0.8.0 |
| **Resizable Gap Panel** | Drag-to-resize gap analysis panel (256-500px) | ✅ v0.11.0 |
| **AI Evidence Explanation** | LLM-generated relationship explanations when no text evidence | ✅ v0.11.0 |
| **Dynamic Chat Questions** | Context-aware suggested questions based on graph data | ✅ v0.11.0 |
| **Hover Debounce** | 50ms debounced node hover to eliminate jitter | ✅ v0.11.0 |
| **Zotero Gap Detection** | Full gap detection parity in Zotero importer | ✅ v0.11.0 |

### 1.4 Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Graph Load Time (100 nodes) | < 2 seconds | ~1.5s |
| Query Response Time | < 5 seconds | ~3s (Groq LLM) |
| Import Speed | 100 papers/minute | ~120 papers/min |
| Concurrent Users | 50+ | Tested up to 100 |
| Graph Visualization Smoothness | 60 FPS | 55-60 FPS |

### 1.5 Runtime Stability Focus (v0.11.1)

Render Starter 환경에서 관찰된 `memory limit exceeded` 이슈 대응을 위해,
아래 6개를 단기 안정화 우선순위로 정의한다.

1. **Request shaping**
- `/api/graph/visualization/{project_id}`에 edge 상한(`max_edges`)을 적용해
  고밀도 그래프 응답의 메모리 피크를 제한한다.

2. **In-process cache bounding**
- centrality cache를 bounded LRU(최대 20개 프로젝트)로 제한해
  장시간 가동 시 누적 메모리 증가를 억제한다.

3. **Reopen-triggered heavy recomputation guard**
- 프론트의 gap auto-refresh를 project 단위 single-attempt로 제한해
  “프로젝트 재진입 시 refresh 재실행” 패턴을 차단한다.

4. **Gap analysis DB fallback path**
- GraphStore 초기화 실패 시에도 QueryExecutionAgent가 direct DB connection으로
  gap 질의를 수행하도록 fallback 경로를 유지해 핵심 질의 기능 중단을 방지한다.

5. **TF-IDF fallback memory guard**
- TF-IDF fallback 경로에 concept cap(1200), feature cap(64), `float32` 변환을 적용해
  임베딩 부재 환경에서의 메모리 피크를 제한한다.

6. **Heavy metrics endpoint TTL cache**
- `/api/graph/centrality/{project_id}`, `/api/graph/diversity/{project_id}`,
  `/api/graph/metrics/{project_id}` 결과를 short TTL(30s) + bounded cache(12 entries)로
  제공해 반복 재진입 시 CPU/메모리 재계산 부담을 줄인다.

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Frontend (Vercel)                          │
│                      Next.js 14 + React 18 + Three.js               │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │   Project   │  │   Graph     │  │    Chat     │  │    Gap     │ │
│  │   Manager   │  │   Canvas    │  │  Interface  │  │   Panel    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
│         │               │               │                │          │
│  ┌──────┴───────────────┴───────────────┴────────────────┴───────┐ │
│  │              State Management (Zustand + TanStack Query)       │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ REST API (HTTPS)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Backend (Render Docker)                        │
│                         FastAPI + Python 3.11+                       │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │               API Layer (FastAPI Routers)                    │   │
│  │  /projects  /graph  /entities  /gaps  /chat  /import        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│  ┌───────────────────────────┴───────────────────────────────────┐ │
│  │                     Service Layer                              │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │ │
│  │  │  Graph   │  │  Entity  │  │   Gap    │  │    Import    │  │ │
│  │  │ Service  │  │ Service  │  │ Service  │  │   Service    │  │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘  │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│  ┌───────────────────────────┴───────────────────────────────────┐ │
│  │                   6-Agent Pipeline                             │ │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────┐  │ │
│  │  │ Intent │→│Concept │→│  Task  │→│ Query  │→│  Reasoning │  │ │
│  │  │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │ │   Agent    │  │ │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────────┘  │ │
│  │                                              ↓                 │ │
│  │                                        ┌────────────┐         │ │
│  │                                        │  Response  │         │ │
│  │                                        │   Agent    │         │ │
│  │                                        └────────────┘         │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│  ┌───────────────────────────┴───────────────────────────────────┐ │
│  │                   Core Components                              │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐│ │
│  │  │   Entity     │  │     Gap      │  │    LLM Provider      ││ │
│  │  │  Extractor   │  │   Detector   │  │  (Groq/Claude/GPT)   ││ │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘│ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ asyncpg (Connection Pool)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 PostgreSQL 16 + pgvector (Supabase)                  │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    │
│  │ projects │  │ entities │  │  edges   │  │ structural_gaps  │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐   │
│  │ paper_metadata   │  │ zotero_sync_state│  │ teams           │   │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘   │
│                     │                                                │
│              vector column                                           │
│            (1536 dimensions)                                         │
└─────────────────────────────────────────────────────────────────────┘
```

**Reference Diagrams:**
- System Context: [`DOCS/architecture/diagrams/system-context.mmd`](diagrams/system-context.mmd)
- Full Architecture: [`DOCS/architecture/overview.md`](overview.md)

### 2.2 Technology Stack

#### Frontend
| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| Framework | Next.js (App Router) | 14.1.0 | SSR, routing, React framework |
| UI Library | React | 18.2.0 | Component-based UI |
| State Management | Zustand | 4.5.0 | Global state |
| Server State | TanStack Query | 5.17.0 | API caching, optimistic updates |
| Styling | Tailwind CSS | 3.4.1 | Utility-first CSS |
| 3D Visualization | Three.js + react-force-graph-3d | 0.160.0 | 3D force-directed graph |
| 2D Visualization | D3.js | 7.9.0 | Topic clustering, network analysis |
| Graph Editor | React Flow | 11.10.0 | Node-based canvas (legacy mode) |
| Charts | Recharts | (via d3) | Data visualization |
| Authentication | Supabase SSR | 0.8.0 | Auth state management |

#### Backend
| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| Framework | FastAPI | 0.109.0+ | Async web framework |
| Language | Python | 3.11+ | Backend logic |
| Database | PostgreSQL | 16 | Relational storage |
| Vector DB | pgvector | 0.2.4+ | Embedding storage, similarity search |
| DB Driver | asyncpg | 0.29.0+ | Async PostgreSQL driver |
| Validation | Pydantic | 2.6.0+ | Schema validation |
| LLM Provider (Default) | Groq | - | llama-3.3-70b-versatile |
| LLM Providers (Optional) | Anthropic, OpenAI, Google | - | Fallback providers |
| Embeddings | OpenAI | - | text-embedding-3-small (1536 dim) |
| Testing | pytest + pytest-asyncio | 8.0.0+ | Test framework |

#### Deployment
| Service | Platform | Type | URL |
|---------|----------|------|-----|
| Frontend | Vercel | Next.js | `https://schola-rag-graph.vercel.app` |
| Backend | Render | Docker | `https://scholarag-graph-docker.onrender.com` |
| Database | Supabase | PostgreSQL+pgvector | Managed |

---

## 3. Component Specifications

### 3.1 Backend Components

#### 3.1.1 6-Agent Pipeline

**Purpose**: Process user queries through a multi-stage RAG pipeline inspired by AGENTiGraph.

**Architecture**:
```
User Query → Intent Agent → Concept Agent → Task Agent → Query Agent → Reasoning Agent → Response Agent → Final Response
```

**Agent Specifications**:

| Agent | Input | Output | Model | Temperature |
|-------|-------|--------|-------|-------------|
| **1. Intent Agent** | User query string | Intent classification (SEARCH, EXPLORE, EXPLAIN, COMPARE, SUMMARIZE, IDENTIFY_GAPS) | Groq llama-3.3-70b | 0.3 |
| **2. Concept Agent** | User query + Intent | Extracted entities (Concept, Method, Finding, Paper, Author) | Groq llama-3.3-70b | 0.3 |
| **3. Task Agent** | Extracted entities + Intent | Task plan (DAG of subtasks) | Rule-based | N/A |
| **4. Query Agent** | Task plan | SQL queries + Vector searches | asyncpg + pgvector | N/A |
| **5. Reasoning Agent** | Query results | Chain-of-thought analysis | Groq llama-3.3-70b | 0.3 |
| **6. Response Agent** | Analysis + User context | Natural language response + Citations + Graph highlights | Groq llama-3.3-70b | 0.5 |

**Key Classes**:
```python
# backend/agents/orchestrator.py
class AgentOrchestrator:
    async def process_query(self, query: str, project_id: str) -> OrchestratorResult

# backend/agents/intent_agent.py
class IntentAgent:
    async def classify(self, query: str) -> IntentResult

# backend/agents/concept_extraction_agent.py
class ConceptExtractionAgent:
    async def extract(self, query: str) -> ExtractionResult

# backend/agents/reasoning_agent.py
class ReasoningAgent:
    async def analyze(self, query_results: QueryResults, context: ConversationContext) -> ReasoningOutput
```

**Data Flow**: See [`DOCS/architecture/multi-agent-system.md`](multi-agent-system.md) for detailed pipeline diagrams.

#### 3.1.2 Graph Processing

**Purpose**: Extract, disambiguate, and analyze knowledge graph entities from academic papers.

**Components**:

| Component | File | Responsibility |
|-----------|------|----------------|
| **Entity Extractor** | `backend/graph/entity_extractor.py` | Extract Concepts, Methods, Findings from paper abstracts using LLM |
| **Entity Disambiguator** | `backend/graph/entity_disambiguator.py` | Merge similar entities using embedding similarity (threshold: 0.9) |
| **Relationship Builder** | `backend/graph/relationship_builder.py` | Create edges between entities based on co-occurrence and semantic similarity |
| **Gap Detector** | `backend/graph/gap_detector.py` | Identify structural gaps using K-means clustering and connection matrix analysis |

**Entity Extraction Pipeline**:
```python
# Extraction Prompt Template
EXTRACTION_PROMPT = """
Analyze this academic paper and extract structured knowledge:

Title: {title}
Abstract: {abstract}

Extract:
1. concepts: Key theoretical concepts (max 10)
2. methods: Research methodologies (max 5)
3. findings: Key findings with effect sizes (max 5)

For each entity:
- name: Canonical name (lowercase, singular)
- definition: Brief definition in context
- confidence: 0.0-1.0 extraction confidence

Return ONLY valid JSON.
"""
```

**Gap Detection Algorithm**:
1. Cluster concepts using K-means (optimal K via elbow method)
2. Build inter-cluster connection matrix from edges
3. Identify gaps where connection strength < 0.1
4. Calculate semantic distance between gap clusters
5. Find bridge concepts using embedding similarity
6. Generate research questions using LLM

**v0.11.0 Enhancement**: Zotero RDF importer now includes full gap detection parity with ScholaRAG importer. After relationship building, the importer runs clustering, gap analysis, and centrality calculation automatically.

#### 3.1.3 Import Pipeline

**Purpose**: Import papers from multiple sources and construct knowledge graphs.

**Supported Import Types**:

| Type | Source | Format | Status |
|------|--------|--------|--------|
| **ScholaRAG** | Local folder | `papers_metadata.csv` + PDFs | ✅ Complete |
| **PDF Upload** | User upload | PDF files | ✅ Complete |
| **Zotero** | Zotero library | Hybrid (Local API → Web API) | ✅ Complete |

**ScholaRAG Import Flow**:
```
1. Validate folder structure
2. Read papers_metadata.csv
3. Extract entities from each paper (parallel)
4. Disambiguate entities (merge similar)
5. Build relationships (co-occurrence + semantic)
6. Calculate graph metrics (degree, betweenness)
7. Detect structural gaps
8. Store in PostgreSQL
```

**Zotero Hybrid Import** (ADR-002):
- **Local API First**: Connect to Zotero desktop app via HTTP (localhost:23119)
- **Web API Fallback**: Use Zotero Web API if local unavailable
- **Sync State**: Track last sync timestamp to enable incremental updates

#### 3.1.4 LLM Provider Management

**Default Provider**: Groq (llama-3.3-70b-versatile)

**Rationale**:
- **Cost**: Free tier (14,400 req/day)
- **Speed**: 67 tokens/second for 70B model
- **Quality**: Comparable to Claude 3.5 Haiku

**Provider Priority**:
```
1. Groq (default)
2. Anthropic (fallback)
3. OpenAI (fallback)
4. Google (fallback)
```

**Environment Variables**:
```env
# Primary LLM
GROQ_API_KEY=gsk_...
DEFAULT_LLM_PROVIDER=groq
DEFAULT_LLM_MODEL=llama-3.3-70b-versatile

# Embedding Provider (separate)
OPENAI_API_KEY=sk-...  # Only for embeddings

# Optional Fallbacks
ANTHROPIC_API_KEY=sk-ant-...
```

**Rate Limiting**:
```python
# Groq Free Tier
MAX_REQUESTS_PER_DAY = 14400
MAX_REQUESTS_PER_MINUTE = 10  # 14400 / (24*60)

# Implementation
llm_provider = GroqProvider(
    api_key=settings.groq_api_key,
    requests_per_minute=10
)
```

**Fallback Strategy**:
```python
async def get_llm_response(prompt: str) -> str:
    for provider in ["groq", "anthropic", "openai"]:
        try:
            return await llm_provider.generate(prompt)
        except Exception as e:
            logger.warning(f"{provider} failed: {e}")
            continue
    # Final fallback: keyword-based rules
    return fallback_response(prompt)
```

**Full Details**: See [`DOCS/development/LLM_CONFIGURATION.md`](../development/LLM_CONFIGURATION.md)

### 3.2 Frontend Components

#### 3.2.1 Pages

**Directory**: `frontend/app/`

| Page | Route | Purpose |
|------|-------|---------|
| **Home** | `/` | Landing page, project list |
| **Project Detail** | `/projects/[id]` | Graph visualization + Chat interface |
| **Import** | `/import` | Upload papers (ScholaRAG/PDF/Zotero) |
| **Team Management** | `/teams` | Manage teams and project sharing |
| **Login** | `/login` | Supabase authentication |

#### 3.2.2 Graph Visualization

**Purpose**: Three interactive view modes for exploring knowledge graphs.

**View Modes**:

| Mode | Component | Technology | Use Case |
|------|-----------|------------|----------|
| **3D View** | `Graph3D.tsx` | Three.js + react-force-graph-3d | Full graph exploration with physics simulation |
| **Topic View** | `TopicViewMode.tsx` | D3.js force layout | Topic clustering and community detection |
| **Gaps View** | `GapsViewMode.tsx` | Three.js + Ghost Edges | Research gap identification with AI hypotheses |

**3D View Specifications**:
```typescript
// frontend/components/graph/Graph3D.tsx
interface Graph3DProps {
  nodes: Node[];
  edges: Edge[];
  onNodeClick: (node: Node) => void;
}

// Force simulation parameters (v0.9.0 optimized)
{
  charge: -30,              // Node repulsion
  linkDistance: 50,          // Edge length
  gravity: 0.1,             // Center pull
  iterations: 100,          // Stabilization iterations
  d3VelocityDecay: 0.4,    // v0.9.0: Slower decay for natural movement
  cooldownTicks: 1000,      // v0.9.0: Extended simulation time
  warmupTicks: 100          // v0.9.0: Pre-stabilization
}

// v0.9.0: InfraNodus-style label configuration
LABEL_CONFIG = {
  minFontSize: 10,                 // Smallest label font
  maxFontSize: 28,                 // Largest label font
  minOpacity: 0.3,                 // Least visible label
  maxOpacity: 1.0,                 // Most visible label
  alwaysVisiblePercentile: 0.8,    // Top 20% always show
  hoverRevealPercentile: 0.5       // Top 50% on hover
}

// v0.11.0: Hover debounce
- hoveredNodeRef: useRef for deduplication
- hoverTimeoutRef: 50ms debounce before state update
- ~90% reduction in React re-renders during hover

// Rendering (v0.9.0 updated)
- Node size: 5-15 (scaled by degree centrality)
- Node color: Cluster-based (12 colors, hash-assigned)
- Edge opacity: 0.3-0.7 (scaled by weight)
- Highlighted nodes: Yellow glow effect
- Labels: Centrality-based visibility with shadow (no background box)
- Drag release: Nodes float back naturally (fx/fy/fz = undefined)
```

**Topic View Specifications**:
```typescript
// frontend/components/graph/TopicViewMode.tsx
interface TopicViewProps {
  nodes: Node[];
  edges: Edge[];
  clusters: Cluster[];
}

// D3 force layout
{
  forceLink: d3.forceLink().distance(100),
  forceCharge: d3.forceManyBody().strength(-300),
  forceCenter: d3.forceCenter(width/2, height/2),
  forceCollide: d3.forceCollide().radius(30)
}

// Clustering
- Algorithm: Louvain (community detection)
- Visual grouping: Convex hull around clusters
- Zoom levels: 0.5x - 3x (semantic zoom)
```

**Gaps View Specifications**:
```typescript
// frontend/components/graph/GapsViewMode.tsx
interface GapsViewProps {
  nodes: Node[];
  edges: Edge[];
  gaps: StructuralGap[];
}

// Ghost edges (potential connections)
{
  color: "rgba(255, 255, 0, 0.3)",  // Semi-transparent yellow
  style: "dashed",
  width: 2
}

// AI Bridge Hypotheses
- Triggered on gap click
- Backend: POST /api/graph/gaps/{id}/generate-bridge
- LLM generates 3-5 bridge concepts
- Displayed as tooltip overlays
```

**Full Details**: See [`DOCS/development/VIEW_MODES_REFERENCE.md`](../development/VIEW_MODES_REFERENCE.md)

#### 3.2.3 Frontend Dependency Management (v0.7.0)

**Purpose**: Ensure stable builds and prevent breaking changes from transitive dependencies.

**Critical Dependencies** (Three.js ecosystem):

| Package | Pinned Version | Role |
|---------|----------------|------|
| `three` | `0.152.2` | Core 3D rendering engine |
| `react-force-graph-3d` | `1.21.3` | React wrapper for 3D force graphs |
| `3d-force-graph` | `1.70.0` (override) | Force-directed graph layout |
| `three-render-objects` | `1.26.5` (override) | Three.js rendering utilities |
| `three-forcegraph` | `1.38.0` (override) | Force graph visualization |

**npm Overrides Strategy**:

```json
// package.json
{
  "dependencies": {
    "react-force-graph-3d": "1.21.3",  // Exact version
    "three": "0.152.2"                   // Exact version
  },
  "overrides": {
    "three": "0.152.2",
    "three-render-objects": "1.26.5",
    "three-forcegraph": "1.38.0",
    "3d-force-graph": "1.70.0"
  }
}
```

**webpack Configuration** (next.config.js):

```javascript
// Resolve ESM imports for three/examples/jsm/*
webpack: (config) => {
  const path = require('path');
  const webpack = require('webpack');
  const threePackageRoot = path.join(
    path.dirname(require.resolve('three')), '..'
  );

  // Single Three.js instance
  config.resolve.alias = {
    ...config.resolve.alias,
    three: require.resolve('three'),
  };

  // Rewrite three/examples/jsm/* paths
  config.plugins.push(
    new webpack.NormalModuleReplacementPlugin(
      /^three\/examples\/jsm\/.+/,
      (resource) => {
        const subPath = resource.request.replace(/^three\//, '');
        resource.request = path.join(threePackageRoot, subPath);
      }
    )
  );

  return config;
}
```

**Why This Matters**:

```
Problem: ESM Module Resolution Failure
┌─────────────────────────────────────────────────────────────────┐
│  react-force-graph-3d@1.29.0 (latest)                          │
│    └── 3d-force-graph@1.79.0                                   │
│        └── three-render-objects@1.40.4                         │
│            └── import from 'three/examples/jsm/...'            │
│                └── ❌ webpack can't resolve ESM subpath        │
└─────────────────────────────────────────────────────────────────┘

Solution: Pin to stable versions + webpack path rewriting
┌─────────────────────────────────────────────────────────────────┐
│  react-force-graph-3d@1.21.3 (pinned)                          │
│    └── 3d-force-graph@1.70.0 (override)                        │
│        └── three-render-objects@1.26.5 (override)              │
│            └── import from 'three/examples/jsm/...'            │
│                └── ✅ webpack NormalModuleReplacementPlugin    │
└─────────────────────────────────────────────────────────────────┘
```

**Dependency Update Protocol**:

1. **Test locally first**: `npm run build`
2. **Verify version tree**: `npm ls three three-render-objects 3d-force-graph`
3. **Never use `^` or `~`** for Three.js ecosystem packages
4. **Monitor Vercel builds** after any dependency change
5. **Document changes** in this section and release notes

#### 3.2.4 State Management

**Global State** (Zustand):
```typescript
// frontend/lib/store.ts
interface GraphStore {
  nodes: Node[];
  edges: Edge[];
  selectedNode: Node | null;
  filters: FilterState;
  viewMode: "3d" | "topic" | "gaps";

  // Actions
  setNodes: (nodes: Node[]) => void;
  selectNode: (node: Node) => void;
  updateFilters: (filters: Partial<FilterState>) => void;
  setViewMode: (mode: string) => void;
}
```

**Server State** (TanStack Query):
```typescript
// frontend/lib/api.ts
const useProject = (projectId: string) => {
  return useQuery({
    queryKey: ["project", projectId],
    queryFn: () => fetchProject(projectId),
    staleTime: 5 * 60 * 1000,  // 5 minutes
    cacheTime: 30 * 60 * 1000  // 30 minutes
  });
};

const useGraphData = (projectId: string) => {
  return useQuery({
    queryKey: ["graph", projectId],
    queryFn: () => fetchGraphData(projectId),
    staleTime: 10 * 60 * 1000  // 10 minutes
  });
};
```

### 3.3 Database Schema

**Database**: PostgreSQL 16 + pgvector
**Hosting**: Supabase

#### 3.3.1 Core Tables

**Projects Table**:
```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Entities Table** (Concepts, Methods, Findings):
```sql
CREATE TYPE entity_type AS ENUM (
    'Paper', 'Author', 'Concept', 'Method', 'Finding'
);

CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    entity_type entity_type NOT NULL,
    name VARCHAR(500) NOT NULL,
    name_normalized VARCHAR(500),
    definition TEXT,
    properties JSONB DEFAULT '{}',
    embedding vector(1536),          -- OpenAI embeddings
    centrality_degree FLOAT DEFAULT 0,
    centrality_betweenness FLOAT DEFAULT 0,
    cluster_id INTEGER,
    source_papers JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_entities_project ON entities(project_id);
CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_embedding ON entities
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

**Relationships Table** (Edges):
```sql
CREATE TYPE relationship_type AS ENUM (
    'AUTHORED_BY', 'CITES', 'DISCUSSES_CONCEPT',
    'USES_METHOD', 'HAS_FINDING', 'RELATED_TO', 'CO_OCCURS'
);

CREATE TABLE relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    source_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    target_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type relationship_type NOT NULL,
    weight FLOAT DEFAULT 1.0,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_id, target_id, relationship_type)
);

-- Indexes
CREATE INDEX idx_relationships_source ON relationships(source_id);
CREATE INDEX idx_relationships_target ON relationships(target_id);
CREATE INDEX idx_relationships_type ON relationships(relationship_type);
```

**Structural Gaps Table**:
```sql
CREATE TABLE structural_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    cluster_a_id INTEGER NOT NULL,
    cluster_b_id INTEGER NOT NULL,
    gap_strength FLOAT NOT NULL,
    semantic_distance FLOAT,
    bridge_concepts JSONB DEFAULT '[]',
    research_questions JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Full Schema**: See [`DOCS/architecture/database-schema.md`](database-schema.md)

#### 3.3.2 pgvector Usage

**Embedding Search**:
```sql
-- Find similar entities by embedding
SELECT *,
       1 - (embedding <=> $1) as similarity
FROM entities
WHERE project_id = $2
  AND embedding IS NOT NULL
  AND 1 - (embedding <=> $1) > 0.7  -- Similarity threshold
ORDER BY embedding <=> $1
LIMIT 10;
```

**Index Type**: HNSW (Hierarchical Navigable Small World)
- **Parameters**: m=16, ef_construction=64
- **Operator**: `<=>` (cosine distance)
- **Performance**: ~10ms for 10K vectors

---

## 4. Data Flow Diagrams

### 4.1 Import Flow

```
User uploads ScholaRAG folder
         ↓
[Backend] Validate folder structure
         ↓
[Backend] Read papers_metadata.csv
         ↓
[Backend] For each paper:
         ├─ Extract entities (LLM)
         ├─ Generate embeddings (OpenAI)
         └─ Store paper_metadata row
         ↓
[Backend] Entity disambiguation
         ├─ Group by embedding similarity
         ├─ Merge clusters (threshold: 0.9)
         └─ Update entities table
         ↓
[Backend] Relationship building
         ├─ Co-occurrence edges (same paper)
         ├─ Semantic edges (embedding similarity)
         └─ Store relationships table
         ↓
[Backend] Graph metrics calculation
         ├─ Degree centrality
         ├─ Betweenness centrality
         ├─ Community detection (Louvain)
         └─ Update entities.properties
         ↓
[Backend] Gap detection
         ├─ K-means clustering
         ├─ Inter-cluster connection matrix
         ├─ Identify weak connections
         ├─ Find bridge concepts
         ├─ Generate research questions (LLM)
         └─ Store structural_gaps table
         ↓
[Backend] Return import_job_id
         ↓
[Frontend] Poll /api/import/status/{job_id}
         ↓
[Frontend] Display success + redirect to project
```

### 4.2 Query Flow (6-Agent Pipeline)

```
User sends query: "What methods are used to study chatbot effectiveness?"
         ↓
[Backend] Intent Agent
         ├─ Classify intent: "METHOD_ANALYSIS"
         ├─ Extract domain: "effectiveness"
         └─ Confidence: 0.95
         ↓
[Backend] Concept Agent
         ├─ Extract entities: ["chatbot", "effectiveness", "methods"]
         ├─ Match to graph entities via embedding search
         └─ Return matched_ids: [uuid1, uuid2, uuid3]
         ↓
[Backend] Task Agent
         ├─ Intent: METHOD_ANALYSIS
         ├─ Plan tasks:
         │   ├─ Task 1: Search methods related to "chatbot"
         │   ├─ Task 2: Filter by "effectiveness" context
         │   └─ Task 3: Rank by usage count
         └─ Generate DAG (no dependencies, run parallel)
         ↓
[Backend] Query Agent
         ├─ Execute Task 1: SQL query for methods
         │   SELECT * FROM entities WHERE entity_type='Method' AND ...
         ├─ Execute Task 2: Vector search for "effectiveness"
         │   SELECT * FROM entities WHERE embedding <=> $1 < 0.3
         ├─ Execute Task 3: Count relationships
         │   SELECT method_id, COUNT(*) FROM relationships GROUP BY method_id
         └─ Combine results
         ↓
[Backend] Reasoning Agent
         ├─ Chain-of-thought analysis:
         │   Step 1: "RCT appears in 23 papers"
         │   Step 2: "Pre/post-test in 15 papers"
         │   Step 3: "Most common for chatbot effectiveness studies"
         └─ Final conclusion: "RCT is most prevalent..."
         ↓
[Backend] Response Agent
         ├─ Generate natural language response
         ├─ Add citations (papers containing methods)
         ├─ Highlight graph nodes (methods)
         ├─ Suggest follow-ups:
         │   "Show me RCT chatbot papers"
         │   "Compare RCT vs pre/post-test"
         │   "What are the limitations of RCT?"
         └─ Return OrchestratorResult
         ↓
[Frontend] Display response in chat
         ├─ Render markdown response
         ├─ Show citation list
         ├─ Highlight nodes in graph (yellow glow)
         └─ Display follow-up buttons
```

### 4.3 Graph Visualization Flow

```
User navigates to /projects/{id}
         ↓
[Frontend] Fetch graph data
         ├─ GET /api/graph/{project_id}
         ├─ Returns: { nodes: [...], edges: [...], metrics: {...} }
         └─ Cache in TanStack Query (10 min stale time)
         ↓
[Frontend] User selects view mode
         ├─ 3D View → Graph3D.tsx
         ├─ Topic View → TopicViewMode.tsx
         └─ Gaps View → GapsViewMode.tsx
         ↓
[Case: 3D View]
         ├─ Initialize Three.js scene
         ├─ Apply force simulation
         │   ├─ Charge force (repulsion)
         │   ├─ Link force (edge constraints)
         │   └─ Center force (gravity)
         ├─ Render nodes as spheres (size by degree)
         ├─ Render edges as lines (opacity by weight)
         ├─ User interaction:
         │   ├─ Click node → Highlight neighbors
         │   ├─ Drag node → Update position
         │   └─ Scroll → Zoom camera
         └─ Maintain 60 FPS
         ↓
[Case: Topic View]
         ├─ Run Louvain clustering (if not cached)
         ├─ Layout with D3 force simulation
         ├─ Draw cluster boundaries (convex hull)
         ├─ Color nodes by cluster
         └─ Enable semantic zoom (0.5x-3x)
         ↓
[Case: Gaps View]
         ├─ Fetch structural gaps: GET /api/graph/gaps/{project_id}
         ├─ Render nodes + edges (same as 3D)
         ├─ Add ghost edges for gaps (dashed yellow)
         ├─ User clicks gap → POST /api/graph/gaps/{id}/generate-bridge
         ├─ LLM generates bridge concepts
         ├─ Display as tooltip overlay
         └─ Allow "add to graph" action
```

---

## 5. API Contracts

### 5.1 Key Endpoints

**Base URL**: `https://scholarag-graph-docker.onrender.com`

#### Project Management

```
GET /api/projects
Response: { projects: [{ id, name, description, paper_count, created_at }] }

POST /api/projects
Request: { name, description }
Response: { project: { id, name, ... } }

GET /api/projects/{id}
Response: { project: { id, name, description, config, stats } }
```

#### Graph Data

```
GET /api/graph/{project_id}
Response: {
  nodes: [{ id, label, type, degree, betweenness, cluster_id, properties }],
  edges: [{ id, source, target, weight, type }],
  metrics: { node_count, edge_count, density, modularity }
}

GET /api/graph/visualization/{project_id}
Query: ?max_nodes=1000&max_nodes_le=5000  # v0.11.0: default 1000 (was 200)
# ORDER BY prioritizes academic entities (Concept/Method/Finding=1) over Paper/Author(=5)
Response: {
  nodes: [{ id, label, size, color, x, y, z }],
  edges: [{ source, target, opacity }],
  clusters: [{ id, nodes: [], centroid: [x,y,z] }]
}
```

#### Gap Analysis

```
GET /api/graph/gaps/{project_id}
Query: ?min_strength=0.5&limit=10
Response: {
  gaps: [{
    id, cluster_a_id, cluster_b_id, gap_strength,
    semantic_distance, bridge_concepts, research_questions
  }]
}

POST /api/graph/gaps/{id}/generate-bridge
Response: {
  bridge_hypotheses: [
    { concept: "active learning", relevance: 0.85, reasoning: "..." },
    { concept: "peer feedback", relevance: 0.78, reasoning: "..." }
  ]
}

GET /api/graph/gaps/{project_id}/recommendations
Query: ?min_strength=0.6&max_recommendations=5
Response: {
  recommendations: [{
    gap_id, cluster_a_names, cluster_b_names, gap_strength,
    recommended_papers: [{
      paper_id, title, authors, year, relevance_score, reason
    }]
  }]
}

GET /api/graph/gaps/{project_id}/export
Query: ?format=markdown
Response: Markdown file download
Content-Type: text/markdown
Content-Disposition: attachment; filename="gap_report_ProjectName.md"
```

#### Chat (6-Agent RAG)

```
POST /api/chat/query
Request: {
  query: "What methods are used?",
  project_id: "uuid",
  conversation_id: "uuid" (optional)
}
Response: {
  content: "The most common methods are...",
  citations: ["paper_id_1", "paper_id_2"],
  highlighted_nodes: ["node_id_1", "node_id_2"],
  highlighted_edges: ["edge_id_1"],
  suggested_follow_ups: ["Show me papers using RCT", "Compare methods"]
}

POST /api/chat/explain/{node_id}
Request: { node_name?: string, node_type?: string }
Response: {
  explanation: "Detailed explanation of the concept...",
  related_concepts: ["concept1", "concept2"],
  source_papers: ["paper_id_1", "paper_id_2"]
}
Note: v0.9.0 - Uses node_name/node_type for user-friendly explanation.
      Falls back to DB lookup if not provided.
```

#### Import

```
POST /api/import/scholarag
Request: multipart/form-data { folder: File }
Response: { import_job_id: "uuid" }

GET /api/import/status/{job_id}
Response: {
  status: "processing" | "completed" | "failed",
  progress: 75,
  total_papers: 100,
  processed_papers: 75,
  error_message: null
}
```

#### Health Check

```
GET /health
Response: {
  status: "healthy",
  database: "connected",
  llm_provider: "groq",
  version: "0.5.0"
}
```

**Full API Documentation**: See [`DOCS/api/overview.md`](../api/overview.md)

---

## 6. Deployment Architecture

### 6.1 Production Environment

| Service | Platform | Type | URL | Resources |
|---------|----------|------|-----|-----------|
| **Frontend** | Vercel | Next.js | `https://schola-rag-graph.vercel.app` | Serverless (Auto-scale) |
| **Backend** | Render | Docker | `https://scholarag-graph-docker.onrender.com` | 1 vCPU, 2GB RAM |
| **Database** | Supabase | PostgreSQL 16 + pgvector | Managed | Starter Plan |

### 6.2 Docker Configuration

**Backend Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc g++ libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**render.yaml**:
```yaml
services:
  - type: web
    name: scholarag-graph-docker
    env: docker
    dockerfilePath: ./Dockerfile
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: scholarag-db
          property: connectionString
      - key: GROQ_API_KEY
        sync: false
      - key: OPENAI_API_KEY
        sync: false
      - key: CORS_ORIGINS
        value: https://schola-rag-graph.vercel.app,http://localhost:3000
```

### 6.3 Environment Variables

**Backend (Render)**:
```env
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Authentication
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...

# LLM Providers
GROQ_API_KEY=gsk_...
DEFAULT_LLM_PROVIDER=groq
DEFAULT_LLM_MODEL=llama-3.3-70b-versatile

# Embeddings
OPENAI_API_KEY=sk-...

# CORS (CRITICAL)
CORS_ORIGINS=https://schola-rag-graph.vercel.app,https://scholarag-graph.vercel.app,http://localhost:3000

# Environment
ENVIRONMENT=production
```

**Frontend (Vercel)**:
```env
NEXT_PUBLIC_API_URL=https://scholarag-graph-docker.onrender.com
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

### 6.4 CORS Configuration

**Critical**: Backend must whitelist frontend URLs in `CORS_ORIGINS`.

**Implementation**:
```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Common Issue**: CORS errors after frontend URL change.
**Solution**: Update `CORS_ORIGINS` in Render Dashboard → Environment Variables.

### 6.5 Auto-Deploy Configuration

**Status**: ❌ **DISABLED** (INFRA-006)

**Reason**: Auto-deploy causes server restarts during import operations, killing background tasks (BUG-028).

**Deployment Process**:
1. Go to Render Dashboard → `scholarag-graph-docker`
2. Click "Manual Deploy" → "Deploy latest commit"
3. ⚠️ Ensure no imports are running before deploying

---

## 7. Change Log

### Version 0.12.0 (2026-02-07) - Current

**Gap Analysis Enhancement Release (3 features)**:

- **LLM-Summarized Cluster Labels**: `_generate_cluster_label()` in `GapDetector` uses LLM to generate 3-5 word topic labels from cluster keywords with 5s timeout and keyword-join fallback. LLM injected into `refresh_gap_analysis` via `get_llm_provider()`.
- **Gap-Based Paper Recommendations**: `GET /gaps/{project_id}/recommendations/{gap_id}` queries Semantic Scholar using bridge candidates and cluster names. 15s timeout, graceful empty-result fallback. Frontend "Find Papers" button in GapPanel with recommendation cards.
- **Gap Analysis Report Export**: `GET /gaps/{project_id}/export` generates Markdown report with cluster table, structural gaps, bridge candidates, and research questions. StreamingResponse with file attachment. Frontend "Export Report" button in GapPanel.

Files changed: `backend/graph/gap_detector.py`, `backend/routers/graph.py`, `frontend/lib/api.ts`, `frontend/components/graph/GapPanel.tsx`

### Version 0.11.1 (2026-02-06)

**Production Bug Fix Release (5 issues)**:

*CRITICAL (P0)*:
- GraphStore initialization: Enhanced error logging with traceback in `chat.py`; gap analysis agent rewritten with real DB queries (`structural_gaps`, `entities`, `relationships` tables)
- Embedding/Gap detection: TF-IDF fallback when embeddings unavailable (sklearn `TfidfVectorizer`); explicit error reporting on embedding failure; gap refresh endpoint with TF-IDF path

*HIGH (P1)*:
- Topics tab visibility: Tab bar contrast improved (`bg-ink/15` + border), inactive tab text `text-ink/70`
- Node hover jitter: Physics simulation freeze after stabilization (`cooldownTicks` 1000→200, `d3VelocityDecay` 0.4→0.75, `onEngineStop` pins all nodes via `fx/fy/fz`)

*MEDIUM (P2)*:
- Draggable panels: New `DraggablePanel` component with localStorage persistence, viewport clamping; applied to GapPanel, CentralityPanel, ClusterPanel, InsightHUD

*Memory Stabilization (carried from earlier patch)*:
- Visualization edge cap (`max_edges` default 15000)
- Centrality cache LRU bounding (max 20 entries)
- Gap auto-refresh single-attempt per session
- QueryExecutionAgent DB fallback when GraphStore is unavailable
- TF-IDF fallback guardrails (concept cap 1200, feature cap 64, float32 vectors)
- Heavy metrics endpoint TTL cache (30s, max 12 entries, project-scoped invalidation on refresh/recluster)

### Version 0.11.0 (2026-02-06)

**Comprehensive Bug Fix & UX Enhancement Release (11 issues)**:

*CRITICAL*:
- Visualization API `max_nodes` default 200→1000 (max 5000), ORDER BY prioritizes academic entities
- Zotero importer gap detection parity: clustering + gap analysis + centrality after import

*HIGH*:
- AI-powered relationship evidence: LLM explanation fallback when no text chunks exist
- Gap Panel drag-to-resize (256-500px range)
- Dynamic chat questions based on graph data (replaces hardcoded questions)
- Bridge Ideas error categorization (LLM/network/not-found)
- Cluster label UUID detection with keyword-based fallback names

*MEDIUM*:
- Node hover 50ms debounce eliminates jitter (~90% fewer state updates)
- View mode toggle redesigned as tab-bar with rounded styling
- Panel layout flex-based stacking prevents overlap

*LOW*:
- All toolbar tooltips translated to Korean

### Version 0.10.2 (2026-02-06)

**Stability / Memory Hardening**:
- Import progress path now uses coalesced async update workers instead of per-callback fan-out tasks
- Zotero checkpoint persistence now uses queued, serialized writes to reduce concurrent write pressure
- Legacy in-memory import job cleanup policy added (terminal-state + age-based cleanup)
- Periodic maintenance loop extended to include quota buffer flush and old job cleanup
- Shutdown lifecycle now flushes quota buffers and performs import/job cleanup before exit

**Frontend Runtime Efficiency**:
- ImportProgress polling changed from interval-based to single-flight timeout loop
- StatusBar polling changed to visibility-aware timeout loop
- Graph3D monitoring intervals reduced (position save and camera checks) with hidden-tab skip

**Testing/Documentation Alignment**:
- New TDD baseline document created: `DOCS/testing/TDD.md`
- SDD-TDD traceability updated for release verification criteria

### Version 0.9.0 (2026-02-04)

**Major Features**:
- InfraNodus-style labeling: centrality-based visibility (top 20% always visible), dynamic font sizing (10-28px), opacity gradient (0.3-1.0)
- Graph physics optimization: velocity decay 0.4, cooldown 1000 ticks for stable, natural node movement
- AI Explain uses concept names instead of raw UUIDs (node_name/node_type passed to explain endpoint)
- Gap auto-refresh: automatic re-detection when clusters exist but no gaps found (min_gaps=3)
- Evidence query stabilization: escape_sql_like + classified error handling (error_code field)
- Korean tooltips for all 14 toolbar buttons

**Bug Fixes**:
- Fixed graph shrinkage after simulation (d3VelocityDecay 0.9→0.4)
- Fixed nodes stuck after drag (fx/fy/fz = undefined on drag end)
- Fixed "No Gaps Detected" when clusters exist
- Fixed Evidence 500 errors from unescaped SQL LIKE patterns

**Removed**:
- Particle effects (lightning toggle and particle rendering completely removed from code, store, and UI)

### Version 0.8.0 (2026-02-04)

**Features**:
- Label visibility toggle: toolbar button cycles none/important/all modes
- Node removal preview: visual preview before applying centrality-based slicing
- InsightHUD repositioning: moved to right-side (InfraNodus-style layout)
- Hash-based cluster color assignment for consistent colors across refreshes

**Bug Fixes**:
- EdgeContextModal accessibility: ESC key, focus trap, ARIA attributes
- Evidence API stability: table existence check prevents 500 errors
- Cluster color stability: hashClusterId() for deterministic color mapping

**Technical**:
- LabelVisibility type with cycleLabelVisibility() store action
- Dynamic panel stacking for InsightHUD positioning

### Version 0.5.0 (2026-02-04)

**Major Features**:
- 6-Agent RAG pipeline (Intent → Concept → Task → Query → Reasoning → Response)
- Three view modes (3D, Topic, Gaps)
- Groq LLM integration as default provider
- InfraNodus-style gap detection with AI bridge hypotheses
- ScholaRAG folder import
- Zotero hybrid import (Local API + Web API)
- Team collaboration features

**Technical Improvements**:
- Migrated backend to Render Docker (from Python service)
- PostgreSQL 16 + pgvector for vector search
- Supabase authentication integration
- HNSW index for embedding search (m=16, ef_construction=64)

**Known Issues**:
- Auto-deploy disabled to prevent import interruption (INFRA-006)
- Graph visualization performance degrades above 500 nodes

### Version 0.7.0 (2026-02-04)

**Features**:
- **Node Pinning**: Click to pin nodes, Shift+click for multi-select
- **Adaptive Labeling**: Zoom-responsive label visibility
- **Graph-to-Prompt**: Export graph context as structured prompt

**Bug Fixes**:
- Fixed 'focused' diversity rating type error (BUG-041)
- Resolved Three.js ESM module resolution for Vercel builds (BUG-042)

**Technical**:
- Added Frontend Dependency Management section (§3.2.3)
- webpack NormalModuleReplacementPlugin for ESM paths
- Pinned Three.js ecosystem to stable versions

### Version 0.4.0 (2026-01-20)

**Features**:
- Added Topic View mode with D3.js clustering
- Implemented Gaps View mode with ghost edges
- Added PRISMA 2020 diagram generation

**Technical**:
- Louvain community detection algorithm
- Structural gap detection with K-means clustering

### Version 0.3.0 (2026-01-15)

**Features**:
- ScholaRAG folder import
- PDF upload and entity extraction

**Technical**:
- Entity disambiguation using embedding similarity
- Relationship builder with co-occurrence and semantic edges

### Version 0.2.0 (2026-01-10)

**Features**:
- Basic knowledge graph visualization (3D only)
- Manual entity creation

**Technical**:
- PostgreSQL schema with pgvector extension
- FastAPI backend setup

### Version 0.1.0 (2026-01-01)

**Initial Release**:
- Project scaffolding
- Basic authentication

---

## Appendices

### Appendix A: Related Documents

| Document | Purpose | Location |
|----------|---------|----------|
| **Architecture Overview** | High-level system design | [`DOCS/architecture/overview.md`](overview.md) |
| **Multi-Agent System** | 6-Agent pipeline details | [`DOCS/architecture/multi-agent-system.md`](multi-agent-system.md) |
| **Database Schema** | Full PostgreSQL schema | [`DOCS/architecture/database-schema.md`](database-schema.md) |
| **LLM Configuration** | Groq setup guide | [`DOCS/development/LLM_CONFIGURATION.md`](../development/LLM_CONFIGURATION.md) |
| **View Modes Reference** | Frontend visualization guide | [`DOCS/development/VIEW_MODES_REFERENCE.md`](../development/VIEW_MODES_REFERENCE.md) |
| **API Documentation** | REST API reference | [`DOCS/api/overview.md`](../api/overview.md) |

### Appendix B: Glossary

| Term | Definition |
|------|------------|
| **Concept-Centric Graph** | Knowledge graph where concepts are first-class entities; papers are metadata |
| **Entity** | Node in the knowledge graph (Concept, Method, Finding, Paper, Author) |
| **Relationship** | Edge connecting two entities (DISCUSSES_CONCEPT, USES_METHOD, etc.) |
| **Structural Gap** | Weak connection between two clusters of concepts, indicating research gap |
| **Bridge Concept** | Potential entity that could connect two gap clusters |
| **Ghost Edge** | Visualization of a potential (non-existent) relationship in Gaps View |
| **Embedding** | 1536-dimensional vector representation of text (OpenAI text-embedding-3-small) |
| **HNSW** | Hierarchical Navigable Small World; fast approximate nearest neighbor search |
| **pgvector** | PostgreSQL extension for vector operations and similarity search |
| **Louvain Algorithm** | Community detection algorithm for graph clustering |
| **InfraNodus** | Text network visualization tool; inspiration for gap detection |
| **PRISMA 2020** | Reporting guideline for systematic reviews |

### Appendix C: Performance Benchmarks

| Operation | Input Size | Time | Notes |
|-----------|------------|------|-------|
| Entity Extraction | 100 papers | ~2 min | Groq LLM, parallel processing |
| Entity Disambiguation | 1000 entities | ~5 sec | Embedding similarity, threshold 0.9 |
| Gap Detection | 500 concepts | ~3 sec | K-means + connection matrix |
| Graph Rendering (3D) | 100 nodes, 200 edges | ~1.5 sec | Three.js, 60 FPS |
| Graph Rendering (3D) | 500 nodes, 1000 edges | ~4 sec | 30-40 FPS (v0.11.0: jitter-free hover) |
| Vector Search | 10K entities | ~10 ms | HNSW index, 10 results |
| Query Response (6-Agent) | Average query | ~3 sec | Groq LLM, includes reasoning |

### Appendix D: Security Considerations

| Area | Current Status | Planned Improvements |
|------|----------------|----------------------|
| **Authentication** | Supabase JWT tokens | ✅ Production-ready |
| **Authorization** | Role-based (team member, owner) | Add guest access (read-only) |
| **API Security** | CORS, rate limiting (planned) | Implement API key rotation |
| **Data Encryption** | HTTPS, DB encryption at rest | ✅ Production-ready |
| **Input Validation** | Pydantic schemas | Add XSS sanitization for chat |
| **SQL Injection** | Parameterized queries (asyncpg) | ✅ Safe |

---

**Document End**

**Last Updated**: 2026-02-06
**Next Review**: 2026-05-06
**Maintained By**: ScholaRAG_Graph Development Team
