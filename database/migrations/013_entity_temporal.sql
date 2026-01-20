-- Migration: 013_entity_temporal.sql
-- Description: Add temporal tracking columns for graph evolution visualization
-- Version: v0.4.0

-- ============================================================================
-- Add Temporal Columns to Entities
-- ============================================================================
-- Track when entities first appeared and last appeared in the literature

-- Add source_year column (from the paper that introduced this entity)
ALTER TABLE entities ADD COLUMN IF NOT EXISTS source_year INTEGER;

-- Add first_seen_year (earliest paper mentioning this entity)
ALTER TABLE entities ADD COLUMN IF NOT EXISTS first_seen_year INTEGER;

-- Add last_seen_year (most recent paper mentioning this entity)
ALTER TABLE entities ADD COLUMN IF NOT EXISTS last_seen_year INTEGER;

-- ============================================================================
-- Add Temporal Columns to Relationships
-- ============================================================================
-- Track when relationships were first established

ALTER TABLE relationships ADD COLUMN IF NOT EXISTS first_seen_year INTEGER;

-- ============================================================================
-- Indexes for Temporal Queries
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_entities_source_year
    ON entities(source_year) WHERE source_year IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_entities_first_seen_year
    ON entities(first_seen_year) WHERE first_seen_year IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_entities_temporal_range
    ON entities(project_id, first_seen_year, last_seen_year)
    WHERE first_seen_year IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_relationships_first_seen
    ON relationships(first_seen_year) WHERE first_seen_year IS NOT NULL;

-- ============================================================================
-- Migration Function: Populate temporal data from paper_metadata
-- ============================================================================
-- Run this after migration to backfill existing data

CREATE OR REPLACE FUNCTION migrate_entity_temporal_data(target_project_id UUID DEFAULT NULL)
RETURNS TABLE (
    entities_updated BIGINT,
    relationships_updated BIGINT
) AS $$
DECLARE
    ent_count BIGINT := 0;
    rel_count BIGINT := 0;
BEGIN
    -- Update entities from paper metadata via entity_paper_links or relationships
    -- For entities linked to papers via DISCUSSES_CONCEPT, USES_METHOD, etc.
    WITH entity_years AS (
        SELECT
            e.id as entity_id,
            MIN(pm.publication_year) as first_year,
            MAX(pm.publication_year) as last_year
        FROM entities e
        JOIN relationships r ON (e.id = r.source_id OR e.id = r.target_id)
        JOIN entities paper ON (
            (paper.id = r.source_id OR paper.id = r.target_id)
            AND paper.id != e.id
            AND paper.entity_type = 'Paper'
        )
        LEFT JOIN paper_metadata pm ON pm.title = paper.name
        WHERE pm.publication_year IS NOT NULL
        AND (target_project_id IS NULL OR e.project_id = target_project_id)
        GROUP BY e.id
    )
    UPDATE entities e
    SET
        first_seen_year = COALESCE(e.first_seen_year, ey.first_year),
        last_seen_year = COALESCE(e.last_seen_year, ey.last_year),
        source_year = COALESCE(e.source_year, ey.first_year)
    FROM entity_years ey
    WHERE e.id = ey.entity_id;

    GET DIAGNOSTICS ent_count = ROW_COUNT;

    -- Alternative: Update from paper properties if stored in entity properties
    UPDATE entities e
    SET
        first_seen_year = COALESCE(
            e.first_seen_year,
            (e.properties->>'year')::INTEGER,
            (e.properties->>'publication_year')::INTEGER
        ),
        last_seen_year = COALESCE(
            e.last_seen_year,
            (e.properties->>'year')::INTEGER,
            (e.properties->>'publication_year')::INTEGER
        )
    WHERE e.entity_type = 'Paper'
    AND e.first_seen_year IS NULL
    AND (target_project_id IS NULL OR e.project_id = target_project_id)
    AND (
        e.properties->>'year' IS NOT NULL
        OR e.properties->>'publication_year' IS NOT NULL
    );

    -- Update relationships with earliest year from connected entities
    WITH rel_years AS (
        SELECT
            r.id as rel_id,
            LEAST(
                COALESCE(src.first_seen_year, 9999),
                COALESCE(tgt.first_seen_year, 9999)
            ) as first_year
        FROM relationships r
        JOIN entities src ON r.source_id = src.id
        JOIN entities tgt ON r.target_id = tgt.id
        WHERE (target_project_id IS NULL OR r.project_id = target_project_id)
    )
    UPDATE relationships r
    SET first_seen_year = ry.first_year
    FROM rel_years ry
    WHERE r.id = ry.rel_id
    AND ry.first_year < 9999;

    GET DIAGNOSTICS rel_count = ROW_COUNT;

    RETURN QUERY SELECT ent_count, rel_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Helper Function: Get temporal statistics for a project
-- ============================================================================

CREATE OR REPLACE FUNCTION get_project_temporal_stats(target_project_id UUID)
RETURNS TABLE (
    min_year INTEGER,
    max_year INTEGER,
    year_count BIGINT,
    entities_with_year BIGINT,
    total_entities BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        MIN(e.first_seen_year)::INTEGER as min_year,
        MAX(e.last_seen_year)::INTEGER as max_year,
        COUNT(DISTINCT e.first_seen_year)::BIGINT as year_count,
        COUNT(*) FILTER (WHERE e.first_seen_year IS NOT NULL)::BIGINT as entities_with_year,
        COUNT(*)::BIGINT as total_entities
    FROM entities e
    WHERE e.project_id = target_project_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON COLUMN entities.source_year IS 'Publication year of the paper that introduced this entity';
COMMENT ON COLUMN entities.first_seen_year IS 'Earliest year this entity appears in the literature';
COMMENT ON COLUMN entities.last_seen_year IS 'Most recent year this entity appears in the literature';
COMMENT ON COLUMN relationships.first_seen_year IS 'Year when this relationship was first established';
COMMENT ON FUNCTION migrate_entity_temporal_data IS 'Backfill temporal data from paper metadata';
COMMENT ON FUNCTION get_project_temporal_stats IS 'Get temporal statistics for graph evolution visualization';
