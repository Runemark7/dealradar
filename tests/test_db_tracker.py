"""
Unit tests for db_tracker.py module
Tests the database tracking and evaluation functionality
"""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime
import psycopg2
from psycopg2.extras import Json

from dealradar.database.tracker import PostTracker


@pytest.mark.unit
class TestPostTrackerInit:
    """Tests for PostTracker initialization"""

    def test_init_with_custom_config(self, db_config):
        """
        GIVEN a custom database configuration
        WHEN PostTracker is initialized
        THEN it should use the provided configuration
        """
        # Arrange & Act
        with patch('psycopg2.connect') as mock_connect:
            mock_connect.return_value = MagicMock()
            tracker = PostTracker(db_config)

            # Assert
            assert tracker.db_config == db_config
            mock_connect.assert_called_once_with(**db_config)

    def test_init_with_settings(self):
        """
        GIVEN PostTracker initialized without explicit config
        WHEN PostTracker is initialized
        THEN it should use settings from the settings module
        """
        # Arrange & Act
        with patch('psycopg2.connect') as mock_connect:
            mock_connect.return_value = MagicMock()
            tracker = PostTracker()

            # Assert - should successfully create tracker with default settings
            assert tracker.db_config is not None
            assert 'host' in tracker.db_config
            assert 'database' in tracker.db_config
            mock_connect.assert_called_once()

    def test_init_connection_failure(self, db_config):
        """
        GIVEN database connection fails
        WHEN PostTracker is initialized
        THEN it should raise an exception
        """
        # Arrange
        with patch('psycopg2.connect') as mock_connect:
            mock_connect.side_effect = psycopg2.OperationalError("Connection failed")

            # Act & Assert
            with pytest.raises(psycopg2.OperationalError):
                PostTracker(db_config)

    def test_context_manager_enter_exit(self, db_config):
        """
        GIVEN a PostTracker instance
        WHEN used as context manager
        THEN it should properly enter and exit
        """
        # Arrange
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            # Act
            with PostTracker(db_config) as tracker:
                assert tracker is not None

            # Assert
            mock_conn.close.assert_called_once()


@pytest.mark.unit
class TestSavePost:
    """Tests for save_post method"""

    def test_save_post_success(self, db_config, sample_listing_data, mock_cursor):
        """
        GIVEN valid post data
        WHEN save_post is called
        THEN it should insert the post and return True
        """
        # Arrange
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            result = tracker.save_post(sample_listing_data)

            # Assert
            assert result is True
            mock_cursor.execute.assert_called_once()
            mock_conn.commit.assert_called_once()

            # Verify SQL contains correct columns
            sql_call = mock_cursor.execute.call_args[0][0]
            assert "INSERT INTO posts" in sql_call
            assert "ad_id" in sql_call
            assert "ON CONFLICT" in sql_call

    def test_save_post_with_minimal_data(self, db_config, mock_cursor):
        """
        GIVEN post data with only required fields
        WHEN save_post is called
        THEN it should handle None values properly
        """
        # Arrange
        minimal_data = {
            "ad_id": "123",
            "title": "Test"
        }

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            result = tracker.save_post(minimal_data)

            # Assert
            assert result is True
            args = mock_cursor.execute.call_args[0][1]
            assert args[0] == "123"  # ad_id
            assert args[1] == "Test"  # title
            assert args[2] is None  # price

    def test_save_post_database_error(self, db_config, sample_listing_data, mock_cursor):
        """
        GIVEN a database error occurs
        WHEN save_post is called
        THEN it should rollback and return False
        """
        # Arrange
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_cursor.execute.side_effect = psycopg2.IntegrityError("Constraint violation")
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            result = tracker.save_post(sample_listing_data)

            # Assert
            assert result is False
            mock_conn.rollback.assert_called_once()

    def test_save_post_updates_existing(self, db_config, sample_listing_data, mock_cursor):
        """
        GIVEN a post with existing ad_id
        WHEN save_post is called
        THEN it should use ON CONFLICT to update
        """
        # Arrange
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            tracker.save_post(sample_listing_data)

            # Assert
            sql_call = mock_cursor.execute.call_args[0][0]
            assert "ON CONFLICT (ad_id) DO UPDATE" in sql_call


@pytest.mark.unit
class TestSavePostsBatch:
    """Tests for save_posts_batch method"""

    def test_save_posts_batch_all_success(self, db_config, sample_listing_data):
        """
        GIVEN a list of posts
        WHEN save_posts_batch is called
        THEN it should save all posts and return count
        """
        # Arrange
        posts = [
            {"ad_id": "1", "title": "Post 1"},
            {"ad_id": "2", "title": "Post 2"},
            {"ad_id": "3", "title": "Post 3"}
        ]

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            with patch.object(tracker, 'save_post', return_value=True) as mock_save:
                # Act
                count = tracker.save_posts_batch(posts)

                # Assert
                assert count == 3
                assert mock_save.call_count == 3

    def test_save_posts_batch_partial_failure(self, db_config):
        """
        GIVEN some posts fail to save
        WHEN save_posts_batch is called
        THEN it should return count of successful saves
        """
        # Arrange
        posts = [
            {"ad_id": "1", "title": "Post 1"},
            {"ad_id": "2", "title": "Post 2"},
            {"ad_id": "3", "title": "Post 3"}
        ]

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Second post fails
            with patch.object(tracker, 'save_post', side_effect=[True, False, True]):
                # Act
                count = tracker.save_posts_batch(posts)

                # Assert
                assert count == 2

    def test_save_posts_batch_empty_list(self, db_config):
        """
        GIVEN an empty list of posts
        WHEN save_posts_batch is called
        THEN it should return 0
        """
        # Arrange
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            count = tracker.save_posts_batch([])

            # Assert
            assert count == 0


@pytest.mark.unit
class TestPostExists:
    """Tests for post_exists method"""

    def test_post_exists_true(self, db_config, mock_cursor):
        """
        GIVEN a post exists in database
        WHEN post_exists is called
        THEN it should return True
        """
        # Arrange
        mock_cursor.fetchone.return_value = (True,)

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            result = tracker.post_exists("1213746529")

            # Assert
            assert result is True
            assert "SELECT EXISTS" in mock_cursor.execute.call_args[0][0]

    def test_post_exists_false(self, db_config, mock_cursor):
        """
        GIVEN a post does not exist
        WHEN post_exists is called
        THEN it should return False
        """
        # Arrange
        mock_cursor.fetchone.return_value = (False,)

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            result = tracker.post_exists("nonexistent")

            # Assert
            assert result is False


@pytest.mark.unit
class TestIsEvaluated:
    """Tests for is_evaluated method"""

    def test_is_evaluated_true(self, db_config, mock_cursor):
        """
        GIVEN a post has completed evaluation
        WHEN is_evaluated is called
        THEN it should return True
        """
        # Arrange
        mock_cursor.fetchone.return_value = (True,)

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            result = tracker.is_evaluated("1213746529")

            # Assert
            assert result is True
            sql = mock_cursor.execute.call_args[0][0]
            assert "status = 'completed'" in sql

    def test_is_evaluated_false_pending(self, db_config, mock_cursor):
        """
        GIVEN a post has pending evaluation
        WHEN is_evaluated is called
        THEN it should return False
        """
        # Arrange
        mock_cursor.fetchone.return_value = (False,)

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            result = tracker.is_evaluated("1213746529")

            # Assert
            assert result is False

    def test_is_evaluated_false_not_exists(self, db_config, mock_cursor):
        """
        GIVEN a post has no evaluation record
        WHEN is_evaluated is called
        THEN it should return False
        """
        # Arrange
        mock_cursor.fetchone.return_value = (False,)

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            result = tracker.is_evaluated("nonexistent")

            # Assert
            assert result is False


@pytest.mark.unit
class TestGetUnevaluatedPosts:
    """Tests for get_unevaluated_posts method"""

    def test_get_unevaluated_posts_filters_correctly(self, db_config, mock_cursor):
        """
        GIVEN a list of ad IDs with some evaluated
        WHEN get_unevaluated_posts is called
        THEN it should return only unevaluated ones
        """
        # Arrange
        ad_ids = ["1", "2", "3", "4", "5"]
        evaluated_ids = [("2",), ("4",)]  # IDs 2 and 4 are evaluated

        mock_cursor.fetchall.return_value = evaluated_ids

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            result = tracker.get_unevaluated_posts(ad_ids)

            # Assert
            assert result == ["1", "3", "5"]
            assert "status = 'completed'" in mock_cursor.execute.call_args[0][0]

    def test_get_unevaluated_posts_all_evaluated(self, db_config, mock_cursor):
        """
        GIVEN all posts are evaluated
        WHEN get_unevaluated_posts is called
        THEN it should return empty list
        """
        # Arrange
        ad_ids = ["1", "2", "3"]
        evaluated_ids = [("1",), ("2",), ("3",)]

        mock_cursor.fetchall.return_value = evaluated_ids

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            result = tracker.get_unevaluated_posts(ad_ids)

            # Assert
            assert result == []

    def test_get_unevaluated_posts_none_evaluated(self, db_config, mock_cursor):
        """
        GIVEN no posts are evaluated
        WHEN get_unevaluated_posts is called
        THEN it should return all posts
        """
        # Arrange
        ad_ids = ["1", "2", "3"]
        mock_cursor.fetchall.return_value = []

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            result = tracker.get_unevaluated_posts(ad_ids)

            # Assert
            assert result == ad_ids


@pytest.mark.unit
class TestMarkForEvaluation:
    """Tests for mark_for_evaluation method"""

    def test_mark_for_evaluation_success(self, db_config, mock_cursor):
        """
        GIVEN a valid ad_id
        WHEN mark_for_evaluation is called
        THEN it should insert pending evaluation
        """
        # Arrange
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            result = tracker.mark_for_evaluation("1213746529")

            # Assert
            assert result is True
            sql = mock_cursor.execute.call_args[0][0]
            assert "INSERT INTO evaluations" in sql
            assert "'pending'" in sql
            assert "ON CONFLICT (ad_id) DO NOTHING" in sql
            mock_conn.commit.assert_called_once()

    def test_mark_for_evaluation_database_error(self, db_config, mock_cursor):
        """
        GIVEN a database error occurs
        WHEN mark_for_evaluation is called
        THEN it should rollback and return False
        """
        # Arrange
        mock_cursor.execute.side_effect = psycopg2.Error("DB error")

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            result = tracker.mark_for_evaluation("1213746529")

            # Assert
            assert result is False
            mock_conn.rollback.assert_called_once()


@pytest.mark.unit
class TestSaveEvaluation:
    """Tests for save_evaluation method"""

    def test_save_evaluation_success(self, db_config, mock_cursor):
        """
        GIVEN valid evaluation data
        WHEN save_evaluation is called
        THEN it should save the evaluation
        """
        # Arrange
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            result = tracker.save_evaluation("1213746529", 9, "Great deal!")

            # Assert
            assert result is True
            sql = mock_cursor.execute.call_args[0][0]
            params = mock_cursor.execute.call_args[0][1]

            assert "INSERT INTO evaluations" in sql
            assert params[0] == "1213746529"
            assert params[1] == 9
            assert params[2] == "Great deal!"
            mock_conn.commit.assert_called_once()

    def test_save_evaluation_without_notes(self, db_config, mock_cursor):
        """
        GIVEN evaluation without notes
        WHEN save_evaluation is called
        THEN it should handle None notes
        """
        # Arrange
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            result = tracker.save_evaluation("1213746529", 7)

            # Assert
            assert result is True
            params = mock_cursor.execute.call_args[0][1]
            assert params[2] is None  # notes

    def test_save_evaluation_updates_existing(self, db_config, mock_cursor):
        """
        GIVEN an existing evaluation
        WHEN save_evaluation is called
        THEN it should update the evaluation
        """
        # Arrange
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            tracker.save_evaluation("1213746529", 10, "Updated score")

            # Assert
            sql = mock_cursor.execute.call_args[0][0]
            assert "ON CONFLICT (ad_id) DO UPDATE" in sql

    def test_save_evaluation_database_error(self, db_config, mock_cursor):
        """
        GIVEN a database error occurs
        WHEN save_evaluation is called
        THEN it should rollback and return False
        """
        # Arrange
        mock_cursor.execute.side_effect = psycopg2.Error("DB error")

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            result = tracker.save_evaluation("1213746529", 8)

            # Assert
            assert result is False
            mock_conn.rollback.assert_called_once()


@pytest.mark.unit
class TestMarkEvaluationError:
    """Tests for mark_evaluation_error method"""

    def test_mark_evaluation_error_success(self, db_config, mock_cursor):
        """
        GIVEN an error message
        WHEN mark_evaluation_error is called
        THEN it should save error status
        """
        # Arrange
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            result = tracker.mark_evaluation_error("1213746529", "AI service failed")

            # Assert
            assert result is True
            sql = mock_cursor.execute.call_args[0][0]
            params = mock_cursor.execute.call_args[0][1]

            assert "'error'" in sql
            assert params[0] == "1213746529"
            assert params[1] == "AI service failed"
            mock_conn.commit.assert_called_once()


@pytest.mark.unit
class TestGetHighValueDeals:
    """Tests for get_high_value_deals method"""

    def test_get_high_value_deals_default_score(self, db_config, mock_cursor):
        """
        GIVEN posts with various scores
        WHEN get_high_value_deals is called with default min_score
        THEN it should return deals with score >= 8
        """
        # Arrange
        mock_deals = [
            {"ad_id": "1", "title": "Deal 1", "value_score": 10},
            {"ad_id": "2", "title": "Deal 2", "value_score": 9},
        ]
        mock_cursor.fetchall.return_value = mock_deals

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            deals = tracker.get_high_value_deals()

            # Assert
            assert len(deals) == 2
            sql = mock_cursor.execute.call_args[0][0]
            params = mock_cursor.execute.call_args[0][1]
            assert params[0] == 8  # Default min_score
            assert params[1] == 50  # Default limit

    def test_get_high_value_deals_custom_score(self, db_config, mock_cursor):
        """
        GIVEN a custom min_score
        WHEN get_high_value_deals is called
        THEN it should use the custom score
        """
        # Arrange
        mock_cursor.fetchall.return_value = []

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            tracker.get_high_value_deals(min_score=9, limit=10)

            # Assert
            params = mock_cursor.execute.call_args[0][1]
            assert params[0] == 9
            assert params[1] == 10


@pytest.mark.unit
class TestGetStats:
    """Tests for get_stats method"""

    def test_get_stats_returns_all_metrics(self, db_config, mock_cursor, sample_stats):
        """
        GIVEN database with posts and evaluations
        WHEN get_stats is called
        THEN it should return all statistics
        """
        # Arrange
        mock_cursor.fetchone.return_value = sample_stats

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            stats = tracker.get_stats()

            # Assert
            assert stats['total_posts'] == 100
            assert stats['evaluated_posts'] == 75
            assert stats['pending_evaluations'] == 20
            assert stats['failed_evaluations'] == 5
            assert stats['high_value_deals'] == 10
            assert stats['avg_score'] == 6.5

    def test_get_stats_query_structure(self, db_config, mock_cursor):
        """
        GIVEN get_stats is called
        WHEN the SQL query is executed
        THEN it should query all required metrics
        """
        # Arrange
        mock_cursor.fetchone.return_value = {}

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            tracker.get_stats()

            # Assert
            sql = mock_cursor.execute.call_args[0][0]
            assert "total_posts" in sql
            assert "evaluated_posts" in sql
            assert "pending_evaluations" in sql
            assert "failed_evaluations" in sql
            assert "high_value_deals" in sql
            assert "avg_score" in sql


@pytest.mark.unit
class TestNotifications:
    """Tests for notification-related methods"""

    def test_save_notification_success(self, db_config, mock_cursor):
        """
        GIVEN notification details
        WHEN save_notification is called
        THEN it should save the notification
        """
        # Arrange
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            result = tracker.save_notification("1213746529", 9, "slack")

            # Assert
            assert result is True
            params = mock_cursor.execute.call_args[0][1]
            assert params[0] == "1213746529"
            assert params[1] == 9
            assert params[2] == "slack"
            mock_conn.commit.assert_called_once()

    def test_save_notification_default_channel(self, db_config, mock_cursor):
        """
        GIVEN no channel specified
        WHEN save_notification is called
        THEN it should use default channel 'n8n'
        """
        # Arrange
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            tracker.save_notification("1213746529", 9)

            # Assert
            params = mock_cursor.execute.call_args[0][1]
            assert params[2] == "n8n"

    def test_get_pending_notifications(self, db_config, mock_cursor):
        """
        GIVEN high-value deals without notifications
        WHEN get_pending_notifications is called
        THEN it should return unnotified deals
        """
        # Arrange
        mock_pending = [
            {"ad_id": "1", "value_score": 9, "title": "Deal 1"},
            {"ad_id": "2", "value_score": 10, "title": "Deal 2"}
        ]
        mock_cursor.fetchall.return_value = mock_pending

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            pending = tracker.get_pending_notifications(min_score=8)

            # Assert
            assert len(pending) == 2
            sql = mock_cursor.execute.call_args[0][0]
            assert "LEFT JOIN notifications" in sql
            assert "n.ad_id IS NULL" in sql  # Not yet notified


@pytest.mark.unit
class TestGetPostsForEvaluation:
    """Tests for get_posts_for_evaluation method"""

    def test_get_posts_for_evaluation_returns_pending(self, db_config, mock_cursor):
        """
        GIVEN posts needing evaluation
        WHEN get_posts_for_evaluation is called
        THEN it should return pending posts
        """
        # Arrange
        mock_posts = [
            {"ad_id": "1", "title": "Post 1"},
            {"ad_id": "2", "title": "Post 2"}
        ]
        mock_cursor.fetchall.return_value = mock_posts

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            posts = tracker.get_posts_for_evaluation(limit=10)

            # Assert
            assert len(posts) == 2
            params = mock_cursor.execute.call_args[0][1]
            assert params[0] == 10  # limit

    def test_get_posts_for_evaluation_respects_limit(self, db_config, mock_cursor):
        """
        GIVEN a custom limit
        WHEN get_posts_for_evaluation is called
        THEN it should respect the limit
        """
        # Arrange
        mock_cursor.fetchall.return_value = []

        with patch('psycopg2.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            tracker = PostTracker(db_config)

            # Act
            tracker.get_posts_for_evaluation(limit=5)

            # Assert
            sql = mock_cursor.execute.call_args[0][0]
            params = mock_cursor.execute.call_args[0][1]
            assert "LIMIT" in sql
            assert params[0] == 5
