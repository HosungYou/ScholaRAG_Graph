-- Migration: 007_conversations.sql
-- Description: Enhance conversations table with user_id and add suggested_follow_ups to messages
-- Date: 2025-01-15

-- ================================================
-- Add user_id to conversations table
-- Links conversations to their owners for access control
-- ================================================
ALTER TABLE conversations
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES user_profiles(id) ON DELETE SET NULL;

-- Index for user lookups
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);

-- ================================================
-- Add suggested_follow_ups to messages table
-- Stores AI-suggested follow-up questions for assistant responses
-- ================================================
ALTER TABLE messages
    ADD COLUMN IF NOT EXISTS suggested_follow_ups JSONB DEFAULT '[]';

-- ================================================
-- Change conversation id type from UUID to VARCHAR(64)
-- to support string-based conversation IDs from the chat router
-- ================================================
-- Note: This requires recreating the table due to type change
-- First, create a new table with the correct schema

-- Step 1: Create new conversations table with VARCHAR id
CREATE TABLE IF NOT EXISTS conversations_new (
    id VARCHAR(64) PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES user_profiles(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Step 2: Migrate existing data (if any) - convert UUID to string
INSERT INTO conversations_new (id, project_id, user_id, created_at, updated_at)
SELECT id::text, project_id, user_id, created_at, updated_at
FROM conversations
ON CONFLICT (id) DO NOTHING;

-- Step 3: Drop old foreign key constraint from messages
ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_conversation_id_fkey;

-- Step 4: Alter messages.conversation_id to VARCHAR(64)
ALTER TABLE messages
    ALTER COLUMN conversation_id TYPE VARCHAR(64) USING conversation_id::text;

-- Step 5: Drop old conversations table
DROP TABLE IF EXISTS conversations CASCADE;

-- Step 6: Rename new table
ALTER TABLE conversations_new RENAME TO conversations;

-- Step 7: Add back foreign key constraint
ALTER TABLE messages
    ADD CONSTRAINT messages_conversation_id_fkey
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE;

-- Recreate indexes
CREATE INDEX IF NOT EXISTS idx_conversations_project ON conversations(project_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);

-- ================================================
-- Update trigger for conversations
-- ================================================
DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ================================================
-- Utility view for conversation summaries
-- ================================================
CREATE OR REPLACE VIEW conversation_summaries AS
SELECT
    c.id as conversation_id,
    c.project_id,
    c.user_id,
    c.created_at,
    c.updated_at,
    COUNT(m.id) as message_count,
    MAX(m.created_at) as last_message_at
FROM conversations c
LEFT JOIN messages m ON m.conversation_id = c.id
GROUP BY c.id, c.project_id, c.user_id, c.created_at, c.updated_at;
