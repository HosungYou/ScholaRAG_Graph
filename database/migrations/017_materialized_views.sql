-- Migration 017: Materialized Views for Performance
-- Created: 2026-01-25

-- 1. Concept frequency view (used in graph visualization)
CREATE MATERIALIZED VIEW IF NOT EXISTS concept_frequency_mv AS
SELECT
  c.id,
  c.name,
  c.properties,
  COUNT(r.id) AS paper_count,
  c.centrality_pagerank,
  c.cluster_id,
  c.project_id
FROM entities c
LEFT JOIN relationships r ON c.id = r.target_id
  AND r.relationship_type = 'DISCUSSES_CONCEPT'
WHERE c.entity_type = 'Concept' AND c.is_visualized = TRUE
GROUP BY c.id
ORDER BY paper_count DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_concept_freq_mv_id ON concept_frequency_mv(id);
CREATE INDEX IF NOT EXISTS idx_concept_freq_mv_project ON concept_frequency_mv(project_id);

-- 2. Refresh function
CREATE OR REPLACE FUNCTION refresh_concept_frequency()
RETURNS void AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY concept_frequency_mv;
END;
$$ LANGUAGE plpgsql;

-- 3. Daily API usage summary (for quota dashboard)
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_api_usage_summary_mv AS
SELECT
  user_id,
  api_type,
  DATE(usage_date) as usage_day,
  SUM(call_count) as total_calls,
  SUM(tokens_used) as total_tokens
FROM api_usage
WHERE usage_date > NOW() - INTERVAL '30 days'
GROUP BY user_id, api_type, DATE(usage_date);

CREATE INDEX IF NOT EXISTS idx_daily_usage_mv_user ON daily_api_usage_summary_mv(user_id, usage_day);
