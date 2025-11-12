-- Migration: Add source_request_id to posts table
-- Date: 2025-11-12
-- Description: Track which request caused a post to be discovered/scraped

BEGIN;

-- Add source_request_id column to posts table
ALTER TABLE posts ADD COLUMN IF NOT EXISTS source_request_id INTEGER;

-- Add foreign key constraint
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'posts_source_request_id_fkey'
    ) THEN
        ALTER TABLE posts
        ADD CONSTRAINT posts_source_request_id_fkey
        FOREIGN KEY (source_request_id)
        REFERENCES deal_requests(id)
        ON DELETE SET NULL;
    END IF;
END $$;

-- Add index for better query performance
CREATE INDEX IF NOT EXISTS idx_posts_source_request ON posts(source_request_id);

COMMIT;
