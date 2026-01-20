# CLAUDE.md - ScholaRAG_Graph Project Instructions

> **Last Updated**: 2026-01-20
> **Version**: 3.0.0

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

# LLM (at least one required)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...  # FREE! Recommended for cost savings

# CORS (CRITICAL - must include actual frontend URL)
CORS_ORIGINS=https://schola-rag-graph.vercel.app,https://scholarag-graph.vercel.app,http://localhost:3000

# Defaults
DEFAULT_LLM_PROVIDER=groq  # or anthropic/openai
DEFAULT_LLM_MODEL=llama-3.3-70b-versatile
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
POST /api/chat                 # Chat (6-Agent)
GET  /api/graph/{project_id}   # Graph data
GET  /api/graph/visualization/{project_id}  # Graph visualization
GET  /api/integrations/zotero/collections  # Zotero collections
```

### Health Check

```bash
curl https://scholarag-graph-docker.onrender.com/health
# Expected: {"status":"healthy","database":"connected","llm_provider":"groq"}
```
