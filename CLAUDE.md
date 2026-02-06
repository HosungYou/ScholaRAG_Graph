# CLAUDE.md - ScholaRAG_Graph Project Instructions

> **Last Updated**: 2026-02-06
> **Version**: 3.6.0 (v0.11.0 Comprehensive Bug Fix & UX Enhancement)

## Project Overview

ScholaRAG_Graph is an AGENTiGraph-style **Concept-Centric Knowledge Graph** platform. It visualizes systematic literature review data as a Knowledge Graph with Multi-Agent conversational exploration.

### Key Features
- **Concept-Centric Graph**: Papers/Authors as metadata only; Concepts/Methods/Findings visualized
- **Multi-Agent RAG**: 6-Agent pipeline for query processing
- **Zotero Integration**: Hybrid Import (Local API + Web API)
- **Team Collaboration**: Project sharing and collaboration
- **PRISMA 2020**: Automatic systematic review diagram generation

---

## Architecture

### Backend (FastAPI + Python 3.11+)
```
backend/
├── agents/           # 6-Agent pipeline
├── graph/            # Knowledge Graph processing
├── importers/        # Data importers
├── integrations/     # External APIs (Zotero, Semantic Scholar, OpenAlex)
├── auth/             # Supabase authentication
├── jobs/             # Background tasks
├── llm/              # Multi-Provider LLM
└── routers/          # API endpoints
```

### Frontend (Next.js 14 + React Flow)
```
frontend/
├── app/              # Pages (projects, import, auth)
├── components/       # UI components (graph, chat, auth, teams)
└── lib/              # API client, auth context
```

### Database (PostgreSQL + pgvector + Supabase)
Key Tables: `projects`, `paper_metadata`, `entities`, `relationships`, `zotero_sync_state`, `teams`

---

## Documentation Structure

```
DOCS/
├── .meta/                    # Agent tracking system
│   ├── sessions/             # Session logs
│   ├── decisions/            # ADRs
│   ├── templates/            # Templates
│   └── agent-registry.json   # Statistics
├── features/                 # Feature docs
├── architecture/             # System design
├── development/              # Developer specs
└── project-management/       # Roadmap, action items
```

---

## Development Commands

### Backend
```bash
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
pytest tests/ -v
```

### Frontend
```bash
cd frontend && npm install
npm run dev
```

### Database Migrations
Run in order: `001_init.sql` → `002_pgvector.sql` → `003_graph_tables.sql` → `004_concept_centric.sql` → `005_zotero_hybrid_import.sql` → `006_teams.sql`

---

## Key Architectural Decisions

| ADR | Decision | Location |
|-----|----------|----------|
| ADR-001 | Papers/Authors as metadata only, not visualized | `DOCS/.meta/decisions/001-concept-centric-graph.md` |
| ADR-002 | Local API first, Web API fallback for Zotero | `DOCS/.meta/decisions/002-zotero-hybrid-import.md` |

---

## Entity & Relationship Types

| Entity | Visualized | Description |
|--------|------------|-------------|
| Paper | ❌ Metadata | Academic paper |
| Author | ❌ Metadata | Author |
| **Concept** | ✅ Node | Key concept/keyword |
| **Method** | ✅ Node | Research methodology |
| **Finding** | ✅ Node | Research finding |

| Relationship | Source → Target |
|--------------|-----------------|
| DISCUSSES_CONCEPT | Paper → Concept |
| USES_METHOD | Paper → Method |
| SUPPORTS/CONTRADICTS | Paper → Finding |
| RELATED_TO | Concept ↔ Concept |

---

## Environment Variables

### Backend (Render Docker: scholarag-graph-docker)

```env
# Required
DATABASE_URL=postgresql://...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...

# LLM Provider (Groq - Default Configuration)
GROQ_API_KEY=gsk_...
DEFAULT_LLM_PROVIDER=groq
DEFAULT_LLM_MODEL=llama-3.3-70b-versatile

# Embedding Provider (OpenAI)
OPENAI_API_KEY=sk-...  # Used for embeddings only

# Optional LLM Providers
ANTHROPIC_API_KEY=sk-ant-...  # Optional: Claude models

# CORS (CRITICAL - must include actual frontend URL)
CORS_ORIGINS=https://schola-rag-graph.vercel.app,https://scholarag-graph.vercel.app,http://localhost:3000

# Environment
ENVIRONMENT=production
```

### Frontend (Vercel: schola-rag-graph)

```env
NEXT_PUBLIC_API_URL=https://scholarag-graph-docker.onrender.com
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| CORS error | Frontend URL not in CORS_ORIGINS | Add URL to Render env vars |
| 503 error | DB connection pool exhaustion | Reduce pool size, enable retries |
| Auth failure | Missing Supabase keys | Check both backend & frontend env vars |

---

## Deployment

> ⚠️ **INFRA-004 (2026-01-20)**: Backend migrated from Python service to Docker service.
> ⚠️ **INFRA-006 (2026-01-21)**: Auto-Deploy disabled to prevent import interruption (BUG-028).

| Service | Platform | Type | URL |
|---------|----------|------|-----|
| Frontend | Vercel | Next.js | `https://schola-rag-graph.vercel.app` |
| Backend | Render | **Docker** | `https://scholarag-graph-docker.onrender.com` |
| Database | Supabase | PostgreSQL+pgvector | - |

### ⚠️ Deprecated Services
| Service | Status | Notes |
|---------|--------|-------|
| `scholarag-graph-api` | ❌ Deleted | Replaced by `scholarag-graph-docker` |

### CORS Configuration (Critical!)

Backend must include frontend URL in `CORS_ORIGINS` environment variable:
```
CORS_ORIGINS=https://schola-rag-graph.vercel.app,https://scholarag-graph.vercel.app,http://localhost:3000
```

**Render Dashboard Path**: `scholarag-graph-docker` → Settings → Environment Variables

### Auto-Deploy Configuration (INFRA-006)

> ⚠️ **Auto-Deploy is OFF** - Manual deployment required.

**Why**: Auto-deploy causes server restarts during import operations, killing background tasks (BUG-028).

**Render Dashboard Path**: `scholarag-graph-docker` → Settings → Build & Deploy → Auto-Deploy → **Off**

**To Deploy**:
1. Go to Render Dashboard → `scholarag-graph-docker`
2. Click "Manual Deploy" → "Deploy latest commit"
3. ⚠️ Ensure no imports are running before deploying

---

## Quick Links

| Document | Location |
|----------|----------|
| Action Items | `DOCS/project-management/action-items.md` |
| Session Logs | `DOCS/.meta/sessions/` |
| ADRs | `DOCS/.meta/decisions/` |
| Session Template | `DOCS/.meta/templates/session-template.md` |
| Agent Registry | `DOCS/.meta/agent-registry.json` |

---

## 📝 Session Documentation Protocol

> **IMPORTANT**: Claude Code MUST automatically generate session documents following this protocol.

### Auto-Documentation Triggers

| Trigger | Generated Document | Location |
|---------|-------------------|----------|
| `/code-reviewer` or code review request | Session log + Action Items | `DOCS/.meta/sessions/` |
| New feature implementation | Session log | `DOCS/.meta/sessions/` |
| Architecture decision | ADR | `DOCS/.meta/decisions/` |
| Bug fix | Action Items update | `DOCS/project-management/action-items.md` |

### Session Log Format

**Filename**: `YYYY-MM-DD_[type]-[description].md`

**Required sections**:
- Session ID, Date, Agent, Type, Duration
- Context (User Request, Related Decisions)
- Summary
- Action Items (if applicable)
- Session Statistics

### Action Item Tracking

All discovered Action Items MUST be:
1. Added to `DOCS/project-management/action-items.md`
2. Labeled by priority (🔴 High / 🟡 Medium / 🟢 Low)
3. Checked off with date when completed
4. Moved to Archive section when done

**ID Prefixes**: `SEC-` (security), `BUG-` (bug), `FUNC-` (feature), `PERF-` (performance), `DOC-` (docs), `TEST-` (test)

### Code Review Rules

On `/code-reviewer`, MUST generate:
1. Session log with Overall Assessment, Security Analysis, Recommendations
2. Action Items update
3. Registry update (`agent-registry.json`)

### Exceptions

Skip documentation for:
- Simple Q&A (no code changes)
- File exploration only
- User explicitly says "don't document"

---

## 🏗️ Infrastructure Change Documentation Protocol

> **CRITICAL**: All infrastructure changes MUST be documented IMMEDIATELY after deployment.

### Mandatory Documentation for Infrastructure Changes

| Change Type | Required Updates | Example |
|-------------|------------------|---------|
| Service migration | CLAUDE.md Deployment section, Release Notes | Python → Docker |
| URL change | CLAUDE.md, Frontend config, CORS settings | New Render URL |
| Database change | CLAUDE.md, Migration scripts | Supabase → RDS |
| Provider change | CLAUDE.md, Environment Variables section | Render → Railway |

### Infrastructure Change Checklist

When making infrastructure changes:
```
□ Update CLAUDE.md Deployment section with new service info
□ Update CORS_ORIGINS in both:
  - backend/config.py (default values)
  - Render/Platform environment variables
□ Update frontend API URL configuration
□ Create Release Notes (RELEASE_NOTES_vX.X.X.md)
□ Mark deprecated services clearly
□ Test health endpoint: curl <new-url>/health
□ Test CORS: browser console should show no CORS errors
```

### INFRA- Prefix for Infrastructure Issues

Use `INFRA-XXX` prefix for infrastructure-related action items:
- `INFRA-001`: Initial deployment setup
- `INFRA-002`: CI/CD configuration
- `INFRA-003`: Environment variables setup
- `INFRA-004`: Service migration (e.g., Python → Docker)
- `INFRA-006`: Auto-Deploy disabled (BUG-028 prevention)

---

## 📚 Continuous Architecture Documentation Protocol (v0.7.0)

> **Purpose**: Keep architecture documentation in sync with code changes through automated triggers and clear ownership.

### Documentation Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│  Level 1: Quick Reference (CLAUDE.md)                          │
│    - Commands, environment vars, deployment                     │
│    - Updated: Every session with relevant changes              │
├─────────────────────────────────────────────────────────────────┤
│  Level 2: Architecture Deep Dive (DOCS/architecture/SDD.md)    │
│    - System design, component specs, data flow                  │
│    - Updated: On architectural changes                          │
├─────────────────────────────────────────────────────────────────┤
│  Level 3: Release History (RELEASE_NOTES_vX.X.X.md)           │
│    - Features, fixes, migration guides                          │
│    - Created: On each release                                   │
├─────────────────────────────────────────────────────────────────┤
│  Level 4: Decision Records (DOCS/.meta/decisions/ADR-XXX.md)   │
│    - Why decisions were made, alternatives considered          │
│    - Created: On significant architectural decisions           │
└─────────────────────────────────────────────────────────────────┘
```

### Auto-Update Triggers

| Change Type | Update Required | Files to Modify |
|-------------|-----------------|-----------------|
| **New Feature** | ✅ | RELEASE_NOTES, SDD.md (if architectural) |
| **Bug Fix** | ⚠️ Conditional | RELEASE_NOTES (if user-facing) |
| **Dependency Change** | ✅ | SDD.md §3.2.3, RELEASE_NOTES |
| **API Endpoint** | ✅ | SDD.md §3.1, DOCS/api/* |
| **Database Schema** | ✅ | SDD.md §3.3, migration scripts |
| **Environment Variable** | ✅ | CLAUDE.md, SDD.md |
| **Deployment Change** | ✅ | CLAUDE.md, INFRA-XXX |

### SDD Update Checklist

When making architectural changes:

```
□ Update SDD.md version number (top of file)
□ Update relevant component section (§3.x)
□ Add to Change Log (bottom of file)
□ Update Mermaid diagrams if flow changes
□ Create ADR if decision was significant
□ Link to release notes
```

### Version Number Convention

| Format | When to Use | Example |
|--------|-------------|---------|
| `MAJOR.MINOR.PATCH` | Standard releases | `0.7.0` |
| `MAJOR.MINOR.PATCH-rc.N` | Release candidates | `0.8.0-rc.1` |

**Increment Rules**:
- **PATCH**: Bug fixes, documentation updates
- **MINOR**: New features, non-breaking changes
- **MAJOR**: Breaking changes, major refactoring

### Dependency Documentation Requirements (v0.7.0)

When modifying dependencies:

1. **Document in SDD.md §3.2.3** (Frontend Dependency Management)
2. **Include rationale** for version pinning
3. **Add webpack config** if build system changes needed
4. **Test build locally** before committing

Example:
```markdown
| Package | Version | Reason for Pin |
|---------|---------|----------------|
| `three` | `0.152.2` | ESM compatibility with webpack |
```

### Diagram Update Requirements

Keep Mermaid diagrams in sync with code:

| Diagram | Location | Update When |
|---------|----------|-------------|
| System Context | `DOCS/architecture/diagrams/system-context.mmd` | External integrations change |
| Agent Pipeline | `DOCS/architecture/diagrams/agent-pipeline.mmd` | Agent flow changes |
| Data Flow | `DOCS/architecture/diagrams/data-flow.mmd` | Import/query flow changes |
| Container | `DOCS/architecture/diagrams/container-diagram.mmd` | Component architecture changes |

---

## ❓ User Confirmation Protocol (AskUserQuestion)

> **CRITICAL**: Claude Code NEVER guesses in uncertain situations.
> MUST call `AskUserQuestion` tool in the following cases.

### Mandatory Confirmation Scenarios

#### 1. Option Selection Required

**Triggers**:
- 2+ implementation approaches exist
- Library/framework choice needed
- Architecture pattern decision
- Performance vs readability trade-off

#### 2. Additional Information Needed

**Triggers**:
- Requirements unclear or ambiguous
- Business logic decision needed
- External service integration info missing
- Environment/deployment info insufficient

#### 3. Conflict with Existing Code/Knowledge

**Triggers**:
- New implementation differs from existing patterns
- Conflicts with existing ADR
- Conflicts with previous session decisions
- Inconsistent with documented architecture

### Question Priority

| Priority | Situation | Ask Immediately? |
|----------|-----------|------------------|
| 🔴 Critical | Conflicts with ADR/decision | ✅ Yes |
| 🔴 Critical | Security-related decision | ✅ Yes |
| 🟡 High | Architecture pattern choice | ✅ Yes |
| 🟡 High | Irreversible change (DB schema) | ✅ Yes |
| 🟢 Medium | Library selection | ⚠️ Context-dependent |
| 🟢 Medium | Implementation details | ⚠️ Context-dependent |
| ⚪ Low | Coding style/format | ❌ Follow existing patterns |

### Conflict Detection Checklist

Before starting work, check:
```
□ Conflicts with ADRs in DOCS/.meta/decisions/?
□ Conflicts with previous sessions in DOCS/.meta/sessions/?
□ Related to items in DOCS/project-management/action-items.md?
□ Different approach from existing code patterns?
□ Contradicts decisions in agent-registry.json?
```

**On conflict detection**:
1. Clearly explain the conflict
2. Present context of existing decision
3. Offer options (minimum 2)
4. Proceed only after user confirmation

### Exceptions (Proceed Without Asking)

- Repetitive work following existing patterns
- Explicitly decided conventions (linting, formatting)
- User explicitly says "use your judgment"
- Simple bug fix (no logic change)

### Decision Recording

After user confirmation, record decisions:
1. **ADR-level**: Create `DOCS/.meta/decisions/NNN-title.md`
2. **Session-level**: Record in current session log
3. **Simple choice**: Add code comment

```python
# User Decision (2026-01-15): Use Zotero Local API first
# Ref: Session 2026-01-15_zotero-implementation
async def connect_zotero():
    ...
```

---

## 🔄 Decision Flow Summary

```
┌──────────────────────────────────────────────────────────────┐
│                 Claude Code Decision Flow                     │
├──────────────────────────────────────────────────────────────┤
│  1. Start Task                                                │
│       ↓                                                       │
│  2. Conflict Check (ADR, Sessions, Code Patterns)            │
│       ↓                                                       │
│  3. Conflict? ──────────────────────┐                        │
│       │ No                          │ Yes                    │
│       ↓                             ↓                        │
│  4. Options needed? ────┐   → AskUserQuestion                │
│       │ No              │ Yes       │                        │
│       ↓                 ↓           │                        │
│  5. Info missing? ──┐  AskUserQuestion                       │
│       │ No          │ Yes   ↓       │                        │
│       ↓             ↓       ↓       │                        │
│   Proceed     AskUserQuestion ←─────┘                        │
│       │              ↓                                        │
│       │        Wait for response                             │
│       │              ↓                                        │
│       └──────→ Record decision & proceed                     │
│                      ↓                                        │
│               Log in session                                  │
└──────────────────────────────────────────────────────────────┘
```

---

## API Endpoints (Quick Reference)

**Base URL**: `https://scholarag-graph-docker.onrender.com`

```
GET  /health                   # Health check (DB + LLM status)
POST /api/import/scholarag     # ScholaRAG folder import
POST /api/import/pdf           # PDF import
POST /api/import/zotero/validate  # Zotero file validation
GET  /api/projects             # Project list
POST /api/chat/query           # Chat (6-Agent RAG query)
GET  /api/graph/{project_id}   # Graph data
GET  /api/graph/visualization/{project_id}  # Graph visualization (InfraNodus style)
GET  /api/integrations/zotero/collections  # Zotero collections

# InfraNodus Integration (v0.4.0)
GET  /api/graph/relationships/{id}/evidence    # Relationship evidence
GET  /api/graph/temporal/{project_id}          # Temporal graph stats
POST /api/graph/temporal/{project_id}/migrate  # Trigger temporal migration
POST /api/graph/gaps/{project_id}/refresh      # Refresh gap analysis
GET  /api/graph/gaps/{project_id}/analysis     # Get gap analysis data
POST /api/graph/gaps/{id}/generate-bridge      # AI bridge hypotheses
GET  /api/graph/diversity/{project_id}         # Diversity metrics
GET  /api/graph/compare/{a}/{b}                # Project comparison
```

> **Full API Documentation**: See `DOCS/api/infranodus-api.md` for detailed schemas.

### Health Check

```bash
curl https://scholarag-graph-docker.onrender.com/health
# Expected: {"status":"healthy","database":"connected","llm_provider":"groq"}
```

---

## View Modes (InfraNodus Style)

ScholaRAG_Graph provides three interactive visualization modes inspired by InfraNodus:

| Mode | Component | Technology | Icon | Purpose |
|------|-----------|------------|------|---------|
| **3D** | `Graph3D.tsx` | Three.js + Force Graph | Box (Teal) | Full knowledge graph exploration with physics simulation |
| **Topic** | `TopicViewMode.tsx` | D3.js force layout | Grid2X2 (Purple) | Topic clustering and community detection |
| **Gaps** | `GapsViewMode.tsx` | Three.js + Ghost Edges | AlertTriangle (Amber) | Research gap identification with bridge hypotheses |

### View Mode Details

#### 3D View
- **Physics**: Customizable force simulation (charge, link distance, gravity)
- **Interactions**: Click nodes to highlight connections, drag to reposition
- **Highlighting**: Yellow glow for selected nodes, connected nodes in green
- **Controls**: Orbit controls for 360° rotation and zoom

#### Topic View
- **Communities**: Louvain algorithm for topic clustering
- **Layout**: D3.js force-directed graph with custom forces
- **Zoom**: Semantic zoom levels (0.5-3x)
- **Clusters**: Visual grouping by research theme

#### Gaps View
- **Ghost Edges**: Semi-transparent yellow edges showing potential connections
- **AI Hypotheses**: LLM-generated bridge concepts for unexplored areas
- **High-Impact**: Prioritized gaps based on PageRank and betweenness centrality
- **Interactive**: Click gaps to generate research suggestions

### View Mode Switching

All modes share:
- Same graph data source
- Consistent node/edge filtering
- Search functionality
- Export capabilities

Switch between modes using toolbar icons in the graph interface.

---

## 🏛️ Architecture Review Protocol

> **CRITICAL**: All architectural changes MUST follow this review protocol before implementation.

### Mandatory Review Triggers

| Change Type | Review Required | SDD Section | Documentation |
|-------------|-----------------|-------------|---------------|
| New Agent added | ✅ | 4.1.1 | Update SDD + agent-pipeline.mmd |
| New API Endpoint | ✅ | 6 | Update SDD + API docs |
| Database schema change | ✅ | 4.3 | Update SDD + migrations |
| LLM Provider change | ✅ | 4.1.4 | Update SDD + LLM_CONFIGURATION.md |
| New Import method | ✅ | 4.1.3 | Update SDD + data-flow.mmd |
| New View Mode | ✅ | 4.2.2 | Update SDD + container-diagram.mmd |
| Core algorithm change | ✅ | Varies | Update SDD + relevant docs |

### Architecture Review Checklist

Before committing architectural changes:
```
□ Documented in SDD.md?
□ Mermaid diagrams updated? (DOCS/architecture/diagrams/)
□ Conflicts with existing ADRs? (DOCS/.meta/decisions/)
□ API contract changes documented?
□ Database migration required?
□ Backward compatibility maintained?
□ Performance impact assessed?
```

### Commit Message Conventions (Architecture)

Use these prefixes for architecture-related commits:

| Prefix | Description | Example |
|--------|-------------|---------|
| `arch:` | General architecture change | `arch: add caching layer` |
| `arch(agent):` | Agent system change | `arch(agent): add validation agent` |
| `arch(api):` | API contract change | `arch(api): add /graph/export endpoint` |
| `arch(schema):` | Database schema change | `arch(schema): add temporal_data column` |
| `arch(llm):` | LLM provider/config change | `arch(llm): add Gemini provider` |
| `arch(viz):` | Visualization architecture | `arch(viz): add heatmap view mode` |

### Architecture Decision Records (ADRs)

For significant decisions, create ADR at `DOCS/.meta/decisions/NNN-title.md`:

```markdown
# ADR-NNN: [Title]

## Status
[Proposed | Accepted | Deprecated | Superseded by ADR-XXX]

## Context
[Why is this decision needed?]

## Decision
[What was decided?]

## Consequences
[What are the implications?]

## Alternatives Considered
[What other options were evaluated?]
```

### SDD Update Workflow

When making architectural changes:

1. **Before Implementation**:
   - Check SDD.md for current architecture
   - Identify affected sections
   - Draft changes to SDD

2. **During Implementation**:
   - Keep SDD changes in sync with code
   - Update Mermaid diagrams if flow changes

3. **After Implementation**:
   - Finalize SDD updates
   - Update Change Log section
   - Create ADR if decision was significant

### Key Architecture Documents

| Document | Location | Purpose |
|----------|----------|---------|
| SDD | `DOCS/architecture/SDD.md` | Master design document |
| System Context | `DOCS/architecture/diagrams/system-context.mmd` | External interactions |
| Agent Pipeline | `DOCS/architecture/diagrams/agent-pipeline.mmd` | 6-Agent flow |
| Data Flow | `DOCS/architecture/diagrams/data-flow.mmd` | Import/query flows |
| Container Diagram | `DOCS/architecture/diagrams/container-diagram.mmd` | Internal architecture |
| Overview | `DOCS/architecture/overview.md` | Detailed architecture |
| ADRs | `DOCS/.meta/decisions/` | Decision records |

---

## 📊 v0.11.0 Release Notes

> **Version**: 0.11.0 | **Date**: 2026-02-06
> **Full Notes**: See `RELEASE_NOTES_v0.11.0.md`

### Critical
- **Visualization API**: `max_nodes` default 200→1000 (max 5000), ORDER BY prioritizes academic entities
- **Zotero Gap Detection**: Full parity with ScholaRAG importer (clustering + gap analysis + centrality)

### High
- **AI Evidence Explanation**: LLM-generated relationship explanation when no text chunks exist
- **Gap Panel Resize**: Drag-to-resize (256-500px), default 320px
- **Dynamic Chat Questions**: Graph data-based suggested questions (replaces hardcoded)
- **Bridge Ideas UX**: Categorized error messages (LLM/network/not-found) + UUID label detection
- **Cluster Labels**: UUID regex detection with keyword-based fallback names

### Medium
- **Hover Debounce**: 50ms debounce eliminates node jitter (~90% fewer state updates)
- **View Tab UI**: Tab-bar style view mode toggle (3D/Topics/Gaps)
- **Panel Layout**: Flex-based stacking prevents overlap

### Low
- **Korean Tooltips**: All toolbar buttons translated to Korean

### Technical
- `backend/routers/graph.py`: max_nodes, ORDER BY, ai_explanation field
- `backend/importers/zotero_rdf_importer.py`: Phase 6 gap detection
- `frontend/components/graph/*`: GapPanel, Graph3D, KnowledgeGraph3D, EdgeContextModal, GapQueryPanel
- `frontend/components/chat/ChatInterface.tsx`: graphStats prop, useMemo questions
- `frontend/types/graph.ts`: ai_explanation field

---

## 📊 v0.10.1 Release Notes

> **Version**: 0.10.1 | **Date**: 2026-02-06
> **Full Notes**: See `RELEASE_NOTES_v0.10.1.md`

### Fixed
- **Repeated Project Reopen Instability**: Removed duplicate graph fetch on project page re-entry path
- **Health Check DB Churn**: Added cached health snapshot (TTL 15s) and single-query DB/pgvector probe
- **Connection Pressure Reduction**: `/health` now uses cached snapshot instead of repeated DB checks

### Technical
- `backend/database.py`: `get_health_snapshot()` + `asyncio.Lock` + TTL cache
- `backend/main.py`: `/health` now reads snapshot once
- `frontend/app/projects/[id]/page.tsx`: removed redundant `fetchGraphData(projectId)` effect

---

## 📊 v0.10.0 Release Notes

> **Version**: 0.10.0 | **Date**: 2026-02-05
> **Full Notes**: See `RELEASE_NOTES_v0.10.0.md`

### Added
- **Entity Type V2**: Type-specific confidence thresholds (0.6-0.7), enhanced DATASETS/METRICS extraction prompts, metrics parsing pipeline
- **Entity Shape Visualization**: 8 distinct Three.js geometries per entity type (Sphere, Box, Octahedron, Cone, Dodecahedron, Tetrahedron, Cylinder, Torus)
- **EntityTypeLegend Component**: Collapsible legend with SVG shape icons and Korean labels
- **Convex Hull Boundaries**: D3.js `polygonHull` cluster boundaries in Topic View
- **Test Infrastructure**: 3 backend test files (test_chat_router, test_graph_router, test_importer) + 3 frontend test files (Graph3D, useGraphStore, api)
- **Active Mode Indicator**: Pulsing dot animation on view mode badges (teal=3D, purple=Topic)

### Improved
- **Camera Polling**: Bucket-based zoom updates (`Math.round(distance/50)*50`) via `useRef` - ~90% fewer state updates
- **Cluster Labels**: 14px color-matched text with text shadow (was 12px white)
- **Topic Legend**: Shows cluster color swatches with names and counts
- **SDD Document**: Updated from v0.7.0 to v0.9.0 with full architectural alignment

### Technical
- `ENTITY_TYPE_CONFIDENCE_THRESHOLDS` constant in `entity_extractor.py`
- `ENTITY_TYPE_SHAPES` constant in `Graph3D.tsx` with geometry switch in `nodeThreeObject`
- `currentZoomRef` for jitter-free camera polling
- `hullGroup` with `d3.polygonHull` in `TopicViewMode.tsx`

---

## 📊 v0.9.0 Release Notes

> **Version**: 0.9.0 | **Date**: 2026-02-04
> **Full Notes**: See `RELEASE_NOTES_v0.9.0.md`

### Added
- **InfraNodus-Style Labeling**: Centrality-based visibility (top 20% always visible), dynamic font sizing (10-28px), opacity gradient (0.3-1.0)
- **Improved Tooltips**: All 14 toolbar buttons have descriptive Korean tooltips

### Fixed
- **Graph Shrinkage**: Reduced velocity decay 0.9→0.4, increased cooldown 200→1000
- **Node Drag Release**: Nodes now float back naturally after dragging
- **AI Explain UUID**: Uses concept names instead of raw UUIDs
- **No Gaps Detected**: Auto-refresh + stronger min_gaps enforcement
- **Evidence 500 Errors**: SQL escaping + classified error handling

### Removed
- **Particle Effects**: Lightning toggle and particle rendering completely removed

### Planned (v0.10.0) → ✅ Released
- ✅ Entity Extraction V2 (all 8 entity types) → v0.10.0
- AI Chat data-based fallback → moved to v0.11.0
- Semantic diversity metrics → moved to v0.11.0
- Next.js 14.2+ security upgrade → moved to v0.11.0

---

## 📊 v0.8.0 Release Notes

> **Version**: 0.8.0 | **Date**: 2026-02-04
> **Full Notes**: See `RELEASE_NOTES_v0.8.0.md`

### Added
- **Label Visibility Toggle**: Toolbar button cycles none/important/all modes
- **Node Removal Preview**: Visual preview before applying slicing
- **InsightHUD Repositioning**: Moved to right-side (InfraNodus-style)

### Fixed
- **EdgeContextModal Accessibility**: ESC key, focus trap, ARIA attributes
- **Evidence API Stability**: Table existence check prevents 500 errors
- **Cluster Color Stability**: Hash-based assignment for consistent colors

### Technical
- `hashClusterId()` function for deterministic color mapping
- `LabelVisibility` type with `cycleLabelVisibility()` store action
- Dynamic panel stacking for InsightHUD positioning

---

## 📊 v0.7.0 Release Notes

> **Version**: 0.7.0 | **Date**: 2026-02-04
> **Full Notes**: See `RELEASE_NOTES_v0.7.0.md`

### Added
- **Node Pinning**: Click to pin, Shift+click for multi-select
- **Adaptive Labeling**: Zoom-responsive label visibility
- **Graph-to-Prompt**: Export graph context for AI tools
- **Continuous Documentation Protocol**: Auto-update triggers and guidelines
- **SDD §3.2.3**: Frontend Dependency Management section

### Fixed
- `'focused'` diversity rating type error (BUG-041)
- Three.js ESM module resolution for Vercel builds (BUG-042)

### Technical
- Pinned Three.js ecosystem to stable versions
- webpack NormalModuleReplacementPlugin for ESM paths
- npm overrides for transitive dependencies
