-- Migration: 018_semantic_chunks.sql
-- Description: Add semantic chunking support for hierarchical retrieval
-- Version: v0.3.0

-- ============================================================================
-- Semantic Chunks Table
-- ============================================================================
-- Stores hierarchical chunks from academic papers:
-- - Parent chunks (level 0): Full section content for context
-- - Child chunks (level 1): Paragraph-level for precise retrieval

CREATE TABLE IF NOT EXISTS semantic_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID REFERENCES paper_metadata(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    
    -- Content
    text TEXT NOT NULL,
    summary TEXT,  -- LLM-generated 1-sentence summary (optional)
    
    -- Section metadata
    section_type VARCHAR(50) NOT NULL DEFAULT 'unknown',
    section_title VARCHAR(500),
    
    -- Hierarchy (Parent-Child structure)
    parent_chunk_id UUID REFERENCES semantic_chunks(id) ON DELETE CASCADE,
    chunk_level INTEGER NOT NULL DEFAULT 0,  -- 0=parent (section), 1=child (paragraph)
    
    -- Embeddings (Cohere embed-v4.0, 1536 dimensions)
    embedding vector(1536),
    
    -- Metadata
    token_count INTEGER,
    sequence_order INTEGER NOT NULL DEFAULT 0,
    start_line INTEGER,
    end_line INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_chunk_level CHECK (chunk_level >= 0 AND chunk_level <= 2),
    CONSTRAINT valid_section_type CHECK (section_type IN (
        'title', 'abstract', 'introduction', 'background', 'literature_review',
        'methodology', 'methods', 'results', 'discussion', 'conclusion',
        'references', 'appendix', 'acknowledgments', 'unknown'
    ))
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

-- Primary lookup patterns
CREATE INDEX IF NOT EXISTS idx_semantic_chunks_paper_id 
    ON semantic_chunks(paper_id);

CREATE INDEX IF NOT EXISTS idx_semantic_chunks_project_id 
    ON semantic_chunks(project_id);

CREATE INDEX IF NOT EXISTS idx_semantic_chunks_section_type 
    ON semantic_chunks(section_type);

CREATE INDEX IF NOT EXISTS idx_semantic_chunks_parent 
    ON semantic_chunks(parent_chunk_id);

-- Hierarchical retrieval: find children of a parent
CREATE INDEX IF NOT EXISTS idx_semantic_chunks_hierarchy 
    ON semantic_chunks(parent_chunk_id, chunk_level, sequence_order);

-- Vector similarity search (HNSW for fast approximate nearest neighbor)
CREATE INDEX IF NOT EXISTS idx_semantic_chunks_embedding_hnsw 
    ON semantic_chunks 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Get all child chunks for a parent
CREATE OR REPLACE FUNCTION get_child_chunks(parent_id UUID)
RETURNS TABLE (
    id UUID,
    text TEXT,
    section_type VARCHAR(50),
    sequence_order INTEGER,
    token_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        sc.id,
        sc.text,
        sc.section_type,
        sc.sequence_order,
        sc.token_count
    FROM semantic_chunks sc
    WHERE sc.parent_chunk_id = parent_id
    ORDER BY sc.sequence_order;
END;
$$ LANGUAGE plpgsql;

-- Get parent chunk with all children (for context expansion)
CREATE OR REPLACE FUNCTION get_chunk_with_context(chunk_id UUID)
RETURNS TABLE (
    id UUID,
    text TEXT,
    section_type VARCHAR(50),
    chunk_level INTEGER,
    is_target BOOLEAN
) AS $$
DECLARE
    target_parent_id UUID;
    target_level INTEGER;
BEGIN
    -- Get the chunk's parent and level
    SELECT 
        COALESCE(parent_chunk_id, id),
        chunk_level
    INTO target_parent_id, target_level
    FROM semantic_chunks
    WHERE semantic_chunks.id = chunk_id;
    
    -- Return parent and all siblings
    RETURN QUERY
    SELECT 
        sc.id,
        sc.text,
        sc.section_type,
        sc.chunk_level,
        (sc.id = chunk_id) AS is_target
    FROM semantic_chunks sc
    WHERE sc.id = target_parent_id
       OR sc.parent_chunk_id = target_parent_id
    ORDER BY sc.chunk_level, sc.sequence_order;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- RLS Policies (Row Level Security)
-- ============================================================================

ALTER TABLE semantic_chunks ENABLE ROW LEVEL SECURITY;

-- Users can only see chunks from their own projects
CREATE POLICY semantic_chunks_select_policy ON semantic_chunks
    FOR SELECT
    USING (
        project_id IN (
            SELECT id FROM projects
            WHERE owner_id = auth.uid()
               OR visibility = 'public'
               OR id IN (SELECT pc.project_id FROM project_collaborators pc WHERE pc.user_id = auth.uid())
               OR id IN (
                   SELECT tp.project_id FROM team_projects tp
                   JOIN team_members tm ON tp.team_id = tm.team_id
                   WHERE tm.user_id = auth.uid()
               )
        )
    );

-- Users can only insert chunks to their own projects
CREATE POLICY semantic_chunks_insert_policy ON semantic_chunks
    FOR INSERT
    WITH CHECK (
        project_id IN (
            SELECT id FROM projects
            WHERE owner_id = auth.uid()
        )
    );

-- Users can only delete chunks from their own projects
CREATE POLICY semantic_chunks_delete_policy ON semantic_chunks
    FOR DELETE
    USING (
        project_id IN (
            SELECT id FROM projects
            WHERE owner_id = auth.uid()
        )
    );

-- ============================================================================
-- Trigger for updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_semantic_chunks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_semantic_chunks_updated_at
    BEFORE UPDATE ON semantic_chunks
    FOR EACH ROW
    EXECUTE FUNCTION update_semantic_chunks_updated_at();

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE semantic_chunks IS 'Hierarchical chunks from academic papers for RAG retrieval';
COMMENT ON COLUMN semantic_chunks.chunk_level IS '0=parent (full section), 1=child (paragraph)';
COMMENT ON COLUMN semantic_chunks.section_type IS 'Academic paper section (introduction, methods, results, etc.)';
COMMENT ON COLUMN semantic_chunks.parent_chunk_id IS 'Reference to parent chunk for hierarchical retrieval';
