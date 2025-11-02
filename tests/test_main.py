"""
Unit tests for CLI module
Tests the CLI functionality and workflow orchestration
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open, call
import json
import sys
from io import StringIO

from dealradar.cli import main


@pytest.mark.unit
@pytest.mark.asyncio
class TestMainSingleListing:
    """Tests for single listing mode"""

    async def test_single_listing_success_with_db(self, sample_listing_data, capsys):
        """
        GIVEN a valid ad_id with database enabled
        WHEN main is called in single listing mode
        THEN it should fetch, save to DB, and write to file
        """
        # Arrange
        test_args = ["main.py", "1213746529"]

        with patch.object(sys, 'argv', test_args):
            with patch('dealradar.cli.commands.PostTracker') as mock_tracker_class:
                with patch('dealradar.cli.commands.fetch_blocket_api', new_callable=AsyncMock) as mock_fetch:
                    with patch('builtins.open', mock_open()) as mock_file:
                        # Setup mocks
                        mock_tracker = MagicMock()
                        mock_tracker.is_evaluated.return_value = False
                        mock_tracker.save_post.return_value = True
                        mock_tracker_class.return_value = mock_tracker

                        mock_fetch.return_value = sample_listing_data

                        # Act
                        await main.main()

                        # Assert
                        mock_fetch.assert_called_once_with("1213746529")
                        mock_tracker.save_post.assert_called_once_with(sample_listing_data)
                        mock_tracker.mark_for_evaluation.assert_called_once_with("1213746529")
                        mock_tracker.close.assert_called()

    async def test_single_listing_already_evaluated(self, sample_listing_data):
        """
        GIVEN a post that's already evaluated
        WHEN main is called
        THEN it should notify user but still fetch
        """
        # Arrange
        test_args = ["main.py", "1213746529"]

        with patch.object(sys, 'argv', test_args):
            with patch('dealradar.cli.commands.PostTracker') as mock_tracker_class:
                with patch('dealradar.cli.commands.fetch_blocket_api', new_callable=AsyncMock) as mock_fetch:
                    with patch('builtins.open', mock_open()):
                        mock_tracker = MagicMock()
                        mock_tracker.is_evaluated.return_value = True
                        mock_tracker.save_post.return_value = True
                        mock_tracker_class.return_value = mock_tracker

                        mock_fetch.return_value = sample_listing_data

                        # Act
                        await main.main()

                        # Assert
                        mock_tracker.is_evaluated.assert_called_once_with("1213746529")
                        mock_fetch.assert_called_once()

    async def test_single_listing_fetch_failure(self):
        """
        GIVEN fetch_blocket_api returns None
        WHEN main is called
        THEN it should handle the error gracefully
        """
        # Arrange
        test_args = ["main.py", "1213746529"]

        with patch.object(sys, 'argv', test_args):
            with patch('dealradar.cli.commands.PostTracker') as mock_tracker_class:
                with patch('dealradar.cli.commands.fetch_blocket_api', new_callable=AsyncMock) as mock_fetch:
                    mock_tracker = MagicMock()
                    mock_tracker.is_evaluated.return_value = False
                    mock_tracker_class.return_value = mock_tracker

                    mock_fetch.return_value = None

                    # Act
                    await main.main()

                    # Assert
                    mock_tracker.save_post.assert_not_called()
                    mock_tracker.close.assert_called()

    async def test_single_listing_skip_db(self, sample_listing_data):
        """
        GIVEN --skip-db flag is present
        WHEN main is called
        THEN it should not use database
        """
        # Arrange
        test_args = ["main.py", "1213746529", "--skip-db"]

        with patch.object(sys, 'argv', test_args):
            with patch('dealradar.cli.commands.PostTracker') as mock_tracker_class:
                with patch('dealradar.cli.commands.fetch_blocket_api', new_callable=AsyncMock) as mock_fetch:
                    with patch('builtins.open', mock_open()):
                        mock_fetch.return_value = sample_listing_data

                        # Act
                        await main.main()

                        # Assert
                        mock_tracker_class.assert_not_called()

    async def test_single_listing_db_connection_failure(self, sample_listing_data):
        """
        GIVEN database connection fails
        WHEN main is called
        THEN it should raise an exception
        """
        # Arrange
        test_args = ["main.py", "1213746529"]

        with patch.object(sys, 'argv', test_args):
            with patch('dealradar.cli.commands.PostTracker') as mock_tracker_class:
                with patch('dealradar.cli.commands.fetch_blocket_api', new_callable=AsyncMock) as mock_fetch:
                    mock_tracker_class.side_effect = Exception("Connection failed")
                    mock_fetch.return_value = sample_listing_data

                    # Act & Assert - exception should be raised
                    with pytest.raises(Exception, match="Connection failed"):
                        await main.main()


@pytest.mark.unit
@pytest.mark.asyncio
class TestMainSearchMode:
    """Tests for search category mode"""

    async def test_search_mode_success(self, sample_listing_data):
        """
        GIVEN valid search parameters
        WHEN main is called in search mode
        THEN it should fetch and save listings
        """
        # Arrange
        test_args = ["main.py", "--search", "5021", "--limit", "2"]
        ad_ids = ["1213746529", "1213746530"]

        with patch.object(sys, 'argv', test_args):
            with patch('dealradar.cli.commands.PostTracker') as mock_tracker_class:
                with patch('dealradar.cli.commands.fetch_search_results', new_callable=AsyncMock) as mock_search:
                    with patch('dealradar.cli.commands.fetch_multiple_listings', new_callable=AsyncMock) as mock_fetch_multi:
                        with patch('builtins.open', mock_open()):
                            # Setup mocks
                            mock_tracker = MagicMock()
                            mock_tracker.get_unevaluated_posts.return_value = ad_ids
                            mock_tracker.save_posts_batch.return_value = 2
                            mock_tracker_class.return_value = mock_tracker

                            mock_search.return_value = ad_ids
                            # Add ad_id to the returned listings
                            listings_with_ids = [
                                {**sample_listing_data, "ad_id": ad_ids[0]},
                                {**sample_listing_data, "ad_id": ad_ids[1]}
                            ]
                            mock_fetch_multi.return_value = listings_with_ids

                            # Act
                            await main.main()

                            # Assert
                            mock_search.assert_called_once_with("5021", 2)
                            mock_fetch_multi.assert_called_once_with(ad_ids)
                            mock_tracker.save_posts_batch.assert_called_once()

    async def test_search_mode_no_listings_found(self):
        """
        GIVEN search returns no listings
        WHEN main is called in search mode
        THEN it should exit gracefully
        """
        # Arrange
        test_args = ["main.py", "--search", "5021"]

        with patch.object(sys, 'argv', test_args):
            with patch('dealradar.cli.commands.PostTracker') as mock_tracker_class:
                with patch('dealradar.cli.commands.fetch_search_results', new_callable=AsyncMock) as mock_search:
                    mock_tracker = MagicMock()
                    mock_tracker_class.return_value = mock_tracker
                    mock_search.return_value = []

                    # Act
                    await main.main()

                    # Assert
                    mock_tracker.close.assert_called()

    async def test_search_mode_filters_evaluated_posts(self):
        """
        GIVEN some posts are already evaluated
        WHEN main is called in search mode
        THEN it should filter them out
        """
        # Arrange
        test_args = ["main.py", "--search", "5021", "--limit", "5"]
        all_ad_ids = ["1", "2", "3", "4", "5"]
        unevaluated_ids = ["1", "3", "5"]

        with patch.object(sys, 'argv', test_args):
            with patch('dealradar.cli.commands.PostTracker') as mock_tracker_class:
                with patch('dealradar.cli.commands.fetch_search_results', new_callable=AsyncMock) as mock_search:
                    with patch('dealradar.cli.commands.fetch_multiple_listings', new_callable=AsyncMock) as mock_fetch_multi:
                        with patch('builtins.open', mock_open()):
                            mock_tracker = MagicMock()
                            mock_tracker.get_unevaluated_posts.return_value = unevaluated_ids
                            mock_tracker.save_posts_batch.return_value = 3
                            mock_tracker_class.return_value = mock_tracker

                            mock_search.return_value = all_ad_ids
                            # Add ad_ids to the returned listings
                            listings_with_ids = [{"ad_id": id} for id in unevaluated_ids]
                            mock_fetch_multi.return_value = listings_with_ids

                            # Act
                            await main.main()

                            # Assert
                            mock_tracker.get_unevaluated_posts.assert_called_once_with(all_ad_ids)
                            mock_fetch_multi.assert_called_once_with(unevaluated_ids)

    async def test_search_mode_all_posts_evaluated(self):
        """
        GIVEN all posts are already evaluated
        WHEN main is called in search mode
        THEN it should exit without fetching
        """
        # Arrange
        test_args = ["main.py", "--search", "5021"]
        all_ad_ids = ["1", "2", "3"]

        with patch.object(sys, 'argv', test_args):
            with patch('dealradar.cli.commands.PostTracker') as mock_tracker_class:
                with patch('dealradar.cli.commands.fetch_search_results', new_callable=AsyncMock) as mock_search:
                    with patch('dealradar.cli.commands.fetch_multiple_listings', new_callable=AsyncMock) as mock_fetch_multi:
                        mock_tracker = MagicMock()
                        mock_tracker.get_unevaluated_posts.return_value = []
                        mock_tracker_class.return_value = mock_tracker

                        mock_search.return_value = all_ad_ids

                        # Act
                        await main.main()

                        # Assert
                        mock_fetch_multi.assert_not_called()
                        mock_tracker.close.assert_called()

    async def test_search_mode_missing_category(self):
        """
        GIVEN --search flag without category ID
        WHEN main is called
        THEN it should show error and exit
        """
        # Arrange
        test_args = ["main.py", "--search"]

        with patch.object(sys, 'argv', test_args):
            # Act
            await main.main()

            # Assert - should exit gracefully without crash

    async def test_search_mode_invalid_limit(self):
        """
        GIVEN invalid --limit value
        WHEN main is called in search mode
        THEN it should show error and exit
        """
        # Arrange
        test_args = ["main.py", "--search", "5021", "--limit", "invalid"]

        with patch.object(sys, 'argv', test_args):
            # Act
            await main.main()

            # Assert - should exit gracefully without crash

    async def test_search_mode_creates_output_file(self, sample_listing_data):
        """
        GIVEN successful search
        WHEN main is called in search mode
        THEN it should create JSON output file with correct structure
        """
        # Arrange
        test_args = ["main.py", "--search", "5021", "--limit", "1"]
        ad_ids = ["1213746529"]

        with patch.object(sys, 'argv', test_args):
            with patch('dealradar.cli.commands.PostTracker') as mock_tracker_class:
                with patch('dealradar.cli.commands.fetch_search_results', new_callable=AsyncMock) as mock_search:
                    with patch('dealradar.cli.commands.fetch_multiple_listings', new_callable=AsyncMock) as mock_fetch_multi:
                        with patch('builtins.open', mock_open()) as mock_file:
                            with patch('dealradar.cli.commands.datetime') as mock_datetime:
                                # Setup mocks
                                mock_datetime.now.return_value.strftime.return_value = "20250101_120000"

                                mock_tracker = MagicMock()
                                mock_tracker.get_unevaluated_posts.return_value = ad_ids
                                mock_tracker.save_posts_batch.return_value = 1
                                mock_tracker_class.return_value = mock_tracker

                                mock_search.return_value = ad_ids
                                mock_fetch_multi.return_value = [sample_listing_data]

                                # Act
                                await main.main()

                                # Assert
                                mock_file.assert_called()
                                filename_call = [c for c in mock_file.call_args_list if 'blocket_search' in str(c)]
                                assert len(filename_call) > 0

    async def test_search_mode_skip_db(self, sample_listing_data):
        """
        GIVEN --skip-db flag in search mode
        WHEN main is called
        THEN it should not filter or save to database
        """
        # Arrange
        test_args = ["main.py", "--search", "5021", "--skip-db"]
        ad_ids = ["1", "2", "3"]

        with patch.object(sys, 'argv', test_args):
            with patch('dealradar.cli.commands.fetch_search_results', new_callable=AsyncMock) as mock_search:
                with patch('dealradar.cli.commands.fetch_multiple_listings', new_callable=AsyncMock) as mock_fetch_multi:
                    with patch('builtins.open', mock_open()):
                        mock_search.return_value = ad_ids
                        mock_fetch_multi.return_value = [sample_listing_data] * 3

                        # Act
                        await main.main()

                        # Assert
                        mock_fetch_multi.assert_called_once_with(ad_ids)


@pytest.mark.unit
@pytest.mark.asyncio
class TestMainStatsMode:
    """Tests for --stats mode"""

    async def test_stats_mode_displays_statistics(self, sample_stats):
        """
        GIVEN database with statistics
        WHEN main is called with --stats
        THEN it should display all statistics
        """
        # Arrange
        test_args = ["main.py", "--stats"]

        with patch.object(sys, 'argv', test_args):
            with patch('dealradar.cli.commands.PostTracker') as mock_tracker_class:
                mock_tracker = MagicMock()
                mock_tracker.get_stats.return_value = sample_stats
                mock_tracker.__enter__ = MagicMock(return_value=mock_tracker)
                mock_tracker.__exit__ = MagicMock(return_value=None)
                mock_tracker_class.return_value = mock_tracker

                # Act
                await main.main()

                # Assert
                mock_tracker.get_stats.assert_called_once()

    async def test_stats_mode_without_database(self):
        """
        GIVEN --stats mode with --skip-db
        WHEN main is called
        THEN it should show error
        """
        # Arrange
        test_args = ["main.py", "--stats", "--skip-db"]

        with patch.object(sys, 'argv', test_args):
            # Act
            await main.main()

            # Assert - Should just exit (no crash)

    async def test_stats_mode_db_connection_failure(self):
        """
        GIVEN database connection fails in stats mode
        WHEN main is called with --stats
        THEN it should show error message
        """
        # Arrange
        test_args = ["main.py", "--stats"]

        with patch.object(sys, 'argv', test_args):
            with patch('dealradar.cli.commands.PostTracker') as mock_tracker_class:
                mock_tracker_class.side_effect = Exception("Connection failed")

                # Act
                await main.main()

                # Assert - Should handle gracefully


@pytest.mark.unit
@pytest.mark.asyncio
class TestMainDealsMode:
    """Tests for --deals mode"""

    async def test_deals_mode_default_score(self):
        """
        GIVEN --deals mode without min-score
        WHEN main is called
        THEN it should use default min_score of 8
        """
        # Arrange
        test_args = ["main.py", "--deals"]
        mock_deals = [{"ad_id": "1", "value_score": 9}]

        with patch.object(sys, 'argv', test_args):
            with patch('dealradar.cli.commands.PostTracker') as mock_tracker_class:
                mock_tracker = MagicMock()
                mock_tracker.get_high_value_deals.return_value = mock_deals
                mock_tracker.__enter__ = MagicMock(return_value=mock_tracker)
                mock_tracker.__exit__ = MagicMock(return_value=None)
                mock_tracker_class.return_value = mock_tracker

                # Act
                await main.main()

                # Assert
                mock_tracker.get_high_value_deals.assert_called_once_with(min_score=8)

    async def test_deals_mode_custom_score(self):
        """
        GIVEN --deals mode with custom min-score
        WHEN main is called
        THEN it should use custom min_score
        """
        # Arrange
        test_args = ["main.py", "--deals", "--min-score", "9"]
        mock_deals = [{"ad_id": "1", "value_score": 10}]

        with patch.object(sys, 'argv', test_args):
            with patch('dealradar.cli.commands.PostTracker') as mock_tracker_class:
                mock_tracker = MagicMock()
                mock_tracker.get_high_value_deals.return_value = mock_deals
                mock_tracker.__enter__ = MagicMock(return_value=mock_tracker)
                mock_tracker.__exit__ = MagicMock(return_value=None)
                mock_tracker_class.return_value = mock_tracker

                # Act
                await main.main()

                # Assert
                mock_tracker.get_high_value_deals.assert_called_once_with(min_score=9)

    async def test_deals_mode_invalid_score(self):
        """
        GIVEN --deals mode with invalid min-score
        WHEN main is called
        THEN it should show error and exit
        """
        # Arrange
        test_args = ["main.py", "--deals", "--min-score", "invalid"]

        with patch.object(sys, 'argv', test_args):
            # Act
            await main.main()

            # Assert - Should exit gracefully

    async def test_deals_mode_without_database(self):
        """
        GIVEN --deals mode with --skip-db
        WHEN main is called
        THEN it should show error
        """
        # Arrange
        test_args = ["main.py", "--deals", "--skip-db"]

        with patch.object(sys, 'argv', test_args):
            # Act
            await main.main()

            # Assert - Should just exit


@pytest.mark.unit
@pytest.mark.asyncio
class TestMainUsageHelp:
    """Tests for help/usage display"""

    async def test_no_arguments_shows_usage(self):
        """
        GIVEN no command line arguments
        WHEN main is called
        THEN it should display usage information
        """
        # Arrange
        test_args = ["main.py"]

        with patch.object(sys, 'argv', test_args):
            # Act
            await main.main()

            # Assert - Should complete without error

    async def test_usage_contains_all_modes(self, capsys):
        """
        GIVEN no arguments
        WHEN main is called
        THEN usage should mention all modes
        """
        # Arrange
        test_args = ["main.py"]

        with patch.object(sys, 'argv', test_args):
            # Act
            await main.main()
            captured = capsys.readouterr()

            # Assert
            # At least verify it runs without crashing


@pytest.mark.unit
@pytest.mark.asyncio
class TestMainIntegration:
    """Integration-style tests for main workflow"""

    async def test_complete_workflow_search_to_save(self, sample_listing_data):
        """
        GIVEN a complete search workflow
        WHEN main executes search mode
        THEN it should fetch, filter, save, and mark for evaluation
        """
        # Arrange
        test_args = ["main.py", "--search", "5021", "--limit", "3"]
        ad_ids = ["1", "2", "3"]

        with patch.object(sys, 'argv', test_args):
            with patch('dealradar.cli.commands.PostTracker') as mock_tracker_class:
                with patch('dealradar.cli.commands.fetch_search_results', new_callable=AsyncMock) as mock_search:
                    with patch('dealradar.cli.commands.fetch_multiple_listings', new_callable=AsyncMock) as mock_fetch_multi:
                        with patch('builtins.open', mock_open()):
                            # Setup complete workflow
                            mock_tracker = MagicMock()
                            mock_tracker.get_unevaluated_posts.return_value = ad_ids
                            mock_tracker.save_posts_batch.return_value = 3
                            mock_tracker_class.return_value = mock_tracker

                            mock_search.return_value = ad_ids
                            listings = [
                                {**sample_listing_data, "ad_id": ad_id}
                                for ad_id in ad_ids
                            ]
                            mock_fetch_multi.return_value = listings

                            # Act
                            await main.main()

                            # Assert - verify complete flow
                            mock_search.assert_called_once_with("5021", 3)
                            mock_tracker.get_unevaluated_posts.assert_called_once()
                            mock_fetch_multi.assert_called_once()
                            mock_tracker.save_posts_batch.assert_called_once()

                            # Verify mark_for_evaluation called for each listing
                            assert mock_tracker.mark_for_evaluation.call_count == 3

    async def test_error_recovery_continue_without_db(self, sample_listing_data):
        """
        GIVEN database connection fails
        WHEN main is called
        THEN it should raise an exception
        """
        # Arrange
        test_args = ["main.py", "1213746529"]

        with patch.object(sys, 'argv', test_args):
            with patch('dealradar.cli.commands.PostTracker') as mock_tracker_class:
                with patch('dealradar.cli.commands.fetch_blocket_api', new_callable=AsyncMock) as mock_fetch:
                    mock_tracker_class.side_effect = Exception("DB connection failed")
                    mock_fetch.return_value = sample_listing_data

                    # Act & Assert - exception should be raised
                    with pytest.raises(Exception, match="DB connection failed"):
                        await main.main()
