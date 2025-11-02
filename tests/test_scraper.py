"""
Unit tests for scraper.py module
Tests the Blocket API scraping functionality
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import json

from dealradar.api.scraper import (
    fetch_search_results,
    fetch_blocket_api,
    fetch_multiple_listings,
)
from dealradar.api.client import get_auth_token
from dealradar.config.settings import settings

# Constants for testing
SITE_URL = settings.SITE_URL
API_URL = settings.API_URL
USER_AGENT = settings.USER_AGENT


@pytest.mark.unit
@pytest.mark.asyncio
class TestGetAuthToken:
    """Tests for get_auth_token function"""

    async def test_get_auth_token_success(self, auth_token_response):
        """
        GIVEN a valid Blocket API endpoint
        WHEN get_auth_token is called
        THEN it should return a valid bearer token
        """
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = auth_token_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Clear global token cache
            from dealradar.api import client
            client._auth_token = None

            # Act
            token = await get_auth_token()

            # Assert
            assert token == auth_token_response["bearerToken"]
            mock_client.get.assert_called_once_with(
                f"{SITE_URL}/api/adout-api-route/refresh-token-and-validate-session",
                headers={"User-Agent": USER_AGENT},
                timeout=30.0
            )

    async def test_get_auth_token_cached(self, auth_token_response):
        """
        GIVEN an already cached auth token
        WHEN get_auth_token is called again
        THEN it should return the cached token without API call
        """
        # Arrange
        from dealradar.api import client
        cached_token = "cached_token_123"
        client._auth_token = cached_token

        with patch('httpx.AsyncClient') as mock_client_class:
            # Act
            token = await get_auth_token()

            # Assert
            assert token == cached_token
            mock_client_class.assert_not_called()

    async def test_get_auth_token_http_error(self):
        """
        GIVEN a Blocket API that returns an error
        WHEN get_auth_token is called
        THEN it should return None
        """
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            from dealradar.api import client
            client._auth_token = None

            # Act
            token = await get_auth_token()

            # Assert
            assert token is None

    async def test_get_auth_token_missing_token_in_response(self):
        """
        GIVEN an API response without bearerToken
        WHEN get_auth_token is called
        THEN it should return None
        """
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "no token"}

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            from dealradar.api import client
            client._auth_token = None

            # Act
            token = await get_auth_token()

            # Assert
            assert token is None

    async def test_get_auth_token_network_exception(self):
        """
        GIVEN a network error occurs
        WHEN get_auth_token is called
        THEN it should handle the exception and return None
        """
        # Arrange
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = httpx.RequestError("Network error")
            mock_client_class.return_value = mock_client

            from dealradar.api import client
            client._auth_token = None

            # Act
            token = await get_auth_token()

            # Assert
            assert token is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestFetchSearchResults:
    """Tests for fetch_search_results function"""

    async def test_fetch_search_results_success(self, sample_search_response, auth_token_response):
        """
        GIVEN a valid category ID and limit
        WHEN fetch_search_results is called
        THEN it should return a list of ad IDs sorted by timestamp
        """
        # Arrange
        category_id = "5021"
        limit = 2

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_search_response

        with patch('dealradar.api.scraper.get_auth_token', new_callable=AsyncMock, return_value=auth_token_response["bearerToken"]):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get.return_value = mock_response
                mock_client_class.return_value = mock_client

                # Act
                ad_ids = await fetch_search_results(category_id, limit)

                # Assert
                assert len(ad_ids) == limit
                assert ad_ids == ["1213746529", "1213746530"]  # Sorted by timestamp, newest first

                # Verify API call
                call_args = mock_client.get.call_args
                assert f"{API_URL}/search_bff/v2/content" in str(call_args)

    async def test_fetch_search_results_no_auth_token(self):
        """
        GIVEN get_auth_token returns None
        WHEN fetch_search_results is called
        THEN it should return an empty list
        """
        # Arrange
        with patch('dealradar.api.scraper.get_auth_token', new_callable=AsyncMock, return_value=None):
            # Act
            ad_ids = await fetch_search_results("5021", 10)

            # Assert
            assert ad_ids == []

    async def test_fetch_search_results_api_error(self, auth_token_response):
        """
        GIVEN the API returns an error status code
        WHEN fetch_search_results is called
        THEN it should return an empty list
        """
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"

        with patch('dealradar.api.scraper.get_auth_token', new_callable=AsyncMock, return_value=auth_token_response["bearerToken"]):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get.return_value = mock_response
                mock_client_class.return_value = mock_client

                # Act
                ad_ids = await fetch_search_results("5021", 10)

                # Assert
                assert ad_ids == []

    async def test_fetch_search_results_empty_data(self, auth_token_response):
        """
        GIVEN the API returns empty data
        WHEN fetch_search_results is called
        THEN it should return an empty list
        """
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}

        with patch('dealradar.api.scraper.get_auth_token', new_callable=AsyncMock, return_value=auth_token_response["bearerToken"]):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get.return_value = mock_response
                mock_client_class.return_value = mock_client

                # Act
                ad_ids = await fetch_search_results("5021", 10)

                # Assert
                assert ad_ids == []

    async def test_fetch_search_results_limit_clamping(self, sample_search_response, auth_token_response):
        """
        GIVEN a limit above API maximum (99)
        WHEN fetch_search_results is called
        THEN it should clamp the limit to API maximum
        """
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_search_response

        with patch('dealradar.api.scraper.get_auth_token', new_callable=AsyncMock, return_value=auth_token_response["bearerToken"]):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get.return_value = mock_response
                mock_client_class.return_value = mock_client

                # Act
                await fetch_search_results("5021", 150)

                # Assert
                call_args = mock_client.get.call_args
                params = call_args.kwargs.get('params', {})
                assert params['lim'] == 99  # Clamped to max

    async def test_fetch_search_results_exception_handling(self, auth_token_response):
        """
        GIVEN an exception occurs during API call
        WHEN fetch_search_results is called
        THEN it should handle the exception and return empty list
        """
        # Arrange
        with patch('dealradar.api.scraper.get_auth_token', new_callable=AsyncMock, return_value=auth_token_response["bearerToken"]):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get.side_effect = Exception("Unexpected error")
                mock_client_class.return_value = mock_client

                # Act
                ad_ids = await fetch_search_results("5021", 10)

                # Assert
                assert ad_ids == []


@pytest.mark.unit
@pytest.mark.asyncio
class TestFetchBlocketApi:
    """Tests for fetch_blocket_api function"""

    async def test_fetch_blocket_api_success(self, sample_api_response, auth_token_response):
        """
        GIVEN a valid ad ID
        WHEN fetch_blocket_api is called
        THEN it should return properly formatted listing data
        """
        # Arrange
        ad_id = "1213746529"

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.content = json.dumps(sample_api_response).encode('utf-8')

        with patch('dealradar.api.scraper.get_auth_token', new_callable=AsyncMock, return_value=auth_token_response["bearerToken"]):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get.return_value = mock_response
                mock_client_class.return_value = mock_client

                # Act
                listing_data = await fetch_blocket_api(ad_id)

                # Assert
                assert listing_data is not None
                assert listing_data['ad_id'] == ad_id
                assert listing_data['title'] == "Gaming Laptop - RTX 3080"
                assert listing_data['price'] == "15000 kr"
                assert listing_data['location'] == "Stockholm"
                assert len(listing_data['images']) == 2
                assert listing_data['seller'] == "John Doe"
                assert listing_data['company_ad'] is False

    async def test_fetch_blocket_api_no_auth_token(self):
        """
        GIVEN get_auth_token returns None
        WHEN fetch_blocket_api is called
        THEN it should return None
        """
        # Arrange
        with patch('dealradar.api.scraper.get_auth_token', new_callable=AsyncMock, return_value=None):
            # Act
            result = await fetch_blocket_api("1213746529")

            # Assert
            assert result is None

    async def test_fetch_blocket_api_http_error(self, auth_token_response):
        """
        GIVEN the API returns an error status
        WHEN fetch_blocket_api is called
        THEN it should return None
        """
        # Arrange
        mock_response = AsyncMock()
        mock_response.status_code = 404

        with patch('dealradar.api.scraper.get_auth_token', new_callable=AsyncMock, return_value=auth_token_response["bearerToken"]):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get.return_value = mock_response
                mock_client_class.return_value = mock_client

                # Act
                result = await fetch_blocket_api("1213746529")

                # Assert
                assert result is None

    async def test_fetch_blocket_api_missing_data(self, auth_token_response):
        """
        GIVEN API response without 'data' field
        WHEN fetch_blocket_api is called
        THEN it should return None
        """
        # Arrange
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.content = json.dumps({"error": "no data"}).encode('utf-8')

        with patch('dealradar.api.scraper.get_auth_token', new_callable=AsyncMock, return_value=auth_token_response["bearerToken"]):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get.return_value = mock_response
                mock_client_class.return_value = mock_client

                # Act
                result = await fetch_blocket_api("1213746529")

                # Assert
                assert result is None

    async def test_fetch_blocket_api_handles_missing_optional_fields(self, auth_token_response):
        """
        GIVEN API response with missing optional fields
        WHEN fetch_blocket_api is called
        THEN it should handle None values gracefully
        """
        # Arrange
        minimal_response = {
            "data": {
                "ad_id": "1213746529",
                "subject": "Test Item"
                # Missing: price, location, images, etc.
            }
        }

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.content = json.dumps(minimal_response).encode('utf-8')

        with patch('dealradar.api.scraper.get_auth_token', new_callable=AsyncMock, return_value=auth_token_response["bearerToken"]):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get.return_value = mock_response
                mock_client_class.return_value = mock_client

                # Act
                result = await fetch_blocket_api("1213746529")

                # Assert
                assert result is not None
                assert result['ad_id'] == "1213746529"
                assert result['title'] == "Test Item"
                assert result['price'] is None
                assert result['images'] == []

    async def test_fetch_blocket_api_exception_handling(self, auth_token_response):
        """
        GIVEN an exception occurs during API call
        WHEN fetch_blocket_api is called
        THEN it should handle the exception and return None
        """
        # Arrange
        with patch('dealradar.api.scraper.get_auth_token', new_callable=AsyncMock, return_value=auth_token_response["bearerToken"]):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.get.side_effect = Exception("Network error")
                mock_client_class.return_value = mock_client

                # Act
                result = await fetch_blocket_api("1213746529")

                # Assert
                assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
class TestFetchMultipleListings:
    """Tests for fetch_multiple_listings function"""

    async def test_fetch_multiple_listings_success(self, sample_listing_data, auth_token_response):
        """
        GIVEN a list of ad IDs
        WHEN fetch_multiple_listings is called
        THEN it should return all listings
        """
        # Arrange
        ad_ids = ["1213746529", "1213746530", "1213746531"]

        with patch('dealradar.api.scraper.get_auth_token', new_callable=AsyncMock, return_value=auth_token_response["bearerToken"]):
            with patch('dealradar.api.scraper.fetch_blocket_api', new_callable=AsyncMock) as mock_fetch:
                mock_fetch.return_value = sample_listing_data

                # Act
                listings = await fetch_multiple_listings(ad_ids, batch_size=2)

                # Assert
                assert len(listings) == 3
                assert mock_fetch.call_count == 3

    async def test_fetch_multiple_listings_with_failures(self, sample_listing_data, auth_token_response):
        """
        GIVEN some API calls fail
        WHEN fetch_multiple_listings is called
        THEN it should return only successful listings
        """
        # Arrange
        ad_ids = ["1213746529", "1213746530", "1213746531"]

        with patch('dealradar.api.scraper.get_auth_token', new_callable=AsyncMock, return_value=auth_token_response["bearerToken"]):
            with patch('dealradar.api.scraper.fetch_blocket_api', new_callable=AsyncMock) as mock_fetch:
                # Second call returns None (failure)
                mock_fetch.side_effect = [sample_listing_data, None, sample_listing_data]

                # Act
                listings = await fetch_multiple_listings(ad_ids, batch_size=3)

                # Assert
                assert len(listings) == 2  # Only successful ones

    async def test_fetch_multiple_listings_with_exceptions(self, sample_listing_data, auth_token_response):
        """
        GIVEN some API calls raise exceptions
        WHEN fetch_multiple_listings is called
        THEN it should filter out exceptions and continue
        """
        # Arrange
        ad_ids = ["1213746529", "1213746530"]

        with patch('dealradar.api.scraper.get_auth_token', new_callable=AsyncMock, return_value=auth_token_response["bearerToken"]):
            with patch('dealradar.api.scraper.fetch_blocket_api', new_callable=AsyncMock) as mock_fetch:
                # First succeeds, second raises exception
                mock_fetch.side_effect = [sample_listing_data, Exception("API Error")]

                # Act
                listings = await fetch_multiple_listings(ad_ids, batch_size=2)

                # Assert
                assert len(listings) == 1

    async def test_fetch_multiple_listings_no_auth_token(self):
        """
        GIVEN get_auth_token returns None
        WHEN fetch_multiple_listings is called
        THEN it should return empty list
        """
        # Arrange
        ad_ids = ["1213746529", "1213746530"]

        with patch('dealradar.api.scraper.fetch_blocket_api', new_callable=AsyncMock, return_value=None):
            # Act
            listings = await fetch_multiple_listings(ad_ids)

            # Assert
            assert listings == []

    async def test_fetch_multiple_listings_batching(self, sample_listing_data, auth_token_response):
        """
        GIVEN a batch_size parameter
        WHEN fetch_multiple_listings is called
        THEN it should process listings in batches
        """
        # Arrange
        ad_ids = ["1", "2", "3", "4", "5"]
        batch_size = 2

        with patch('dealradar.api.scraper.get_auth_token', new_callable=AsyncMock, return_value=auth_token_response["bearerToken"]):
            with patch('dealradar.api.scraper.fetch_blocket_api', new_callable=AsyncMock) as mock_fetch:
                mock_fetch.return_value = sample_listing_data

                with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                    # Act
                    listings = await fetch_multiple_listings(ad_ids, batch_size=batch_size)

                    # Assert
                    assert len(listings) == 5
                    # Should have 2 delays between 3 batches (5 items / batch_size=2 = 3 batches)
                    assert mock_sleep.call_count == 2

    async def test_fetch_multiple_listings_empty_list(self, auth_token_response):
        """
        GIVEN an empty list of ad IDs
        WHEN fetch_multiple_listings is called
        THEN it should return an empty list
        """
        # Arrange
        with patch('dealradar.api.scraper.get_auth_token', new_callable=AsyncMock, return_value=auth_token_response["bearerToken"]):
            # Act
            listings = await fetch_multiple_listings([])

            # Assert
            assert listings == []
