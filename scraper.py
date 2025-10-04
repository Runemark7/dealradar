"""
Blocket scraper module
Contains all scraping logic for fetching Blocket listings
Uses direct HTTP API calls instead of browser automation
"""
import asyncio
import json
import httpx
from datetime import datetime

# Blocket API constants
SITE_URL = "https://www.blocket.se"
API_URL = "https://api.blocket.se"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

# Global token cache
_auth_token = None


async def get_auth_token():
    """
    Get authentication token from Blocket's public endpoint.
    Token is cached for reuse.

    Returns:
        str: Bearer token for API authentication
    """
    global _auth_token

    if _auth_token:
        return _auth_token

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SITE_URL}/api/adout-api-route/refresh-token-and-validate-session",
                headers={"User-Agent": USER_AGENT},
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                _auth_token = data.get('bearerToken')
                if _auth_token:
                    print(f"✓ Retrieved authentication token")
                    return _auth_token
                else:
                    print(f"ERROR: Token not found in response. Response data: {data}")
                    return None
            else:
                print(f"ERROR: Failed to get token (HTTP {response.status_code})")
                return None

    except Exception as e:
        print(f"ERROR: Failed to fetch auth token: {e}")
        return None


async def fetch_search_results(category_id, limit=10):
    """
    Fetch search results from Blocket API directly using HTTP requests.

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
        api_url = f"{API_URL}/search_bff/v2/content"
        params = {
            "cg": category_id,
            "lim": min(max(limit, 50), 99),  # API max is 99
            "status": "active"
        }

        headers = {
            "User-Agent": USER_AGENT,
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                api_url,
                params=params,
                headers=headers,
                timeout=30.0
            )

            if response.status_code != 200:
                print(f"ERROR: API returned status {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return []

            search_api_data = response.json()

            if search_api_data and 'data' in search_api_data:
                ads = search_api_data['data']

                # Sort by timestamp (newest first)
                sorted_ads = sorted(ads, key=lambda x: x.get('list_time', x.get('timestamp', 0)), reverse=True)

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


async def fetch_blocket_api(ad_id):
    """
    Fetch listing data directly from Blocket's API using HTTP requests.

    Args:
        ad_id: The Blocket ad ID (e.g., "1213746529")

    Returns:
        Dictionary with listing data or None if failed
    """
    try:
        print(f"[API].... Fetching from Blocket API for ad {ad_id}...")

        # Get auth token first
        token = await get_auth_token()
        if not token:
            print("ERROR: Could not get authentication token")
            return None

        # Build API request for single listing
        api_url = f"{API_URL}/search_bff/v2/content/{ad_id}"

        headers = {
            "User-Agent": USER_AGENT,
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                api_url,
                headers=headers,
                timeout=30.0
            )

            if response.status_code != 200:
                print(f"ERROR: API returned status {response.status_code}")
                return None

            api_response_data = response.json()

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


async def fetch_multiple_listings(ad_ids, batch_size=10):
    """
    Fetch multiple listings in parallel using HTTP requests.
    Much faster than browser automation.

    Args:
        ad_ids: List of ad IDs to fetch
        batch_size: Number of parallel requests per batch (default 10)

    Returns:
        List of listing data dictionaries
    """
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
            await asyncio.sleep(0.5)

    print(f"\n✓ Successfully fetched {len(all_listings)}/{len(ad_ids)} listings")
    return all_listings