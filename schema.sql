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
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    raw_data JSONB
);

-- Evaluations table: tracks AI evaluation results
CREATE TABLE IF NOT EXISTS evaluations (
    id SERIAL PRIMARY KEY,
    ad_id VARCHAR(50) REFERENCES posts(ad_id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, completed, error, skipped
    value_score INTEGER CHECK (value_score BETWEEN 1 AND 10),
    evaluation_notes TEXT,
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
