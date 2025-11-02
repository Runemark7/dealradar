"""
Database Tracker for DealRadar
Manages post tracking and evaluation status in PostgreSQL
"""
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from typing import List, Dict, Optional
from datetime import datetime

from ..config import settings


class PostTracker:
    """Manages tracking of Blocket posts and their evaluations"""

    def __init__(self, db_config: Optional[Dict] = None):
        """
        Initialize database connection

        Args:
            db_config: Dict with keys: host, port, database, user, password
                      If None, uses configuration from settings
        """
        if db_config is None:
            db_config = settings.db_config

        self.db_config = db_config
        self.conn = None
        self.connect()

    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            print(f"✓ Connected to database: {self.db_config['database']}")
        except psycopg2.Error as e:
            print(f"✗ Database connection error: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ==================== POST MANAGEMENT ====================

    def save_post(self, post_data: Dict) -> bool:
        """
        Save a post to the database

        Args:
            post_data: Dictionary with post information (must include ad_id)

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO posts (
                        ad_id, title, price, description, seller, location,
                        category, company_ad, type, region, images, raw_data
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ad_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        price = EXCLUDED.price,
                        description = EXCLUDED.description,
                        raw_data = EXCLUDED.raw_data
                """, (
                    post_data.get('ad_id'),
                    post_data.get('title'),
                    post_data.get('price'),
                    post_data.get('description'),
                    post_data.get('seller'),
                    post_data.get('location'),
                    post_data.get('category'),
                    post_data.get('company_ad', False),
                    post_data.get('type'),
                    post_data.get('region'),
                    Json(post_data.get('images', [])),
                    Json(post_data)
                ))
                self.conn.commit()
                return True
        except psycopg2.Error as e:
            print(f"✗ Error saving post {post_data.get('ad_id')}: {e}")
            self.conn.rollback()
            return False

    def save_posts_batch(self, posts: List[Dict]) -> int:
        """
        Save multiple posts at once

        Args:
            posts: List of post dictionaries

        Returns:
            Number of successfully saved posts
        """
        count = 0
        for post in posts:
            if self.save_post(post):
                count += 1
        return count

    def post_exists(self, ad_id: str) -> bool:
        """Check if a post exists in the database"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT EXISTS(SELECT 1 FROM posts WHERE ad_id = %s)", (ad_id,))
            return cur.fetchone()[0]

    # ==================== EVALUATION MANAGEMENT ====================

    def is_evaluated(self, ad_id: str) -> bool:
        """
        Check if post has already been evaluated

        Args:
            ad_id: The Blocket ad ID

        Returns:
            True if evaluated, False otherwise
        """
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM evaluations
                    WHERE ad_id = %s AND status = 'completed'
                )
            """, (ad_id,))
            return cur.fetchone()[0]

    def get_unevaluated_posts(self, ad_ids: List[str]) -> List[str]:
        """
        Filter out already evaluated posts from a list

        Args:
            ad_ids: List of ad IDs to check

        Returns:
            List of ad IDs that haven't been evaluated yet
        """
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT ad_id FROM evaluations
                WHERE ad_id = ANY(%s) AND status = 'completed'
            """, (ad_ids,))
            evaluated = {row[0] for row in cur.fetchall()}
            return [ad_id for ad_id in ad_ids if ad_id not in evaluated]

    # ==================== QUERIES ====================

    def get_high_value_deals(self, min_score: int = None, limit: int = 50) -> List[Dict]:
        """
        Get all high-value deals

        Args:
            min_score: Minimum value score (uses settings default if None)
            limit: Maximum number of results

        Returns:
            List of post dictionaries with evaluation info
        """
        if min_score is None:
            min_score = settings.HIGH_VALUE_THRESHOLD

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT p.*, e.value_score, e.evaluation_notes, e.evaluated_at
                FROM posts p
                INNER JOIN evaluations e ON p.ad_id = e.ad_id
                WHERE e.value_score >= %s AND e.status = 'completed'
                ORDER BY e.value_score DESC, e.evaluated_at DESC
                LIMIT %s
            """, (min_score, limit))
            return [dict(row) for row in cur.fetchall()]

    def get_unevaluated_count(self) -> int:
        """Get count of posts that haven't been evaluated"""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM posts p
                LEFT JOIN evaluations e ON p.ad_id = e.ad_id
                WHERE e.ad_id IS NULL OR e.status = 'pending'
            """)
            return cur.fetchone()[0]

    def get_posts_for_evaluation(self, limit: int = 10) -> List[Dict]:
        """
        Get posts that need evaluation

        Args:
            limit: Maximum number of posts to return

        Returns:
            List of post dictionaries
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT p.*
                FROM posts p
                LEFT JOIN evaluations e ON p.ad_id = e.ad_id
                WHERE e.ad_id IS NULL OR e.status = 'pending'
                ORDER BY p.discovered_at DESC
                LIMIT %s
            """, (limit,))
            return [dict(row) for row in cur.fetchall()]

    def get_stats(self) -> Dict:
        """Get database statistics"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    (SELECT COUNT(*) FROM posts) as total_posts,
                    (SELECT COUNT(*) FROM evaluations WHERE status = 'completed') as evaluated_posts,
                    (SELECT COUNT(*) FROM evaluations WHERE status = 'pending') as pending_evaluations,
                    (SELECT COUNT(*) FROM evaluations WHERE status = 'error') as failed_evaluations,
                    (SELECT COUNT(*) FROM evaluations WHERE value_score >= 8 AND status = 'completed') as high_value_deals,
                    (SELECT AVG(value_score) FROM evaluations WHERE status = 'completed') as avg_score
            """)
            return dict(cur.fetchone())

