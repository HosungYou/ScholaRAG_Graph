-- Migration: 007_hybrid_mode_entity_types.sql
-- Purpose: Add secondary entity types for Hybrid Mode visualization
-- Date: 2026-01-16

-- Add new entity types to the enum
-- Note: PostgreSQL 10+ supports ADD VALUE IF NOT EXISTS in a single statement
-- For older versions, wrap in DO block with exception handling

DO $$
BEGIN
    -- Add Problem type
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'Problem' AND enumtypid = 'entity_type'::regtype) THEN
        ALTER TYPE entity_type ADD VALUE 'Problem';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'Dataset' AND enumtypid = 'entity_type'::regtype) THEN
        ALTER TYPE entity_type ADD VALUE 'Dataset';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'Metric' AND enumtypid = 'entity_type'::regtype) THEN
        ALTER TYPE entity_type ADD VALUE 'Metric';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'Innovation' AND enumtypid = 'entity_type'::regtype) THEN
        ALTER TYPE entity_type ADD VALUE 'Innovation';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'Limitation' AND enumtypid = 'entity_type'::regtype) THEN
        ALTER TYPE entity_type ADD VALUE 'Limitation';
    END IF;
END $$;

-- Also add HAS_AUTHOR relationship type if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'HAS_AUTHOR' AND enumtypid = 'relationship_type'::regtype) THEN
        ALTER TYPE relationship_type ADD VALUE 'HAS_AUTHOR';
    END IF;
END $$;

-- Verify the enum values (run manually to check)
-- SELECT enum_range(NULL::entity_type);
-- SELECT enum_range(NULL::relationship_type);

COMMENT ON TYPE entity_type IS 'Hybrid Mode entity types: Paper, Author (graph nodes) + Concept-centric types';
