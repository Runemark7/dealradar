"""
Blocket CLI Tool
Command-line interface for fetching Blocket listings
"""
import asyncio
import json
from datetime import datetime

from scraper import fetch_blocket_api, fetch_search_results, fetch_multiple_listings

# Keeping the old crawl4ai scraper for potential fallback (unused now)
async def fetch_blocket_listing(url):
    # Define extraction schema for structured data
    schema = {
        "name": "Blocket Listing",
        "baseSelector": "body",
        "fields": [
            {
                "name": "title",
                "selector": "h1",
                "type": "text"
            },
            {
                "name": "price",
                "selector": "[class*='price'], [data-test*='price']",
                "type": "text"
            },
            {
                "name": "description",
                "selector": "[class*='description'], [class*='Description']",
                "type": "text"
            },
            {
                "name": "location",
                "selector": "[class*='location'], [class*='Location']",
                "type": "text"
            },
            {
                "name": "condition",
                "selector": "[class*='condition'], [class*='Condition']",
                "type": "text"
            }
        ]
    }

    async with AsyncWebCrawler(
        verbose=True,
        headless=True,
        # Use stealth mode to avoid detection
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ) as crawler:
        result = await crawler.arun(
            url=url,
            # Wait for main content to load and React to hydrate
            js_code="""
                // Wait for Next.js/React to hydrate
                await new Promise(resolve => setTimeout(resolve, 10000));
                // Scroll to trigger any lazy loading
                window.scrollTo(0, 500);
                await new Promise(resolve => setTimeout(resolve, 1000));
                window.scrollTo(0, document.body.scrollHeight);
                await new Promise(resolve => setTimeout(resolve, 2000));
                // Save full HTML for debugging
                console.log('Page loaded. Body innerHTML length:', document.body.innerHTML.length);
            """,
            # Don't exclude too much initially
            excluded_tags=['script', 'style', 'noscript'],
            bypass_cache=True,
            page_timeout=90000,
            magic=True  # Use magic mode for better JS handling
        )

        # Check if the request was successful
        if not result:
            print("ERROR: Could not fetch data - result is None")
            return None

        # Check for HTTP status/error information
        if hasattr(result, 'status_code') and result.status_code != 200:
            print(f"ERROR: HTTP {result.status_code}")
            if hasattr(result, 'error_message'):
                print(f"Error message: {result.error_message}")
            return None

        # Check if we have any content at all
        if not hasattr(result, 'markdown') or not result.markdown:
            print("ERROR: No content retrieved from the URL")
            if hasattr(result, 'error_message'):
                print(f"Error message: {result.error_message}")
            return None

        # Parse the markdown content to extract structured data
        markdown = result.markdown

        # Debug: Print the markdown to see structure (disabled for production)
        # print("=== RAW MARKDOWN ===")
        # print(markdown[:3000])
        # print("=== END MARKDOWN ===\n")

        # Extract Next.js data from HTML
        next_data = None
        if hasattr(result, 'html') and result.html:
            # Save full HTML to file for inspection
            with open('/tmp/blocket_page.html', 'w', encoding='utf-8') as f:
                f.write(result.html)
            print(f"Full HTML saved to: /tmp/blocket_page.html (length: {len(result.html)} chars)\n")

            # Extract __NEXT_DATA__ JSON
            import re as regex_module
            next_data_match = regex_module.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', result.html, regex_module.DOTALL)
            if next_data_match:
                try:
                    next_data = json.loads(next_data_match.group(1))
                    print("✓ Next.js data extracted successfully\n")
                except json.JSONDecodeError as e:
                    print(f"✗ Failed to parse __NEXT_DATA__: {e}\n")

        # Try to extract from Next.js data first
        listing_data = None
        if next_data and 'props' in next_data and 'pageProps' in next_data['props']:
            props = next_data['props']['pageProps']

            # Check for dehydratedState (React Query data)
            if 'dehydratedState' in props:
                try:
                    queries = props['dehydratedState'].get('queries', [])
                    if queries:
                        # Get the first query's data
                        query_data = queries[0].get('state', {}).get('data', {})
                        if 'context' in query_data and 'gam' in query_data['context']:
                            api_keywords = query_data['context']['gam'].get('api_keywords', {})

                            # URL decode the title
                            import urllib.parse
                            title_raw = api_keywords.get('adtitle', [''])[0]
                            title = urllib.parse.unquote(title_raw) if title_raw else None

                            price_val = api_keywords.get('price', [None])[0]
                            price = f"{price_val} kr" if price_val else None

                            image_url = api_keywords.get('itemimage', [None])[0]

                            listing_data = {
                                "url": url,
                                "title": title,
                                "price": price,
                                "ad_id": api_keywords.get('id', [None])[0],
                                "category_id": api_keywords.get('blocket_section', []),
                                "county": api_keywords.get('county', [None])[0],
                                "municipality": api_keywords.get('municipality', [None])[0],
                                "image": image_url,
                                "ad_type": api_keywords.get('adtype', [None])[0],
                                "full_keywords": api_keywords
                            }
                except Exception as e:
                    print(f"Error extracting from dehydratedState: {e}\n")

        # Fallback to markdown parsing if JSON extraction failed
        if not listing_data or not any(listing_data.get(k) for k in ['title', 'price', 'description']):
            # Extract data using regex patterns (improved)
            title_match = re.search(r'^#+ (.+)$', markdown, re.MULTILINE)
            # Look for price patterns
            price_match = re.search(r'(\d[\d\s]*kr)', markdown, re.IGNORECASE)
            condition_match = re.search(r'(Okej skick|Mycket bra skick|Nyskick|Slitet skick|Begagnat|Nytt)', markdown, re.IGNORECASE)

            # Find description (usually longer text blocks)
            description_lines = []
            lines = markdown.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                # Skip empty lines, headings, and short lines
                if line and not line.startswith('#') and not line.startswith('[') and len(line) > 30:
                    # Check if it's not a menu item or navigation
                    if not any(keyword in line.lower() for keyword in ['kontakta', 'säkerhet', 'villkor', 'företag', 'cookie', 'ladda ned']):
                        description_lines.append(line)

            description = ' '.join(description_lines[:3]) if description_lines else None

            location_match = re.search(r'(?:Plats|Ort)[\s:]*\[?([^\]]+?)\]?(?:\s|$)', markdown, re.IGNORECASE)
            seller_match = re.search(r'(?:Säljare|Annonsör)[\s:]*(.+?)(?:\n|$)', markdown, re.IGNORECASE)

            listing_data = {
                "url": url,
                "title": title_match.group(1).strip() if title_match else None,
                "price": price_match.group(1).strip() if price_match else None,
                "condition": condition_match.group(1).strip() if condition_match else None,
                "description": description,
                "location": location_match.group(1).strip() if location_match else None,
                "seller": seller_match.group(1).strip() if seller_match else None,
                "full_markdown": markdown
            }

        # Check if we extracted any meaningful data
        if any(listing_data.get(key) for key in listing_data if key not in ["url", "full_markdown", "full_data"]):
            print("\n=== EXTRACTED LISTING DATA ===")
            # Print without full_markdown/full_data for readability
            display_data = {k: v for k, v in listing_data.items() if k not in ["full_markdown", "full_data"]}
            print(json.dumps(display_data, indent=2, ensure_ascii=False))
            return listing_data
        else:
            print("ERROR: Could not extract structured data from the page")
            return None

async def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  Single listing:  python main.py <ad_id>")
        print("  Search category: python main.py --search <category_id> [--limit N]")
        print("\nExamples:")
        print("  python main.py 1213746529")
        print("  python main.py --search 5021")
        print("  python main.py --search 5021 --limit 20")
        return

    # Parse arguments
    if sys.argv[1] == "--search":
        # Search mode
        if len(sys.argv) < 3:
            print("ERROR: Category ID required for search mode")
            return

        category_id = sys.argv[2]
        limit = 10  # Default

        # Check for --limit argument
        if "--limit" in sys.argv:
            limit_index = sys.argv.index("--limit")
            if limit_index + 1 < len(sys.argv):
                try:
                    limit = int(sys.argv[limit_index + 1])
                except ValueError:
                    print("ERROR: Invalid limit value")
                    return

        # Fetch search results
        ad_ids = await fetch_search_results(category_id, limit)

        if not ad_ids:
            print("ERROR: No listings found")
            return

        # Fetch full details for all listings
        listings = await fetch_multiple_listings(ad_ids, batch_size=3)

        # Output as JSON
        output = {
            "total_fetched": len(listings),
            "category": category_id,
            "requested_limit": limit,
            "listings": listings
        }

        # Save to file
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"blocket_search_{category_id}_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 60)
        print(f"✓ Saved {len(listings)} listings to: {filename}")
        print("=" * 60)
        print("\nPreview:")
        print(json.dumps(output, indent=2, ensure_ascii=False)[:500] + "...")

    else:
        # Single listing mode
        ad_id = sys.argv[1]

        listing_data = await fetch_blocket_api(ad_id)

        if listing_data:
            # Save to file
            filename = f"blocket_listing_{ad_id}.json"

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(listing_data, f, indent=2, ensure_ascii=False)

            print(f"\n✓ Saved listing to: {filename}")
            print("\n=== EXTRACTED LISTING DATA ===")
            print(json.dumps(listing_data, indent=2, ensure_ascii=False))

            if listing_data.get('description'):
                print("\n=== BESKRIVNING (DESCRIPTION) ===")
                print(listing_data['description'])
                print("=" * 40)
        else:
            print("\nERROR: Failed to fetch listing data")

if __name__ == "__main__":
    asyncio.run(main())
