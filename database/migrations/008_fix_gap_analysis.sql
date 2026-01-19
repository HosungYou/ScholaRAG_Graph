-- ============================================================================
-- Migration: 008_fix_gap_analysis.sql
-- Purpose: Fix schema mismatch for Gap Analysis feature
-- Date: 2026-01-16
-- ============================================================================

-- 1. Add cluster_id column to entities table
ALTER TABLE entities
ADD COLUMN IF NOT EXISTS cluster_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_entities_cluster ON entities(cluster_id);

-- 2. Fix concept_clusters table to match code expectations
-- Add missing columns
ALTER TABLE concept_clusters
ADD COLUMN IF NOT EXISTS cluster_id INTEGER;

ALTER TABLE concept_clusters
ADD COLUMN IF NOT EXISTS concepts UUID[] DEFAULT '{}';

ALTER TABLE concept_clusters
ADD COLUMN IF NOT EXISTS concept_names TEXT[] DEFAULT '{}';

ALTER TABLE concept_clusters
ADD COLUMN IF NOT EXISTS size INTEGER DEFAULT 0;

ALTER TABLE concept_clusters
ADD COLUMN IF NOT EXISTS density FLOAT DEFAULT 0.0;

ALTER TABLE concept_clusters
ADD COLUMN IF NOT EXISTS label VARCHAR(255);

-- Create index on cluster_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_clusters_cluster_id ON concept_clusters(cluster_id);

-- Unique constraint for project + cluster_id combination
CREATE UNIQUE INDEX IF NOT EXISTS idx_clusters_project_cluster_id
ON concept_clusters(project_id, cluster_id);

-- ============================================================================
-- Note: After running this migration, you may need to repopulate cluster data
-- by running gap analysis on existing projects.
-- ============================================================================
