-- Migration: 012_relationship_evidence.sql
-- Description: Add relationship evidence tracking for contextual edge exploration
-- Version: v0.4.0

-- ============================================================================
-- Relationship Evidence Table
-- ============================================================================
-- Stores evidence/source chunks that support each relationship
-- This enables "contextual edge exploration" - clicking an edge shows source text

CREATE TABLE IF NOT EXISTS relationship_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,
    chunk_id UUID NOT NULL REFERENCES semantic_chunks(id) ON DELETE CASCADE,
    relevance_score REAL DEFAULT 0.5,
    extraction_method TEXT DEFAULT 'llm' CHECK (extraction_method IN ('llm', 'cooccurrence', 'manual', 'embedding')),
    context_snippet TEXT,  -- Short excerpt showing the relationship in context
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicate evidence entries
    UNIQUE(relationship_id, chunk_id)
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_rel_evidence_relationship_id
    ON relationship_evidence(relationship_id);

CREATE INDEX IF NOT EXISTS idx_rel_evidence_chunk_id
    ON relationship_evidence(chunk_id);

CREATE INDEX IF NOT EXISTS idx_rel_evidence_relevance
    ON relationship_evidence(relevance_score DESC);

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Get all evidence for a relationship with paper metadata
CREATE OR REPLACE FUNCTION get_relationship_evidence(rel_id UUID)
RETURNS TABLE (
    evidence_id UUID,
    chunk_id UUID,
    chunk_text TEXT,
    section_type VARCHAR(50),
    paper_id UUID,
    paper_title TEXT,
    paper_authors TEXT,
    paper_year INTEGER,
    relevance_score REAL,
    context_snippet TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        re.id as evidence_id,
        re.chunk_id,
        sc.text as chunk_text,
        sc.section_type,
        pm.id as paper_id,
        pm.title as paper_title,
        pm.authors as paper_authors,
        pm.publication_year as paper_year,
        re.relevance_score,
        re.context_snippet
    FROM relationship_evidence re
    JOIN semantic_chunks sc ON re.chunk_id = sc.id
    JOIN paper_metadata pm ON sc.paper_id = pm.id
    WHERE re.relationship_id = rel_id
    ORDER BY re.relevance_score DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- RLS Policies (Row Level Security)
-- ============================================================================

ALTER TABLE relationship_evidence ENABLE ROW LEVEL SECURITY;

-- Users can only see evidence from their own projects
CREATE POLICY relationship_evidence_select_policy ON relationship_evidence
    FOR SELECT
    USING (
        relationship_id IN (
            SELECT r.id FROM relationships r
            JOIN projects p ON r.project_id = p.id
            WHERE p.user_id = auth.uid()
               OR p.id IN (
                   SELECT project_id FROM team_members
                   WHERE user_id = auth.uid()
               )
        )
    );

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE relationship_evidence IS 'Evidence chunks that support each relationship in the knowledge graph';
COMMENT ON COLUMN relationship_evidence.relevance_score IS 'Score 0-1 indicating how strongly this chunk supports the relationship';
COMMENT ON COLUMN relationship_evidence.extraction_method IS 'How the evidence was identified: llm, cooccurrence, manual, or embedding';
COMMENT ON COLUMN relationship_evidence.context_snippet IS 'Short excerpt showing the relationship context';
