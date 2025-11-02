"""
Blocket scraper module
High-level functions for fetching Blocket listings via API
"""
import asyncio
import json
import httpx
from typing import List, Dict, Optional

from .client import get_auth_token, get_api_headers
from ..config import settings


async def fetch_search_results(category_id: str, limit: int = 10) -> List[str]:
    """
    Fetch search results from Blocket API.

    Args:
        category_id: Blocket category ID (e.g., "5021")
        limit: Number of latest listings to return (default 10)

    Returns:
        List of ad IDs sorted by timestamp (newest first)
    """
    try:
        print(f"[SEARCH] Fetching listings from category {category_id}...")

        # Get auth token first
        token = await get_auth_token()
        if not token:
            print("ERROR: Could not get authentication token")
            return []

        # Build API request
        api_url = f"{settings.API_URL}/search_bff/v2/content"
        params = {
            "cg": category_id,
            "lim": min(max(limit, 50), 99),  # API max is 99
            "status": "active"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                api_url,
                params=params,
                headers=get_api_headers(token),
                timeout=settings.API_TIMEOUT_SECONDS
            )

            if response.status_code != 200:
                print(f"ERROR: API returned status {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return []

            search_api_data = response.json()

            if search_api_data and 'data' in search_api_data:
                ads = search_api_data['data']

                # Sort by timestamp (newest first)
                sorted_ads = sorted(
                    ads,
                    key=lambda x: x.get('list_time', x.get('timestamp', 0)),
                    reverse=True
                )

                # Extract ad IDs for the top N listings
                ad_ids = [ad['ad_id'] for ad in sorted_ads[:limit]]

                print(f"✓ Found {len(ads)} listings, returning top {len(ad_ids)}")
                return ad_ids
            else:
                print("ERROR: Could not fetch search results")
                return []

    except Exception as e:
        import traceback
        print(f"ERROR: Failed to fetch search results: {e}")
        traceback.print_exc()
        return []


async def fetch_recent_search_results(category_id: str, max_age_hours: int = 1, limit: int = 50) -> List[str]:
    """
    Fetch search results from Blocket API filtered by age.

    Args:
        category_id: Blocket category ID (e.g., "5021")
        max_age_hours: Maximum age of listings in hours (default 1)
        limit: Maximum number of listings to return (default 50)

    Returns:
        List of ad IDs for posts within the time window, sorted by timestamp (newest first)
    """
    try:
        from datetime import datetime, timedelta, timezone

        print(f"[RECENT] Fetching listings from last {max_age_hours} hour(s) in category {category_id}...")

        # Get auth token first
        token = await get_auth_token()
        if not token:
            print("ERROR: Could not get authentication token")
            return []

        # Fetch more results than needed to account for filtering
        # (API max is 99)
        fetch_limit = min(99, limit * 3)

        # Build API request
        api_url = f"{settings.API_URL}/search_bff/v2/content"
        params = {
            "cg": category_id,
            "lim": fetch_limit,
            "status": "active"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                api_url,
                params=params,
                headers=get_api_headers(token),
                timeout=settings.API_TIMEOUT_SECONDS
            )

            if response.status_code != 200:
                print(f"ERROR: API returned status {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return []

            search_api_data = response.json()

            if search_api_data and 'data' in search_api_data:
                ads = search_api_data['data']

                # Calculate cutoff timestamp (current time - max_age_hours)
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
                cutoff_timestamp = int(cutoff_time.timestamp())

                # Filter by timestamp
                recent_ads = []
                for ad in ads:
                    # Check list_time first, fall back to timestamp
                    ad_timestamp = ad.get('list_time') or ad.get('timestamp', 0)

                    # Handle both seconds and milliseconds timestamps
                    if ad_timestamp > 10000000000:  # Likely milliseconds
                        ad_timestamp = ad_timestamp / 1000

                    if ad_timestamp >= cutoff_timestamp:
                        recent_ads.append(ad)

                # Sort by timestamp (newest first)
                sorted_ads = sorted(
                    recent_ads,
                    key=lambda x: x.get('list_time', x.get('timestamp', 0)),
                    reverse=True
                )

                # Extract ad IDs for the top N listings
                ad_ids = [ad['ad_id'] for ad in sorted_ads[:limit]]

                print(f"✓ Found {len(ads)} total listings, {len(recent_ads)} from last {max_age_hours}h, returning top {len(ad_ids)}")
                return ad_ids
            else:
                print("ERROR: Could not fetch search results")
                return []

    except Exception as e:
        import traceback
        print(f"ERROR: Failed to fetch recent search results: {e}")
        traceback.print_exc()
        return []


async def fetch_blocket_api(ad_id: str) -> Optional[Dict]:
    """
    Fetch listing data directly from Blocket's API.

    Args:
        ad_id: The Blocket ad ID (e.g., "1213746529")

    Returns:
        Dictionary with listing data or None if failed
    """
    try:
        print(f"[API] Fetching from Blocket API for ad {ad_id}...")

        # Get auth token first
        token = await get_auth_token()
        if not token:
            print("ERROR: Could not get authentication token")
            return None

        # Build API request for single listing
        api_url = f"{settings.API_URL}/search_bff/v2/content/{ad_id}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                api_url,
                headers=get_api_headers(token),
                timeout=settings.API_TIMEOUT_SECONDS
            )

            if response.status_code != 200:
                print(f"ERROR: API returned status {response.status_code}")
                return None

            api_response_data = json.loads(response.content.decode("utf-8"))

            if api_response_data and 'data' in api_response_data:
                listing = api_response_data['data']

                # Extract all relevant fields
                listing_data = {
                    "ad_id": listing.get('ad_id'),
                    "title": listing.get('subject'),
                    "description": listing.get('body'),
                    "price": f"{listing.get('price', {}).get('value')} kr" if listing.get('price') else None,
                    "location": listing.get('location', {}).get('name') if isinstance(listing.get('location'), dict) else None,
                    "category": listing.get('category', {}).get('name') if isinstance(listing.get('category'), dict) else None,
                    "images": [img.get('url') for img in listing.get('images', [])] if listing.get('images') else [],
                    "seller": listing.get('advertiser', {}).get('name') if isinstance(listing.get('advertiser'), dict) else None,
                    "company_ad": listing.get('company_ad', False),
                    "type": listing.get('type'),
                    "region": listing.get('location', {}).get('region', {}).get('name') if isinstance(listing.get('location'), dict) else None,
                }

                print("✓ API data fetched successfully\n")
                return listing_data
            else:
                print("ERROR: Could not fetch API response")
                return None

    except Exception as e:
        import traceback
        print(f"ERROR: Failed to fetch from API: {e}")
        traceback.print_exc()
        return None


async def fetch_multiple_listings(ad_ids: List[str], batch_size: int = None) -> List[Dict]:
    """
    Fetch multiple listings in parallel using HTTP requests.

    Args:
        ad_ids: List of ad IDs to fetch
        batch_size: Number of parallel requests per batch (uses settings default if None)

    Returns:
        List of listing data dictionaries
    """
    if batch_size is None:
        batch_size = settings.DEFAULT_BATCH_SIZE

    all_listings = []

    print(f"\n[BATCH] Fetching {len(ad_ids)} listings using HTTP API...")

    # Get auth token once for all requests
    token = await get_auth_token()
    if not token:
        print("ERROR: Could not get authentication token")
        return []

    # Process in batches
    for i in range(0, len(ad_ids), batch_size):
        batch = ad_ids[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(ad_ids) + batch_size - 1) // batch_size

        print(f"\n[BATCH {batch_num}/{total_batches}] Fetching {len(batch)} listings...")

        # Fetch batch in parallel
        tasks = [fetch_blocket_api(ad_id) for ad_id in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None results and exceptions
        for result in results:
            if result and not isinstance(result, Exception):
                all_listings.append(result)

        # Small delay between batches to be nice to the server
        if i + batch_size < len(ad_ids):
            await asyncio.sleep(settings.BATCH_DELAY_SECONDS)

    print(f"\n✓ Successfully fetched {len(all_listings)}/{len(ad_ids)} listings")
    return all_listings
