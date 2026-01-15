# ScholaRAG_Graph

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg)](https://www.postgresql.org/)

**Concept-Centric Knowledge Graph Platform for Systematic Literature Review**

> "Where InfraNodus stops at keywords, ScholaRAG_Graph understands academic concepts."

ScholaRAG_Graph transforms your systematic literature review into an interactive knowledge graph, enabling **research gap detection**, **concept-based exploration**, and **AI-powered Q&A** - all following PRISMA 2020 guidelines.

<p align="center">
  <img src="docs/images/demo.gif" alt="ScholaRAG_Graph Demo" width="800">
</p>

## ✨ Key Features

### 🎯 Concept-Centric Knowledge Graph
Unlike keyword-based tools, ScholaRAG_Graph extracts **academic concepts**, **methods**, and **findings** using LLM-powered entity extraction (NLP-AKG methodology).

```
Traditional tools:  "machine" ── "learning" ── "model"  (word-level)

ScholaRAG_Graph:   [Concept: Transfer Learning] ──APPLIES_TO──► [Method: Fine-tuning]
                              │
                              └──SUPPORTS──► [Finding: 20% accuracy improvement]
```

### 🔍 Research Gap Detection (InfraNodus-style)
Automatically identify **structural gaps** between concept clusters and receive **AI-generated research questions**:
- K-means clustering on concept embeddings
- Inter-cluster connectivity analysis
- Bridge concept identification
- Chain-of-Thought reasoning for contextual questions

### 🤖 6-Agent Multi-Agent System
Intelligent query processing through specialized agents:
1. **Intent Agent**: Classifies user intent (Search, Explore, Compare, Identify Gaps...)
2. **Concept Extraction Agent**: Extracts entities from queries
3. **Task Planning Agent**: Decomposes complex queries into subtasks
4. **Query Execution Agent**: Executes against graph database
5. **Reasoning Agent**: Chain-of-Thought analysis + gap detection
6. **Response Agent**: Natural language response generation

### 📊 PRISMA 2020 Compliance
Full systematic review automation:
1. Identification (paper collection)
2. Deduplication
3. AI-assisted Screening
4. PDF Download
5. RAG Building
6. Analysis (Gap Detection + Q&A)
7. PRISMA Diagram Generation

### 🔌 ScholaRAG Integration
Direct import from [ScholaRAG](https://github.com/HosungYou/ScholaRAG) projects - your existing systematic reviews become explorable knowledge graphs.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ with pgvector extension
- API keys for LLM providers (Anthropic, OpenAI, or Google)

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/HosungYou/ScholaRAG_Graph.git
cd ScholaRAG_Graph

# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Start with Docker Compose
docker-compose up -d
```

Access the app at `http://localhost:3000`

### Option 2: Manual Setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run server
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Database:**
```bash
createdb scholarag_graph
psql scholarag_graph < database/migrations/001_init.sql
psql scholarag_graph < database/migrations/002_pgvector.sql
psql scholarag_graph < database/migrations/003_graph_tables.sql
psql scholarag_graph < database/migrations/004_concept_centric.sql
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js 14)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Knowledge    │  │    Chat      │  │      Gap Panel       │  │
│  │ Graph (Flow) │  │  Interface   │  │  (Research Gaps)     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              6-Agent Orchestrator                        │   │
│  │  Intent → Concept → Task → Query → Reasoning → Response  │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐   │
│  │ Entity         │  │ Relationship   │  │ Gap            │   │
│  │ Extractor      │  │ Builder        │  │ Detector       │   │
│  └────────────────┘  └────────────────┘  └────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 PostgreSQL + pgvector                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Entities   │  │ Relationships│  │    Embeddings        │  │
│  │  (Concepts)  │  │   (Edges)    │  │    (pgvector)        │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 📚 Documentation

- [Installation Guide](docs/installation.md)
- [User Guide](docs/user-guide.md)
- [API Reference](docs/api-reference.md)
- [Architecture Deep Dive](docs/architecture.md)
- [Contributing Guide](CONTRIBUTING.md)

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 14, React 18, React Flow, Zustand, TanStack Query, Tailwind CSS |
| Backend | FastAPI, Python 3.11+, asyncpg |
| Database | PostgreSQL 15+, pgvector |
| LLM | Anthropic Claude, OpenAI GPT-4, Google Gemini |
| ML | scikit-learn (K-means), sentence-transformers |
| Deployment | Docker, Vercel (Frontend), Render (Backend) |

## 🔧 Configuration

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/scholarag_graph

# LLM Providers (at least one required)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# Default LLM
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_LLM_MODEL=claude-3-5-haiku-20241022

# Embeddings
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
```

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Priority Areas

- 🔴 **High**: Test coverage, API documentation, error handling
- 🟡 **Medium**: Zotero integration, PRISMA diagram export
- 🟢 **Low**: Real-time collaboration, Living review support

## 📊 Comparison with Other Tools

| Feature | ScholaRAG_Graph | InfraNodus | Connected Papers | Elicit |
|---------|-----------------|------------|------------------|--------|
| Concept Extraction | ✅ Academic | ⚠️ Keywords | ❌ | ✅ |
| Gap Detection | ✅ | ✅ | ❌ | ❌ |
| Knowledge Graph | ✅ | ✅ | ✅ | ❌ |
| PRISMA Workflow | ✅ | ❌ | ❌ | ✅ |
| Open Source | ✅ | ❌ | ❌ | ❌ |
| Free | ✅ | ❌ ($19-49/mo) | ⚠️ Limited | ⚠️ Limited |
| Large Dataset | ✅ Unlimited | ❌ 3MB max | ⚠️ | ⚠️ 500 papers |

## 📜 License

MIT License - See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [ScholaRAG](https://github.com/HosungYou/ScholaRAG) - Systematic Literature Review Automation
- [AGENTiGraph](https://arxiv.org/abs/2410.11531) - Inspiration for multi-agent architecture
- [InfraNodus](https://infranodus.com/) - Gap detection methodology reference
- [NLP-AKG](https://arxiv.org/html/2502.14192v1) - Academic entity extraction approach

## 📬 Contact

- **Author**: Hosung You
- **GitHub Issues**: [Report bugs or request features](https://github.com/HosungYou/ScholaRAG_Graph/issues)
- **GitHub Discussions**: [Ask questions or discuss ideas](https://github.com/HosungYou/ScholaRAG_Graph/discussions)

---

<p align="center">
  <strong>If ASReview revolutionized screening, ScholaRAG_Graph revolutionizes analysis and discovery.</strong>
</p>
