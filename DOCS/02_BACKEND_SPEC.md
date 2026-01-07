# Backend 서비스 스펙 (Render/FastAPI)

## 서비스 개요

| 항목 | 내용 |
|------|------|
| **역할** | REST API, Multi-Agent 시스템, 데이터 처리 |
| **프레임워크** | FastAPI 0.109+ |
| **런타임** | Python 3.11+ |
| **배포 플랫폼** | Render Web Service |
| **URL** | https://scholarag-graph-api.onrender.com |

---

## 기술 스택

```txt
# Core
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.6.0
pydantic-settings>=2.1.0

# Database
asyncpg>=0.29.0
sqlalchemy>=2.0.25
pgvector>=0.2.4

# LLM Providers
anthropic>=0.18.0
openai>=1.12.0
google-generativeai>=0.4.0

# Data Processing
pandas>=2.2.0
pyyaml>=6.0.1
PyMuPDF>=1.23.0
```

---

## 디렉토리 구조

```
backend/
├── main.py                    # FastAPI 앱 엔트리포인트
├── config.py                  # 환경 설정 (Pydantic Settings)
├── requirements.txt           # Python 의존성
├── routers/
│   ├── __init__.py
│   ├── chat.py               # /api/chat 라우터
│   ├── graph.py              # /api/graph 라우터
│   ├── projects.py           # /api/projects 라우터
│   └── import_.py            # /api/import 라우터
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py       # 6-Agent 조정자
│   ├── intent_agent.py       # 의도 분류
│   ├── concept_extraction_agent.py  # 엔티티 추출
│   ├── task_planning_agent.py       # 작업 계획
│   ├── query_execution_agent.py     # 쿼리 실행
│   ├── reasoning_agent.py           # 추론
│   └── response_agent.py            # 응답 생성
├── graph/
│   ├── __init__.py
│   ├── graph_store.py        # 그래프 저장소
│   ├── entity_extractor.py   # 엔티티 추출기
│   └── relationship_builder.py  # 관계 빌더
├── importers/
│   ├── __init__.py
│   └── scholarag_importer.py # ScholaRAG 폴더 임포터
├── llm/
│   ├── __init__.py
│   ├── base.py               # BaseLLMProvider 추상 클래스
│   ├── claude_provider.py    # Anthropic Claude
│   ├── openai_provider.py    # OpenAI GPT-4
│   └── gemini_provider.py    # Google Gemini
└── models/
    └── __init__.py           # Pydantic 모델
```

---

## API 엔드포인트

### Projects API (`/api/projects`)

| Method | Endpoint | 설명 | 상태 |
|--------|----------|------|------|
| GET | `/` | 프로젝트 목록 | ✅ 완료 |
| POST | `/` | 프로젝트 생성 | ✅ 완료 |
| GET | `/{id}` | 프로젝트 상세 | ✅ 완료 |
| DELETE | `/{id}` | 프로젝트 삭제 | ✅ 완료 |

**주의**: 현재 In-memory 저장소 사용 (PostgreSQL 연동 필요)

### Graph API (`/api/graph`)

| Method | Endpoint | 설명 | 상태 |
|--------|----------|------|------|
| GET | `/{project_id}/subgraph` | 서브그래프 조회 | ⚠️ 부분 |
| GET | `/{project_id}/entities` | 엔티티 목록 | ⚠️ 부분 |
| GET | `/{project_id}/search` | 엔티티 검색 | ⚠️ 부분 |
| GET | `/entity/{id}` | 엔티티 상세 | ⚠️ 부분 |
| GET | `/entity/{id}/neighbors` | 이웃 노드 | ⚠️ 부분 |

### Chat API (`/api/chat`)

| Method | Endpoint | 설명 | 상태 |
|--------|----------|------|------|
| POST | `/query` | 챗봇 쿼리 | ✅ 완료 |
| GET | `/history/{project_id}` | 대화 기록 | ✅ 완료 |
| GET | `/conversation/{id}` | 대화 상세 | ✅ 완료 |
| DELETE | `/conversation/{id}` | 대화 삭제 | ✅ 완료 |
| POST | `/explain/{node_id}` | 노드 설명 | ✅ 완료 |
| POST | `/ask-about/{node_id}` | 노드 질문 | ✅ 완료 |

### Import API (`/api/import`)

| Method | Endpoint | 설명 | 상태 |
|--------|----------|------|------|
| POST | `/scholarag` | ScholaRAG 폴더 임포트 | ⚠️ 부분 |
| GET | `/jobs` | 임포트 작업 목록 | ⚠️ 부분 |
| GET | `/jobs/{id}` | 작업 상태 | ⚠️ 부분 |

### Health Check

| Method | Endpoint | 설명 | 상태 |
|--------|----------|------|------|
| GET | `/` | 기본 상태 | ✅ 완료 |
| GET | `/health` | 상세 상태 | ✅ 완료 |

---

## Pydantic 모델

### Chat Models

```python
class ChatRequest(BaseModel):
    project_id: UUID
    message: str
    conversation_id: Optional[str] = None
    include_trace: bool = False

class ChatResponse(BaseModel):
    conversation_id: str
    message: ChatMessage
    agent_trace: Optional[dict] = None

class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime
    citations: Optional[List[str]] = None
    highlighted_nodes: Optional[List[str]] = None
    highlighted_edges: Optional[List[str]] = None
    suggested_follow_ups: Optional[List[str]] = None
```

### Graph Models

```python
class Node(BaseModel):
    id: str
    entity_type: str  # Paper, Author, Concept, Method, Finding
    name: str
    properties: dict = {}
    embedding: Optional[List[float]] = None

class Edge(BaseModel):
    id: str
    source_id: str
    target_id: str
    relationship_type: str
    weight: float = 1.0
    properties: dict = {}
```

---

## 환경 변수

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# LLM Providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# Configuration
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_LLM_MODEL=claude-3-5-haiku-20241022

# CORS
CORS_ORIGINS=http://localhost:3000,https://scholarag-graph.vercel.app

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false
```

---

## Render 배포 설정

```yaml
# render.yaml
services:
  - type: web
    name: scholarag-graph-api
    runtime: python
    region: oregon
    plan: starter
    buildCommand: pip install -r backend/requirements.txt
    startCommand: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: "3.11"
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: DATABASE_URL
        fromDatabase:
          name: scholarag-graph-db
          property: connectionString
```

---

## 구현 진행률

### 전체: 70%

```
[█████████████████░░░░░░░] 70%
```

| 카테고리 | 진행률 | 상태 |
|----------|--------|------|
| FastAPI 설정 | 100% | ✅ |
| 라우터 구조 | 100% | ✅ |
| Multi-Agent | 95% | ✅ |
| LLM Providers | 100% | ✅ |
| ScholaRAG Importer | 90% | ⚠️ |
| Graph Store | 30% | ⚠️ |
| DB 연동 (asyncpg) | 5% | ❌ |
| 테스트 | 0% | ❌ |

---

## 블로킹 이슈

### 1. PostgreSQL asyncpg 연동 (Critical)

```python
# 현재 상태: graph_store.py
async def _db_add_entity(self, node: Node):
    # TODO: Implement with asyncpg
    pass

async def _db_get_subgraph(self, center_id: str, depth: int):
    # TODO: Implement with asyncpg
    return {"nodes": [], "edges": []}
```

**필요 작업**:
- [ ] asyncpg 연결 풀 설정
- [ ] CRUD 쿼리 구현
- [ ] 트랜잭션 관리
- [ ] 에러 핸들링

### 2. Import 결과 저장 (High)

```python
# 현재 상태: scholarag_importer.py
async def _store_entities(self, project_id: str, entities: list):
    # TODO: Implement actual database storage
    pass
```

---

## 향후 요구사항

### 우선순위 높음
- [ ] asyncpg 완전 통합
- [ ] Import 데이터 영구 저장
- [ ] 벡터 유사도 검색 구현

### 우선순위 중간
- [ ] 캐싱 (Redis)
- [ ] Rate limiting
- [ ] 백그라운드 작업 (Celery)

### 우선순위 낮음
- [ ] OpenAPI 문서 개선
- [ ] 단위 테스트
- [ ] 통합 테스트

---

## 의존성

| 서비스 | 의존 관계 |
|--------|----------|
| PostgreSQL | 모든 데이터 저장 |
| LLM APIs | Multi-Agent 응답 생성 |
| Frontend | API 클라이언트 |
