-- Migration: 009_potential_edges
-- Description: Add potential_edges column to structural_gaps table for Ghost Edge visualization
-- Date: 2026-01-19

-- Add potential_edges column to structural_gaps table
-- Stores JSON array of potential edges (ghost edges) between clusters
ALTER TABLE structural_gaps
ADD COLUMN IF NOT EXISTS potential_edges JSONB DEFAULT '[]'::jsonb;

-- Add comment for documentation
COMMENT ON COLUMN structural_gaps.potential_edges IS 'JSON array of potential edges (ghost edges) for InfraNodus-style visualization. Each edge contains: source_id, target_id, similarity, gap_id, source_name, target_name';

-- Create index for potential_edges if needed for querying
CREATE INDEX IF NOT EXISTS idx_structural_gaps_potential_edges
ON structural_gaps USING gin(potential_edges);
