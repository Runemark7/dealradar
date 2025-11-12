-- Migration: Remove duplicate value_score from request_matches
-- Date: 2025-11-12
-- Description: Remove value_score column from request_matches and reference evaluations instead

BEGIN;

-- Drop the old index that references value_score
DROP INDEX IF EXISTS idx_request_matches_score;

-- Drop the value_score column
ALTER TABLE request_matches DROP COLUMN IF EXISTS value_score;

-- Recreate the active_requests view with updated logic
CREATE OR REPLACE VIEW active_requests AS
SELECT dr.*,
       COUNT(DISTINCT rs.id) as subscriber_count,
       COUNT(DISTINCT rm.id) as match_count,
       MAX(e.value_score) as best_match_score
FROM deal_requests dr
LEFT JOIN request_subscriptions rs ON dr.id = rs.request_id
LEFT JOIN request_matches rm ON dr.id = rm.request_id
LEFT JOIN evaluations e ON rm.ad_id = e.ad_id
WHERE dr.approved = true
  AND dr.status = 'active'
  AND dr.expires_at > CURRENT_TIMESTAMP
GROUP BY dr.id
ORDER BY dr.created_at DESC;

-- Create new view for request matches with full details
CREATE OR REPLACE VIEW request_matches_details AS
SELECT
    rm.id as match_id,
    rm.request_id,
    rm.matched_at,
    dr.title as request_title,
    dr.requirements,
    p.*,
    e.value_score,
    e.evaluation_notes,
    e.notification_message,
    e.estimated_market_value,
    e.specs
FROM request_matches rm
JOIN deal_requests dr ON rm.request_id = dr.id
JOIN posts p ON rm.ad_id = p.ad_id
LEFT JOIN evaluations e ON rm.ad_id = e.ad_id
ORDER BY rm.matched_at DESC, e.value_score DESC;

COMMIT;
