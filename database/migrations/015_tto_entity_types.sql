-- Migration 004: TTO (Technology Transfer Office) Entity & Relationship Types
-- Adds entity types for PSU TTO domain: Invention, Patent, Inventor, Technology, License, Grant, Department
-- Adds relationship types: INVENTED_BY, CITES_PRIOR_ART, USES_TECHNOLOGY, LICENSED_TO, FUNDED_BY, PATENT_OF, DEVELOPED_IN, LICENSE_OF

-- ============================================================
-- 1. Add TTO Entity Types
-- ============================================================

-- Add new entity types to the enum
ALTER TYPE entity_type ADD VALUE IF NOT EXISTS 'Invention';
ALTER TYPE entity_type ADD VALUE IF NOT EXISTS 'Patent';
ALTER TYPE entity_type ADD VALUE IF NOT EXISTS 'Inventor';
ALTER TYPE entity_type ADD VALUE IF NOT EXISTS 'Technology';
ALTER TYPE entity_type ADD VALUE IF NOT EXISTS 'License';
ALTER TYPE entity_type ADD VALUE IF NOT EXISTS 'Grant';
ALTER TYPE entity_type ADD VALUE IF NOT EXISTS 'Department';

-- ============================================================
-- 2. Add TTO Relationship Types
-- ============================================================

ALTER TYPE relationship_type ADD VALUE IF NOT EXISTS 'INVENTED_BY';
ALTER TYPE relationship_type ADD VALUE IF NOT EXISTS 'CITES_PRIOR_ART';
ALTER TYPE relationship_type ADD VALUE IF NOT EXISTS 'USES_TECHNOLOGY';
ALTER TYPE relationship_type ADD VALUE IF NOT EXISTS 'LICENSED_TO';
ALTER TYPE relationship_type ADD VALUE IF NOT EXISTS 'FUNDED_BY';
ALTER TYPE relationship_type ADD VALUE IF NOT EXISTS 'PATENT_OF';
ALTER TYPE relationship_type ADD VALUE IF NOT EXISTS 'DEVELOPED_IN';
ALTER TYPE relationship_type ADD VALUE IF NOT EXISTS 'LICENSE_OF';
ALTER TYPE relationship_type ADD VALUE IF NOT EXISTS 'ASSIGNED_TO';
ALTER TYPE relationship_type ADD VALUE IF NOT EXISTS 'CLASSIFIED_AS';

-- ============================================================
-- 3. Add indexes for TTO-specific queries
-- ============================================================

-- Index for finding entities by type (useful for TTO filtering)
CREATE INDEX IF NOT EXISTS idx_entities_entity_type ON entities (entity_type);

-- Index for finding relationships by type
CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships (relationship_type);

-- Composite index for project + entity type queries
CREATE INDEX IF NOT EXISTS idx_entities_project_type ON entities (project_id, entity_type);
