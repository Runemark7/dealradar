"""
Pytest fixtures and configuration for DealRadar tests
"""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime
import psycopg2


@pytest.fixture
def sample_listing_data():
    """Sample listing data for testing"""
    return {
        "ad_id": "1213746529",
        "title": "Gaming Laptop - RTX 3080",
        "description": "High-end gaming laptop in excellent condition",
        "price": "15000 kr",
        "location": "Stockholm",
        "category": "Computers",
        "images": ["https://example.com/img1.jpg", "https://example.com/img2.jpg"],
        "seller": "John Doe",
        "company_ad": False,
        "type": "sell",
        "region": "Stockholm"
    }


@pytest.fixture
def sample_api_response():
    """Sample Blocket API response for testing"""
    return {
        "data": {
            "ad_id": "1213746529",
            "subject": "Gaming Laptop - RTX 3080",
            "body": "High-end gaming laptop in excellent condition",
            "price": {"value": 15000},
            "location": {"name": "Stockholm", "region": {"name": "Stockholm"}},
            "category": {"name": "Computers"},
            "images": [
                {"url": "https://example.com/img1.jpg"},
                {"url": "https://example.com/img2.jpg"}
            ],
            "advertiser": {"name": "John Doe"},
            "company_ad": False,
            "type": "sell"
        }
    }


@pytest.fixture
def sample_search_response():
    """Sample search API response"""
    return {
        "data": [
            {
                "ad_id": "1213746529",
                "subject": "Gaming Laptop",
                "list_time": 1234567890,
                "timestamp": 1234567890
            },
            {
                "ad_id": "1213746530",
                "subject": "Desktop PC",
                "list_time": 1234567880,
                "timestamp": 1234567880
            },
            {
                "ad_id": "1213746531",
                "subject": "Monitor",
                "list_time": 1234567870,
                "timestamp": 1234567870
            }
        ]
    }


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient for API calls"""
    mock_client = MagicMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_client.get = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.fixture
def mock_db_connection():
    """Mock database connection"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Configure cursor as context manager
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=None)

    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    mock_conn.commit = MagicMock()
    mock_conn.rollback = MagicMock()
    mock_conn.close = MagicMock()

    return mock_conn


@pytest.fixture
def mock_cursor():
    """Mock database cursor"""
    cursor = MagicMock()
    cursor.execute = MagicMock()
    cursor.fetchone = MagicMock()
    cursor.fetchall = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=None)
    return cursor


@pytest.fixture
def db_config():
    """Test database configuration"""
    return {
        'host': 'localhost',
        'port': '5432',
        'database': 'test_dealradar',
        'user': 'test_user',
        'password': 'test_password'
    }


@pytest.fixture
def sample_stats():
    """Sample database statistics"""
    return {
        'total_posts': 100,
        'evaluated_posts': 75,
        'pending_evaluations': 20,
        'failed_evaluations': 5,
        'high_value_deals': 10,
        'avg_score': 6.5
    }


@pytest.fixture
def auth_token_response():
    """Sample auth token response"""
    return {
        "bearerToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token"
    }


@pytest.fixture
def mock_post_tracker(mock_db_connection):
    """Mock PostTracker instance"""
    from unittest.mock import patch

    with patch('psycopg2.connect', return_value=mock_db_connection):
        from db_tracker import PostTracker
        tracker = PostTracker()
        return tracker
