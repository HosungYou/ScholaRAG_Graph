-- Migration: 015_enable_rls.sql
-- Description: Enable RLS on remaining tables and create unified access helper function
-- Version: v0.5.0

-- ============================================================================
-- Helper Function: user_has_project_access
-- ============================================================================
-- Centralized function to check if a user has access to a project.
-- Used by all RLS policies for consistent access control.

CREATE OR REPLACE FUNCTION user_has_project_access(p_project_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM projects p
        WHERE p.id = p_project_id
        AND (
            -- User is the owner
            p.owner_id = auth.uid()
            -- Project is public
            OR p.visibility = 'public'
            -- User is a direct collaborator
            OR p.id IN (
                SELECT pc.project_id
                FROM project_collaborators pc
                WHERE pc.user_id = auth.uid()
            )
            -- User is a member of a team that has access to the project
            OR p.id IN (
                SELECT tp.project_id
                FROM team_projects tp
                JOIN team_members tm ON tp.team_id = tm.team_id
                WHERE tm.user_id = auth.uid()
            )
        )
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION user_has_project_access IS 'Checks if current user has access to a project via ownership, collaborator, or team membership';

-- ============================================================================
-- Enable RLS on Tables
-- ============================================================================

ALTER TABLE entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE paper_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE structural_gaps ENABLE ROW LEVEL SECURITY;
ALTER TABLE concept_clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- RLS Policies: entities
-- ============================================================================

CREATE POLICY entities_select_policy ON entities
    FOR SELECT
    USING (user_has_project_access(project_id));

CREATE POLICY entities_insert_policy ON entities
    FOR INSERT
    WITH CHECK (user_has_project_access(project_id));

CREATE POLICY entities_update_policy ON entities
    FOR UPDATE
    USING (user_has_project_access(project_id));

CREATE POLICY entities_delete_policy ON entities
    FOR DELETE
    USING (user_has_project_access(project_id));

-- ============================================================================
-- RLS Policies: relationships
-- ============================================================================

CREATE POLICY relationships_select_policy ON relationships
    FOR SELECT
    USING (user_has_project_access(project_id));

CREATE POLICY relationships_insert_policy ON relationships
    FOR INSERT
    WITH CHECK (user_has_project_access(project_id));

CREATE POLICY relationships_update_policy ON relationships
    FOR UPDATE
    USING (user_has_project_access(project_id));

CREATE POLICY relationships_delete_policy ON relationships
    FOR DELETE
    USING (user_has_project_access(project_id));

-- ============================================================================
-- RLS Policies: paper_metadata
-- ============================================================================

CREATE POLICY paper_metadata_select_policy ON paper_metadata
    FOR SELECT
    USING (user_has_project_access(project_id));

CREATE POLICY paper_metadata_insert_policy ON paper_metadata
    FOR INSERT
    WITH CHECK (user_has_project_access(project_id));

CREATE POLICY paper_metadata_update_policy ON paper_metadata
    FOR UPDATE
    USING (user_has_project_access(project_id));

CREATE POLICY paper_metadata_delete_policy ON paper_metadata
    FOR DELETE
    USING (user_has_project_access(project_id));

-- ============================================================================
-- RLS Policies: structural_gaps
-- ============================================================================

CREATE POLICY structural_gaps_select_policy ON structural_gaps
    FOR SELECT
    USING (user_has_project_access(project_id));

CREATE POLICY structural_gaps_insert_policy ON structural_gaps
    FOR INSERT
    WITH CHECK (user_has_project_access(project_id));

CREATE POLICY structural_gaps_update_policy ON structural_gaps
    FOR UPDATE
    USING (user_has_project_access(project_id));

CREATE POLICY structural_gaps_delete_policy ON structural_gaps
    FOR DELETE
    USING (user_has_project_access(project_id));

-- ============================================================================
-- RLS Policies: concept_clusters
-- ============================================================================

CREATE POLICY concept_clusters_select_policy ON concept_clusters
    FOR SELECT
    USING (user_has_project_access(project_id));

CREATE POLICY concept_clusters_insert_policy ON concept_clusters
    FOR INSERT
    WITH CHECK (user_has_project_access(project_id));

CREATE POLICY concept_clusters_update_policy ON concept_clusters
    FOR UPDATE
    USING (user_has_project_access(project_id));

CREATE POLICY concept_clusters_delete_policy ON concept_clusters
    FOR DELETE
    USING (user_has_project_access(project_id));

-- ============================================================================
-- RLS Policies: conversations
-- ============================================================================

CREATE POLICY conversations_select_policy ON conversations
    FOR SELECT
    USING (user_has_project_access(project_id));

CREATE POLICY conversations_insert_policy ON conversations
    FOR INSERT
    WITH CHECK (user_has_project_access(project_id));

CREATE POLICY conversations_update_policy ON conversations
    FOR UPDATE
    USING (user_has_project_access(project_id));

CREATE POLICY conversations_delete_policy ON conversations
    FOR DELETE
    USING (user_has_project_access(project_id));

-- ============================================================================
-- RLS Policies: messages
-- ============================================================================
-- Messages are linked to conversations, so we check access via conversation's project

CREATE POLICY messages_select_policy ON messages
    FOR SELECT
    USING (
        conversation_id IN (
            SELECT c.id FROM conversations c
            WHERE user_has_project_access(c.project_id)
        )
    );

CREATE POLICY messages_insert_policy ON messages
    FOR INSERT
    WITH CHECK (
        conversation_id IN (
            SELECT c.id FROM conversations c
            WHERE user_has_project_access(c.project_id)
        )
    );

CREATE POLICY messages_update_policy ON messages
    FOR UPDATE
    USING (
        conversation_id IN (
            SELECT c.id FROM conversations c
            WHERE user_has_project_access(c.project_id)
        )
    );

CREATE POLICY messages_delete_policy ON messages
    FOR DELETE
    USING (
        conversation_id IN (
            SELECT c.id FROM conversations c
            WHERE user_has_project_access(c.project_id)
        )
    );

-- ============================================================================
-- Service Role Bypass Policies
-- ============================================================================
-- Allow service role full access for backend operations

CREATE POLICY entities_service_policy ON entities
    FOR ALL TO service_role
    USING (TRUE);

CREATE POLICY relationships_service_policy ON relationships
    FOR ALL TO service_role
    USING (TRUE);

CREATE POLICY paper_metadata_service_policy ON paper_metadata
    FOR ALL TO service_role
    USING (TRUE);

CREATE POLICY structural_gaps_service_policy ON structural_gaps
    FOR ALL TO service_role
    USING (TRUE);

CREATE POLICY concept_clusters_service_policy ON concept_clusters
    FOR ALL TO service_role
    USING (TRUE);

CREATE POLICY conversations_service_policy ON conversations
    FOR ALL TO service_role
    USING (TRUE);

CREATE POLICY messages_service_policy ON messages
    FOR ALL TO service_role
    USING (TRUE);

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE entities IS 'Knowledge graph entities (concepts, methods, findings) with RLS enabled';
COMMENT ON TABLE relationships IS 'Knowledge graph relationships between entities with RLS enabled';
COMMENT ON TABLE paper_metadata IS 'Academic paper metadata with RLS enabled';
COMMENT ON TABLE structural_gaps IS 'Identified structural gaps in knowledge graph with RLS enabled';
COMMENT ON TABLE concept_clusters IS 'Clustered concepts for visualization with RLS enabled';
COMMENT ON TABLE conversations IS 'Chat conversations per project with RLS enabled';
COMMENT ON TABLE messages IS 'Chat messages within conversations with RLS enabled';
