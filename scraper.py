"""
Blocket scraper module
Contains all scraping logic for fetching Blocket listings
"""
import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright


async def fetch_search_results(category_id, limit=10):
    """
    Fetch search results from Blocket and extract ad IDs sorted by newest first.

    Args:
        category_id: Blocket category ID (e.g., "5021")
        limit: Number of latest listings to return (default 10)

    Returns:
        List of ad IDs sorted by timestamp (newest first)
    """
    try:
        print(f"[SEARCH] Fetching listings from category {category_id}...")

        search_url = f"https://www.blocket.se/annonser/hela_sverige/datorer?cg={category_id}"
        search_api_data = None
        api_captured = False

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()

            # Intercept search API requests
            async def handle_response(response):
                nonlocal search_api_data, api_captured
                if 'api.blocket.se/search_bff/v2/content' in response.url and response.status == 200:
                    # Make sure it's the search endpoint, not individual content
                    if 'cg=' in response.url and '/content?' in response.url:
                        try:
                            search_api_data = await response.json()
                            api_captured = True
                            print(f"✓ Intercepted search API response")
                        except Exception as e:
                            print(f"✗ Failed to parse API response: {e}")

            page.on('response', handle_response)

            # Visit search page to trigger API call
            await page.goto(search_url, wait_until='domcontentloaded', timeout=30000)

            # Wait for API to be captured (max 5 seconds)
            for i in range(50):  # 50 * 0.1 = 5 seconds
                if api_captured:
                    break
                await asyncio.sleep(0.1)

            # Close browser AFTER all async operations complete
            await browser.close()

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


async def fetch_blocket_api(ad_id, page=None):
    """
    Fetch listing data directly from Blocket's API using Playwright.
    Intercepts network requests to capture the API call made by the page itself.

    Args:
        ad_id: The Blocket ad ID (e.g., "1213746529")
        page: Optional Playwright page instance to reuse (if None, creates new browser)

    Returns:
        Dictionary with listing data or None if failed
    """
    try:
        print(f"[API].... Fetching from Blocket API for ad {ad_id}...")

        # We need to visit a Blocket page to trigger the API call
        url = f"https://www.blocket.se/annons/{ad_id}"

        api_response_data = None

        # If page provided, reuse it; otherwise create temporary browser
        if page:
            # Intercept API requests
            async def handle_response(response):
                nonlocal api_response_data
                if 'api.blocket.se' in response.url and ad_id in response.url and response.status == 200:
                    # Only capture the main content API, not related_content
                    if '/search_bff/v2/content/' in response.url and 'related_content' not in response.url:
                        try:
                            api_response_data = await response.json()
                            print(f"✓ Intercepted API response")
                        except:
                            pass

            page.on('response', handle_response)

            try:
                # Visit the page - this will trigger the API call
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                # Wait a bit for API call to complete
                await asyncio.sleep(2)
            finally:
                # Always remove the listener, even if navigation fails
                page.remove_listener('response', handle_response)

        else:
            # Fallback: create temporary browser instance
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                page = await context.new_page()

                # Intercept API requests
                async def handle_response(response):
                    nonlocal api_response_data
                    if 'api.blocket.se' in response.url and ad_id in response.url and response.status == 200:
                        # Only capture the main content API, not related_content
                        if '/search_bff/v2/content/' in response.url and 'related_content' not in response.url:
                            try:
                                api_response_data = await response.json()
                                print(f"✓ Intercepted API response")
                            except:
                                pass

                page.on('response', handle_response)

                # Visit the page - this will trigger the API call
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                # Wait a bit for API call to complete
                await asyncio.sleep(2)

                await browser.close()

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
            print("ERROR: Could not intercept API response")
            return None

    except Exception as e:
        import traceback
        print(f"ERROR: Failed to fetch from API: {e}")
        traceback.print_exc()
        return None


async def fetch_multiple_listings(ad_ids, batch_size=3):
    """
    Fetch multiple listings in batches using a single shared browser instance.
    Much more memory efficient than creating separate browsers for each listing.

    Args:
        ad_ids: List of ad IDs to fetch
        batch_size: Number of parallel pages per batch (default 3)

    Returns:
        List of listing data dictionaries
    """
    all_listings = []

    print(f"\n[BATCH] Fetching {len(ad_ids)} listings using shared browser...")

    async with async_playwright() as p:
        # Launch ONE browser for all requests
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # Process in batches
        for i in range(0, len(ad_ids), batch_size):
            batch = ad_ids[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(ad_ids) + batch_size - 1) // batch_size

            print(f"\n[BATCH {batch_num}/{total_batches}] Fetching {len(batch)} listings...")

            # Create separate pages for parallel requests within this batch
            pages = [await context.new_page() for _ in batch]

            # Fetch batch in parallel using the shared browser
            tasks = [fetch_blocket_api(ad_id, page) for ad_id, page in zip(batch, pages)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Close pages to free memory
            for page in pages:
                await page.close()

            # Filter out None results and exceptions
            for result in results:
                if result and not isinstance(result, Exception):
                    all_listings.append(result)

            # Small delay between batches to be nice to the server
            if i + batch_size < len(ad_ids):
                await asyncio.sleep(1)

        await browser.close()

    print(f"\n✓ Successfully fetched {len(all_listings)}/{len(ad_ids)} listings")
    return all_listings