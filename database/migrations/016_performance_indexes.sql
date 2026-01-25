-- Migration 016: Performance Indexes
-- Created: 2026-01-25
-- Purpose: Optimize frequently used query patterns

-- 1. Paper metadata DOI lookups (import에서 빈번히 사용)
CREATE INDEX IF NOT EXISTS idx_paper_meta_doi_hash
  ON paper_metadata USING hash(doi);

-- 2. Entity cluster + visualization filter (gap detection)
CREATE INDEX IF NOT EXISTS idx_entities_cluster_visualized
  ON entities(cluster_id, is_visualized)
  WHERE is_visualized = TRUE;

-- 3. Zotero item key lookups (sync operations)
CREATE INDEX IF NOT EXISTS idx_entities_zotero_key_project
  ON entities(project_id, zotero_item_key)
  WHERE zotero_item_key IS NOT NULL;

-- 4. Temporal graph queries (year range filtering)
CREATE INDEX IF NOT EXISTS idx_entities_temporal_project
  ON entities(project_id, first_seen_year, last_seen_year)
  WHERE first_seen_year IS NOT NULL;

-- 5. Conversation message ordering (chat history)
CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
  ON messages(conversation_id, created_at DESC);
