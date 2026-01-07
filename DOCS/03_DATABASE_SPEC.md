# Database 서비스 스펙 (PostgreSQL + pgvector)

## 서비스 개요

| 항목 | 내용 |
|------|------|
| **역할** | 그래프 데이터 저장, 벡터 유사도 검색, 관계형 데이터 |
| **DBMS** | PostgreSQL 16 |
| **확장** | pgvector 0.5+ |
| **배포 플랫폼** | Render PostgreSQL |
| **플랜** | Starter ($7/월) 또는 Free (90일 제한) |

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL 16                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Tables    │  │   Indexes   │  │      Extensions         │  │
│  ├─────────────┤  ├─────────────┤  ├─────────────────────────┤  │
│  │ projects    │  │ idx_entity  │  │ pgvector (HNSW)         │  │
│  │ entities    │  │ idx_rel     │  │ pg_trgm (Full-text)     │  │
│  │ relations   │  │ idx_vector  │  │ uuid-ossp               │  │
│  │ conversations│ │ idx_search  │  └─────────────────────────┘  │
│  │ messages    │  └─────────────┘                                │
│  │ import_jobs │                                                 │
│  └─────────────┘                                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Functions & Views                        ││
│  │  find_similar_papers() │ find_research_gaps()               ││
│  │  search_similar_entities() │ papers_with_authors (view)     ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## 스키마 정의

### Migration 001: 기본 테이블

```sql
-- projects 테이블
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    source_folder TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- conversations 테이블
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- messages 테이블
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]',
    highlighted_nodes JSONB DEFAULT '[]',
    highlighted_edges JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- import_jobs 테이블
CREATE TABLE import_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    total_papers INTEGER,
    processed_papers INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

### Migration 002: pgvector 확장

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### Migration 003: 그래프 테이블

```sql
-- 엔티티 타입 ENUM
CREATE TYPE entity_type AS ENUM (
    'Paper', 'Author', 'Concept', 'Method', 'Finding'
);

-- 관계 타입 ENUM
CREATE TYPE relationship_type AS ENUM (
    'AUTHORED_BY', 'CITES', 'DISCUSSES_CONCEPT',
    'USES_METHOD', 'HAS_FINDING', 'RELATED_TO', 'CO_OCCURS'
);

-- entities 테이블 (노드)
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    entity_type entity_type NOT NULL,
    name TEXT NOT NULL,
    properties JSONB DEFAULT '{}',
    embedding vector(1536),
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', name || ' ' || COALESCE(properties->>'abstract', ''))
    ) STORED,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- relationships 테이블 (엣지)
CREATE TABLE relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    source_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    target_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type relationship_type NOT NULL,
    weight FLOAT DEFAULT 1.0,
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, target_id, relationship_type)
);
```

---

## 인덱스

```sql
-- 벡터 검색 (HNSW)
CREATE INDEX idx_entities_embedding ON entities
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Full-text 검색
CREATE INDEX idx_entities_search ON entities USING GIN (search_vector);

-- Trigram 검색 (퍼지 매칭)
CREATE INDEX idx_entities_name_trgm ON entities
USING GIN (name gin_trgm_ops);

-- 그래프 탐색
CREATE INDEX idx_relationships_source ON relationships (source_id);
CREATE INDEX idx_relationships_target ON relationships (target_id);
CREATE INDEX idx_relationships_type ON relationships (relationship_type);

-- 프로젝트별 조회
CREATE INDEX idx_entities_project ON entities (project_id);
CREATE INDEX idx_relationships_project ON relationships (project_id);
```

---

## 함수 및 뷰

### 유사 논문 검색

```sql
CREATE OR REPLACE FUNCTION find_similar_papers(
    p_project_id UUID,
    p_paper_id UUID,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    paper_id UUID,
    paper_name TEXT,
    similarity_score FLOAT,
    shared_concepts TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    WITH paper_concepts AS (
        SELECT target_id AS concept_id
        FROM relationships
        WHERE source_id = p_paper_id
          AND relationship_type = 'DISCUSSES_CONCEPT'
    ),
    similar AS (
        SELECT
            r.source_id,
            COUNT(*) AS shared_count,
            ARRAY_AGG(e.name) AS concepts
        FROM relationships r
        JOIN paper_concepts pc ON r.target_id = pc.concept_id
        JOIN entities e ON r.target_id = e.id
        WHERE r.source_id != p_paper_id
          AND r.relationship_type = 'DISCUSSES_CONCEPT'
        GROUP BY r.source_id
    )
    SELECT
        s.source_id,
        e.name,
        s.shared_count::FLOAT / (SELECT COUNT(*) FROM paper_concepts),
        s.concepts
    FROM similar s
    JOIN entities e ON s.source_id = e.id
    ORDER BY s.shared_count DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;
```

### 연구 갭 분석

```sql
CREATE OR REPLACE FUNCTION find_research_gaps(
    p_project_id UUID,
    p_min_papers INTEGER DEFAULT 3
)
RETURNS TABLE (
    concept_id UUID,
    concept_name TEXT,
    paper_count BIGINT,
    gap_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.name,
        COUNT(DISTINCT r.source_id),
        1.0 - (COUNT(DISTINCT r.source_id)::FLOAT /
               (SELECT COUNT(*) FROM entities
                WHERE project_id = p_project_id
                  AND entity_type = 'Paper'))
    FROM entities e
    LEFT JOIN relationships r ON e.id = r.target_id
        AND r.relationship_type = 'DISCUSSES_CONCEPT'
    WHERE e.project_id = p_project_id
      AND e.entity_type = 'Concept'
    GROUP BY e.id, e.name
    HAVING COUNT(DISTINCT r.source_id) <= p_min_papers
    ORDER BY COUNT(DISTINCT r.source_id) ASC;
END;
$$ LANGUAGE plpgsql;
```

### 벡터 유사도 검색

```sql
CREATE OR REPLACE FUNCTION search_similar_entities(
    p_embedding vector(1536),
    p_project_id UUID,
    p_entity_type entity_type DEFAULT NULL,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    entity_id UUID,
    entity_name TEXT,
    entity_type entity_type,
    distance FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.name,
        e.entity_type,
        e.embedding <=> p_embedding AS dist
    FROM entities e
    WHERE e.project_id = p_project_id
      AND e.embedding IS NOT NULL
      AND (p_entity_type IS NULL OR e.entity_type = p_entity_type)
    ORDER BY e.embedding <=> p_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;
```

### 뷰: 저자별 논문

```sql
CREATE VIEW papers_with_authors AS
SELECT
    p.id AS paper_id,
    p.name AS paper_title,
    p.properties,
    STRING_AGG(a.name, ', ') AS authors
FROM entities p
LEFT JOIN relationships r ON p.id = r.source_id
    AND r.relationship_type = 'AUTHORED_BY'
LEFT JOIN entities a ON r.target_id = a.id
WHERE p.entity_type = 'Paper'
GROUP BY p.id, p.name, p.properties;
```

---

## 연결 설정

### asyncpg 연결 풀 (구현 필요)

```python
# 예상 구현
import asyncpg

class DatabasePool:
    _pool: asyncpg.Pool = None

    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        if cls._pool is None:
            cls._pool = await asyncpg.create_pool(
                dsn=settings.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60,
            )
        return cls._pool

    @classmethod
    async def close(cls):
        if cls._pool:
            await cls._pool.close()
```

---

## 구현 진행률

### 전체: 60%

```
[██████████████░░░░░░░░░░] 60%
```

| 항목 | 진행률 | 상태 |
|------|--------|------|
| 스키마 설계 | 100% | ✅ |
| 마이그레이션 파일 | 100% | ✅ |
| pgvector 인덱스 | 100% | ✅ |
| 함수/뷰 정의 | 100% | ✅ |
| 마이그레이션 실행 | 0% | ❌ |
| asyncpg 연동 | 0% | ❌ |

---

## 실행 체크리스트

### 초기 설정
- [ ] Render PostgreSQL 인스턴스 생성
- [ ] pgvector 확장 활성화 (`CREATE EXTENSION vector`)
- [ ] 마이그레이션 001 실행
- [ ] 마이그레이션 002 실행
- [ ] 마이그레이션 003 실행
- [ ] DATABASE_URL 환경 변수 설정

### 연동
- [ ] asyncpg 연결 풀 구현
- [ ] graph_store.py DB 메서드 구현
- [ ] 트랜잭션 관리 추가
- [ ] 연결 에러 핸들링

---

## Render 설정

```yaml
# render.yaml
databases:
  - name: scholarag-graph-db
    region: oregon
    plan: starter  # $7/월
    postgresMajorVersion: 16
    ipAllowList: []  # 모든 IP 허용 (개발용)
```

---

## 향후 요구사항

### 우선순위 높음
- [ ] 마이그레이션 실행
- [ ] asyncpg 연결 구현
- [ ] CRUD 쿼리 구현

### 우선순위 중간
- [ ] 백업 전략 수립
- [ ] 인덱스 최적화
- [ ] 쿼리 성능 모니터링

### 우선순위 낮음
- [ ] 읽기 복제본
- [ ] 연결 풀 튜닝
- [ ] 쿼리 캐싱 (pg_stat_statements)

---

## 의존성

| 서비스 | 의존 관계 |
|--------|----------|
| Backend | 모든 데이터 읽기/쓰기 |
| pgvector | 벡터 유사도 검색 |
| pg_trgm | 퍼지 텍스트 검색 |
