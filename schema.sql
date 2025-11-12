-- DealRadar Database Schema
-- Tracks Blocket posts and their AI evaluations

-- Posts table: stores all discovered listings
CREATE TABLE IF NOT EXISTS posts (
    ad_id VARCHAR(50) PRIMARY KEY,
    title TEXT,
    price VARCHAR(50),
    description TEXT,
    seller VARCHAR(100),
    location VARCHAR(200),
    category VARCHAR(100),
    company_ad BOOLEAN DEFAULT FALSE,
    type VARCHAR(10),
    region VARCHAR(100),
    images JSONB,
    source_request_id INTEGER,  -- FK constraint added later after deal_requests table exists
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    raw_data JSONB
);

-- Evaluations table: tracks AI evaluation results
CREATE TABLE IF NOT EXISTS evaluations (
    id SERIAL PRIMARY KEY,
    ad_id VARCHAR(50) REFERENCES posts(ad_id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, completed, error, skipped
    value_score NUMERIC(3,1) CHECK (value_score BETWEEN 1 AND 10),
    evaluation_notes TEXT,  -- Main justification from AI
    notification_message TEXT,  -- Short message for notifications
    estimated_market_value VARCHAR(100),  -- AI's market value estimate
    specs JSONB,  -- Parsed specs from AI
    evaluated_at TIMESTAMP,
    error_message TEXT,
    CONSTRAINT unique_evaluation_per_post UNIQUE(ad_id)
);

-- Notifications table: tracks which deals we've notified about
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    ad_id VARCHAR(50) REFERENCES posts(ad_id) ON DELETE CASCADE,
    value_score INTEGER,
    notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notification_channel VARCHAR(50),  -- email, telegram, slack, etc.
    read BOOLEAN DEFAULT FALSE
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_posts_discovered ON posts(discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_price ON posts(price);
CREATE INDEX IF NOT EXISTS idx_evaluations_status ON evaluations(status);
CREATE INDEX IF NOT EXISTS idx_evaluations_score ON evaluations(value_score DESC);
CREATE INDEX IF NOT EXISTS idx_evaluations_evaluated_at ON evaluations(evaluated_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(read);

-- Useful views
CREATE OR REPLACE VIEW unevaluated_posts AS
SELECT p.*
FROM posts p
LEFT JOIN evaluations e ON p.ad_id = e.ad_id
WHERE e.ad_id IS NULL OR e.status = 'pending';

CREATE OR REPLACE VIEW high_value_deals AS
SELECT p.*, e.value_score, e.evaluation_notes, e.evaluated_at
FROM posts p
INNER JOIN evaluations e ON p.ad_id = e.ad_id
WHERE e.value_score >= 8 AND e.status = 'completed'
ORDER BY e.value_score DESC, e.evaluated_at DESC;

CREATE OR REPLACE VIEW pending_notifications AS
SELECT p.*, e.value_score, e.evaluation_notes
FROM posts p
INNER JOIN evaluations e ON p.ad_id = e.ad_id
LEFT JOIN notifications n ON p.ad_id = n.ad_id
WHERE e.value_score >= 8
  AND e.status = 'completed'
  AND n.ad_id IS NULL
ORDER BY e.value_score DESC;

-- Deal Finder: User requests for specific items
CREATE TABLE IF NOT EXISTS deal_requests (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    max_budget INTEGER,
    requirements TEXT,
    structured_prompt TEXT,
    search_keyword VARCHAR(200),
    status VARCHAR(20) DEFAULT 'pending',  -- pending, active, fulfilled, expired
    approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP + INTERVAL '7 days',
    fulfilled_at TIMESTAMP
);

-- Request subscriptions: Email list for each request
CREATE TABLE IF NOT EXISTS request_subscriptions (
    id SERIAL PRIMARY KEY,
    request_id INTEGER REFERENCES deal_requests(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_request_subscription UNIQUE(request_id, email)
);

-- Request matches: Posts that match specific requests
CREATE TABLE IF NOT EXISTS request_matches (
    id SERIAL PRIMARY KEY,
    request_id INTEGER REFERENCES deal_requests(id) ON DELETE CASCADE,
    ad_id VARCHAR(50) REFERENCES posts(ad_id) ON DELETE CASCADE,
    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_request_match UNIQUE(request_id, ad_id)
);

-- Indexes for deal finder
CREATE INDEX IF NOT EXISTS idx_deal_requests_status ON deal_requests(status);
CREATE INDEX IF NOT EXISTS idx_deal_requests_approved ON deal_requests(approved);
CREATE INDEX IF NOT EXISTS idx_deal_requests_expires ON deal_requests(expires_at);

-- Add foreign key constraint to posts.source_request_id (after deal_requests table exists)
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

-- Index for posts.source_request_id
CREATE INDEX IF NOT EXISTS idx_posts_source_request ON posts(source_request_id);

-- View for active requests
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

-- View for request matches with full post and evaluation details
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
