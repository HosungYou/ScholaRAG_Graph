-- ScholaRAG_Graph Database Schema
-- Migration 014: API Quota System
-- Per-project/user daily API call limits for external services

-- ============================================================================
-- API Quota Plans Table
-- ============================================================================
-- Defines quota limits for different plans/tiers

CREATE TABLE IF NOT EXISTS api_quota_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL UNIQUE,  -- 'free', 'basic', 'premium', 'enterprise'
    description TEXT,

    -- Daily limits per API type
    semantic_scholar_daily_limit INT NOT NULL DEFAULT 100,
    openalex_daily_limit INT NOT NULL DEFAULT 200,
    zotero_daily_limit INT NOT NULL DEFAULT 100,

    -- Total daily limit across all APIs
    total_daily_limit INT NOT NULL DEFAULT 500,

    -- Monthly limits (optional, NULL = unlimited within daily)
    semantic_scholar_monthly_limit INT,
    openalex_monthly_limit INT,
    zotero_monthly_limit INT,
    total_monthly_limit INT,

    -- Pricing metadata (for future billing)
    price_monthly DECIMAL(10, 2) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default plans
INSERT INTO api_quota_plans (name, description, semantic_scholar_daily_limit, openalex_daily_limit, zotero_daily_limit, total_daily_limit)
VALUES
    ('free', 'Free tier with limited API calls', 50, 100, 50, 200),
    ('basic', 'Basic plan for individual researchers', 200, 400, 200, 800),
    ('premium', 'Premium plan for research teams', 500, 1000, 500, 2000),
    ('enterprise', 'Unlimited plan for institutions', 10000, 20000, 10000, 50000)
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- User Quota Assignments Table
-- ============================================================================
-- Assigns quota plans to users (defaults to 'free' if not assigned)

CREATE TABLE IF NOT EXISTS user_quota_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,  -- References auth.users in Supabase
    plan_id UUID REFERENCES api_quota_plans(id) ON DELETE SET NULL,

    -- Custom overrides (NULL = use plan defaults)
    custom_semantic_scholar_limit INT,
    custom_openalex_limit INT,
    custom_zotero_limit INT,
    custom_total_limit INT,

    valid_from TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    valid_until TIMESTAMP WITH TIME ZONE,  -- NULL = indefinite

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_user_assignment UNIQUE (user_id)
);

-- ============================================================================
-- Project Quota Assignments Table (Optional)
-- ============================================================================
-- Allows per-project quota limits (separate from user limits)

CREATE TABLE IF NOT EXISTS project_quota_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Per-project limits (NULL = inherit from user)
    semantic_scholar_daily_limit INT,
    openalex_daily_limit INT,
    zotero_daily_limit INT,
    total_daily_limit INT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_project_assignment UNIQUE (project_id)
);

-- ============================================================================
-- API Usage Tracking Table
-- ============================================================================
-- Records all API calls for quota enforcement and analytics

CREATE TABLE IF NOT EXISTS api_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Who made the call
    user_id UUID,  -- NULL for anonymous/unauthenticated
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,

    -- API call details
    api_type VARCHAR(50) NOT NULL,  -- 'semantic_scholar', 'openalex', 'zotero'
    endpoint VARCHAR(255) NOT NULL,  -- '/semantic-scholar/search', etc.

    -- Usage tracking
    call_count INT NOT NULL DEFAULT 1,  -- For bulk operations

    -- Date tracking (for daily/monthly aggregation)
    usage_date DATE NOT NULL DEFAULT CURRENT_DATE,
    usage_hour INT NOT NULL DEFAULT EXTRACT(HOUR FROM NOW()),

    -- Request metadata
    request_ip VARCHAR(45),  -- IPv4 or IPv6
    user_agent TEXT,

    -- Response metadata
    response_status INT,  -- HTTP status code
    response_time_ms INT,  -- Response time in milliseconds
    error_message TEXT,    -- If call failed

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for efficient quota checking
CREATE INDEX IF NOT EXISTS idx_api_usage_user_date ON api_usage(user_id, usage_date);
CREATE INDEX IF NOT EXISTS idx_api_usage_project_date ON api_usage(project_id, usage_date);
CREATE INDEX IF NOT EXISTS idx_api_usage_user_api_date ON api_usage(user_id, api_type, usage_date);
CREATE INDEX IF NOT EXISTS idx_api_usage_project_api_date ON api_usage(project_id, api_type, usage_date);
CREATE INDEX IF NOT EXISTS idx_api_usage_date ON api_usage(usage_date);

-- Partial index for recent data (hot data optimization)
CREATE INDEX IF NOT EXISTS idx_api_usage_recent ON api_usage(user_id, api_type, usage_date)
WHERE usage_date >= CURRENT_DATE - INTERVAL '7 days';

-- ============================================================================
-- Daily Usage Summary View
-- ============================================================================
-- Pre-aggregated view for fast quota checking

CREATE OR REPLACE VIEW daily_api_usage_summary AS
SELECT
    user_id,
    project_id,
    api_type,
    usage_date,
    SUM(call_count) as total_calls,
    COUNT(*) as request_count,
    AVG(response_time_ms) as avg_response_time_ms,
    SUM(CASE WHEN response_status >= 400 THEN 1 ELSE 0 END) as error_count
FROM api_usage
WHERE usage_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY user_id, project_id, api_type, usage_date;

-- ============================================================================
-- User Daily Usage Function
-- ============================================================================
-- Fast function to get user's current daily usage

CREATE OR REPLACE FUNCTION get_user_daily_usage(
    p_user_id UUID,
    p_api_type VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    api_type VARCHAR,
    daily_calls BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        au.api_type::VARCHAR,
        COALESCE(SUM(au.call_count), 0)::BIGINT as daily_calls
    FROM api_usage au
    WHERE au.user_id = p_user_id
      AND au.usage_date = CURRENT_DATE
      AND (p_api_type IS NULL OR au.api_type = p_api_type)
    GROUP BY au.api_type;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Quota Check Function
-- ============================================================================
-- Returns quota status for a user

CREATE OR REPLACE FUNCTION check_user_quota(
    p_user_id UUID,
    p_api_type VARCHAR
)
RETURNS TABLE (
    quota_limit INT,
    current_usage BIGINT,
    remaining INT,
    is_exceeded BOOLEAN,
    plan_name VARCHAR
) AS $$
DECLARE
    v_plan_id UUID;
    v_limit INT;
    v_usage BIGINT;
    v_plan_name VARCHAR;
BEGIN
    -- Get user's plan
    SELECT
        COALESCE(uqa.plan_id, (SELECT id FROM api_quota_plans WHERE name = 'free')),
        COALESCE(aqp.name, 'free')
    INTO v_plan_id, v_plan_name
    FROM api_quota_plans aqp
    LEFT JOIN user_quota_assignments uqa ON uqa.plan_id = aqp.id AND uqa.user_id = p_user_id
    WHERE aqp.name = 'free' OR uqa.user_id = p_user_id
    LIMIT 1;

    -- Get limit for the API type
    SELECT
        CASE p_api_type
            WHEN 'semantic_scholar' THEN COALESCE(uqa.custom_semantic_scholar_limit, aqp.semantic_scholar_daily_limit)
            WHEN 'openalex' THEN COALESCE(uqa.custom_openalex_limit, aqp.openalex_daily_limit)
            WHEN 'zotero' THEN COALESCE(uqa.custom_zotero_limit, aqp.zotero_daily_limit)
            ELSE aqp.total_daily_limit
        END
    INTO v_limit
    FROM api_quota_plans aqp
    LEFT JOIN user_quota_assignments uqa ON uqa.plan_id = aqp.id AND uqa.user_id = p_user_id
    WHERE aqp.id = v_plan_id OR (uqa.user_id IS NULL AND aqp.name = 'free')
    LIMIT 1;

    -- Default to free plan limits if nothing found
    IF v_limit IS NULL THEN
        SELECT
            CASE p_api_type
                WHEN 'semantic_scholar' THEN semantic_scholar_daily_limit
                WHEN 'openalex' THEN openalex_daily_limit
                WHEN 'zotero' THEN zotero_daily_limit
                ELSE total_daily_limit
            END
        INTO v_limit
        FROM api_quota_plans
        WHERE name = 'free';
    END IF;

    -- Get current usage
    SELECT COALESCE(SUM(call_count), 0)
    INTO v_usage
    FROM api_usage
    WHERE user_id = p_user_id
      AND api_type = p_api_type
      AND usage_date = CURRENT_DATE;

    RETURN QUERY SELECT
        v_limit,
        v_usage,
        GREATEST(0, v_limit - v_usage)::INT,
        v_usage >= v_limit,
        v_plan_name;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Cleanup Old Usage Data
-- ============================================================================
-- Function to archive/delete old usage data (run periodically)

CREATE OR REPLACE FUNCTION cleanup_old_api_usage(days_to_keep INT DEFAULT 90)
RETURNS INT AS $$
DECLARE
    deleted_count INT;
BEGIN
    DELETE FROM api_usage
    WHERE usage_date < CURRENT_DATE - (days_to_keep || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Triggers for updated_at
-- ============================================================================

CREATE TRIGGER update_api_quota_plans_updated_at
    BEFORE UPDATE ON api_quota_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_quota_assignments_updated_at
    BEFORE UPDATE ON user_quota_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_project_quota_assignments_updated_at
    BEFORE UPDATE ON project_quota_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- RLS Policies (Supabase)
-- ============================================================================

-- Enable RLS
ALTER TABLE api_quota_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_quota_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_quota_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_usage ENABLE ROW LEVEL SECURITY;

-- Quota plans: readable by all authenticated users
CREATE POLICY "quota_plans_read" ON api_quota_plans
    FOR SELECT TO authenticated
    USING (is_active = TRUE);

-- User assignments: users can only see their own
CREATE POLICY "user_assignments_own" ON user_quota_assignments
    FOR ALL TO authenticated
    USING (auth.uid() = user_id);

-- Project assignments: project members can see
CREATE POLICY "project_assignments_members" ON project_quota_assignments
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM projects p
            LEFT JOIN team_members tm ON tm.team_id = p.team_id
            WHERE p.id = project_quota_assignments.project_id
            AND (p.user_id = auth.uid() OR tm.user_id = auth.uid())
        )
    );

-- API usage: users can see their own usage
CREATE POLICY "api_usage_own" ON api_usage
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

-- Service role can do everything (for backend)
CREATE POLICY "service_full_access_plans" ON api_quota_plans
    FOR ALL TO service_role
    USING (TRUE);

CREATE POLICY "service_full_access_user_assignments" ON user_quota_assignments
    FOR ALL TO service_role
    USING (TRUE);

CREATE POLICY "service_full_access_project_assignments" ON project_quota_assignments
    FOR ALL TO service_role
    USING (TRUE);

CREATE POLICY "service_full_access_usage" ON api_usage
    FOR ALL TO service_role
    USING (TRUE);
