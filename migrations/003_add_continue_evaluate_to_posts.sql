-- Migration: Add continue_evaluate fields to posts table
-- Date: 2025-11-16
-- Description: Add fields to track whether a post should be evaluated for a specific request

BEGIN;

-- Add continue_evaluate column to posts table
ALTER TABLE posts ADD COLUMN IF NOT EXISTS continue_evaluate BOOLEAN DEFAULT FALSE;

-- Add continue_evaluate_reasoning column to posts table
ALTER TABLE posts ADD COLUMN IF NOT EXISTS continue_evaluate_reasoning TEXT;

-- Add index for better query performance when filtering by continue_evaluate
CREATE INDEX IF NOT EXISTS idx_posts_continue_evaluate ON posts(continue_evaluate) WHERE continue_evaluate = TRUE;

COMMIT;
