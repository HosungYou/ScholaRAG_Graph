-- ============================================
-- ScholaRAG_Graph - Supabase Migration Script
-- ============================================
-- Run this in Supabase SQL Editor (one-time setup)
-- Dashboard > SQL Editor > New Query > Paste & Run
-- ============================================

-- 1. Enable required extensions
-- (pgvector should be enabled via Dashboard > Database > Extensions)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 2. Projects table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    research_question TEXT,
    source_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);

-- 3. Conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_project ON conversations(project_id);

-- 4. Messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]',
    highlighted_nodes JSONB DEFAULT '[]',
    highlighted_edges JSONB DEFAULT '[]',
    agent_trace JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);

-- 5. Import jobs table
CREATE TABLE IF NOT EXISTS import_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    progress FLOAT DEFAULT 0.0,
    message TEXT,
    folder_path TEXT,
    stats JSONB,
    error_details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_import_jobs_status ON import_jobs(status);
CREATE INDEX IF NOT EXISTS idx_import_jobs_project ON import_jobs(project_id);

-- 6. Entity types enum
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'entity_type') THEN
        CREATE TYPE entity_type AS ENUM (
            'Paper',
            'Author',
            'Concept',
            'Method',
            'Finding'
        );
    END IF;
END $$;

-- 7. Relationship types enum
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'relationship_type') THEN
        CREATE TYPE relationship_type AS ENUM (
            'AUTHORED_BY',
            'CITES',
            'DISCUSSES_CONCEPT',
            'USES_METHOD',
            'USES_DATASET',
            'SUPPORTS',
            'CONTRADICTS',
            'RELATED_TO',
            'AFFILIATED_WITH',
            'COLLABORATION'
        );
    END IF;
END $$;

-- 8. Entities table (graph nodes)
CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    entity_type entity_type NOT NULL,
    name VARCHAR(500) NOT NULL,
    properties JSONB DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entities_project ON entities(project_id);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_properties ON entities USING gin (properties);

-- HNSW index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_entities_embedding ON entities
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Trigram index for fuzzy text search
CREATE INDEX IF NOT EXISTS idx_entities_name_trgm ON entities
    USING gin (name gin_trgm_ops);

-- 9. Relationships table (graph edges)
CREATE TABLE IF NOT EXISTS relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    source_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    target_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type relationship_type NOT NULL,
    properties JSONB DEFAULT '{}',
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_relationships_project ON relationships(project_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_id);
CREATE INDEX IF NOT EXISTS idx_relationships_source_type ON relationships(source_id, relationship_type);
CREATE INDEX IF NOT EXISTS idx_relationships_target_type ON relationships(target_id, relationship_type);

CREATE UNIQUE INDEX IF NOT EXISTS idx_relationships_unique
    ON relationships(source_id, target_id, relationship_type);

-- 10. Updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers
DROP TRIGGER IF EXISTS update_projects_updated_at ON projects;
CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_import_jobs_updated_at ON import_jobs;
CREATE TRIGGER update_import_jobs_updated_at
    BEFORE UPDATE ON import_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_entities_updated_at ON entities;
CREATE TRIGGER update_entities_updated_at
    BEFORE UPDATE ON entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 11. Useful views
CREATE OR REPLACE VIEW papers_with_authors AS
SELECT
    p.id AS paper_id,
    p.name AS paper_title,
    p.properties AS paper_properties,
    array_agg(DISTINCT a.name) AS authors
FROM entities p
LEFT JOIN relationships r ON p.id = r.source_id AND r.relationship_type = 'AUTHORED_BY'
LEFT JOIN entities a ON r.target_id = a.id AND a.entity_type = 'Author'
WHERE p.entity_type = 'Paper'
GROUP BY p.id, p.name, p.properties;

CREATE OR REPLACE VIEW concept_frequency AS
SELECT
    c.id AS concept_id,
    c.name AS concept_name,
    c.properties AS concept_properties,
    COUNT(r.id) AS paper_count
FROM entities c
LEFT JOIN relationships r ON c.id = r.target_id AND r.relationship_type = 'DISCUSSES_CONCEPT'
WHERE c.entity_type = 'Concept'
GROUP BY c.id, c.name, c.properties
ORDER BY paper_count DESC;

-- 12. Helper functions
CREATE OR REPLACE FUNCTION find_similar_papers(paper_uuid UUID, limit_count INT DEFAULT 10)
RETURNS TABLE (
    related_paper_id UUID,
    related_paper_name VARCHAR,
    shared_concept_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    WITH paper_concepts AS (
        SELECT target_id AS concept_id
        FROM relationships
        WHERE source_id = paper_uuid
          AND relationship_type = 'DISCUSSES_CONCEPT'
    )
    SELECT
        r2.source_id AS related_paper_id,
        e.name AS related_paper_name,
        COUNT(DISTINCT r2.target_id) AS shared_concept_count
    FROM relationships r2
    JOIN paper_concepts pc ON r2.target_id = pc.concept_id
    JOIN entities e ON r2.source_id = e.id
    WHERE r2.relationship_type = 'DISCUSSES_CONCEPT'
      AND r2.source_id != paper_uuid
      AND e.entity_type = 'Paper'
    GROUP BY r2.source_id, e.name
    ORDER BY shared_concept_count DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION find_research_gaps(project_uuid UUID, min_papers INT DEFAULT 3)
RETURNS TABLE (
    concept_id UUID,
    concept_name VARCHAR,
    paper_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.name,
        COUNT(r.id) AS paper_count
    FROM entities c
    LEFT JOIN relationships r ON c.id = r.target_id AND r.relationship_type = 'DISCUSSES_CONCEPT'
    WHERE c.entity_type = 'Concept'
      AND c.project_id = project_uuid
    GROUP BY c.id, c.name
    HAVING COUNT(r.id) < min_papers
    ORDER BY paper_count ASC;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION search_similar_entities(
    query_embedding vector(1536),
    target_project_id UUID,
    target_entity_type entity_type DEFAULT NULL,
    limit_count INT DEFAULT 10
)
RETURNS TABLE (
    entity_id UUID,
    entity_name VARCHAR,
    entity_type entity_type,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.name,
        e.entity_type,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM entities e
    WHERE e.project_id = target_project_id
      AND e.embedding IS NOT NULL
      AND (target_entity_type IS NULL OR e.entity_type = target_entity_type)
    ORDER BY e.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Migration complete!
-- You should see 6 tables in Table Editor:
--   - projects
--   - conversations
--   - messages
--   - import_jobs
--   - entities
--   - relationships
-- ============================================
