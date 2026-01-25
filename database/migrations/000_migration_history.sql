-- Migration: 000_migration_history.sql
-- Description: Migration tracking table to record applied migrations
-- Version: v0.1.0
-- Note: This migration should be run FIRST before all others

-- ============================================================================
-- Migration History Table
-- ============================================================================
-- Tracks all applied migrations with timestamps and checksums for verification

CREATE TABLE IF NOT EXISTS migration_history (
    id SERIAL PRIMARY KEY,
    migration_number VARCHAR(10) UNIQUE NOT NULL,
    migration_name VARCHAR(255) NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    checksum VARCHAR(64),  -- SHA-256 hash of migration file for integrity verification
    applied_by VARCHAR(255),  -- User/service that applied the migration
    execution_time_ms INTEGER,  -- How long the migration took to run
    rollback_sql TEXT,  -- Optional: SQL to rollback this migration
    notes TEXT  -- Optional: Any notes about the migration
);

-- ============================================================================
-- Indexes
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_migration_history_number
    ON migration_history(migration_number);

CREATE INDEX IF NOT EXISTS idx_migration_history_applied_at
    ON migration_history(applied_at DESC);

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Record a migration as applied
CREATE OR REPLACE FUNCTION record_migration(
    p_migration_number VARCHAR(10),
    p_migration_name VARCHAR(255),
    p_checksum VARCHAR(64) DEFAULT NULL,
    p_applied_by VARCHAR(255) DEFAULT 'system',
    p_execution_time_ms INTEGER DEFAULT NULL,
    p_rollback_sql TEXT DEFAULT NULL,
    p_notes TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO migration_history (
        migration_number,
        migration_name,
        checksum,
        applied_by,
        execution_time_ms,
        rollback_sql,
        notes
    ) VALUES (
        p_migration_number,
        p_migration_name,
        p_checksum,
        p_applied_by,
        p_execution_time_ms,
        p_rollback_sql,
        p_notes
    )
    ON CONFLICT (migration_number) DO UPDATE SET
        applied_at = NOW(),
        checksum = COALESCE(EXCLUDED.checksum, migration_history.checksum),
        applied_by = EXCLUDED.applied_by,
        execution_time_ms = EXCLUDED.execution_time_ms,
        notes = EXCLUDED.notes;
END;
$$ LANGUAGE plpgsql;

-- Check if a migration has been applied
CREATE OR REPLACE FUNCTION is_migration_applied(p_migration_number VARCHAR(10))
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM migration_history
        WHERE migration_number = p_migration_number
    );
END;
$$ LANGUAGE plpgsql;

-- Get the latest applied migration number
CREATE OR REPLACE FUNCTION get_latest_migration()
RETURNS VARCHAR(10) AS $$
DECLARE
    v_latest VARCHAR(10);
BEGIN
    SELECT migration_number INTO v_latest
    FROM migration_history
    ORDER BY migration_number DESC
    LIMIT 1;

    RETURN v_latest;
END;
$$ LANGUAGE plpgsql;

-- List all pending migrations (for use with application code)
CREATE OR REPLACE FUNCTION get_applied_migrations()
RETURNS TABLE (
    migration_number VARCHAR(10),
    migration_name VARCHAR(255),
    applied_at TIMESTAMP WITH TIME ZONE,
    checksum VARCHAR(64)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        mh.migration_number,
        mh.migration_name,
        mh.applied_at,
        mh.checksum
    FROM migration_history mh
    ORDER BY mh.migration_number ASC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- RLS Policies
-- ============================================================================
-- Migration history should be readable by authenticated users but only writable by service role

ALTER TABLE migration_history ENABLE ROW LEVEL SECURITY;

-- Authenticated users can read migration history
CREATE POLICY migration_history_select_policy ON migration_history
    FOR SELECT TO authenticated
    USING (TRUE);

-- Only service role can modify migration history
CREATE POLICY migration_history_service_policy ON migration_history
    FOR ALL TO service_role
    USING (TRUE);

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE migration_history IS 'Tracks all database migrations applied to this database';
COMMENT ON COLUMN migration_history.migration_number IS 'Migration file number (e.g., 001, 002, 015)';
COMMENT ON COLUMN migration_history.migration_name IS 'Descriptive name of the migration';
COMMENT ON COLUMN migration_history.checksum IS 'SHA-256 hash of migration file content for integrity verification';
COMMENT ON COLUMN migration_history.applied_by IS 'User or service that ran the migration';
COMMENT ON COLUMN migration_history.execution_time_ms IS 'Time taken to execute the migration in milliseconds';
COMMENT ON COLUMN migration_history.rollback_sql IS 'SQL to reverse this migration (if applicable)';

-- ============================================================================
-- Record this migration
-- ============================================================================

SELECT record_migration(
    '000',
    'migration_history',
    NULL,
    'initial_setup',
    NULL,
    'DROP TABLE IF EXISTS migration_history CASCADE;',
    'Initial migration tracking table setup'
);
