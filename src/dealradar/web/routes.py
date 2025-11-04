"""
Flask API routes
Defines all HTTP endpoints for the web service
"""
import asyncio
from flask import jsonify, request, render_template_string
import psycopg2
from psycopg2.extras import RealDictCursor

from ..api import fetch_blocket_api, fetch_search_results, fetch_multiple_listings, fetch_recent_search_results
from ..config import settings


def register_routes(app):
    """Register all routes with the Flask app"""

    @app.route('/api')
    def api_docs():
        """API documentation endpoint"""
        return jsonify({
            "name": "Blocket API Microservice",
            "version": "1.0",
            "endpoints": {
                "single_listing": {
                    "path": "/api/listing/<ad_id>",
                    "method": "GET",
                    "description": "Fetch a single listing by ad_id",
                    "example": "/api/listing/1213746529"
                },
                "category_search": {
                    "path": "/api/search",
                    "method": "GET",
                    "description": "Search listings by category",
                    "parameters": {
                        "category": "Category ID (required)",
                        "limit": "Number of listings to return (default: 10)"
                    },
                    "example": "/api/search?category=5021&limit=10"
                },
                "recent_search": {
                    "path": "/api/search/recent",
                    "method": "GET",
                    "description": "Search for recent listings by category and time window",
                    "parameters": {
                        "category": "Category ID (required)",
                        "hours": "Maximum age of listings in hours (default: 1, max: 168)",
                        "limit": "Number of listings to return (default: 50, max: 99)"
                    },
                    "example": "/api/search/recent?category=5021&hours=1&limit=20"
                },
                "health": {
                    "path": "/health",
                    "method": "GET",
                    "description": "Health check endpoint"
                }
            }
        })

    @app.route('/api/listing/<ad_id>', methods=['GET'])
    def get_listing(ad_id):
        """
        Fetch a single listing by ad_id

        Args:
            ad_id: Blocket ad ID

        Returns:
            JSON response with listing data
        """
        try:
            # Run async function in sync context
            listing_data = asyncio.run(fetch_blocket_api(ad_id))

            if listing_data:
                return jsonify({
                    "success": True,
                    "data": listing_data
                }), 200
            else:
                return jsonify({
                    "success": False,
                    "error": "Listing not found or could not be fetched"
                }), 404

        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/search', methods=['GET'])
    def search_listings():
        """
        Search listings by category

        Query Parameters:
            category: Category ID (required)
            limit: Number of listings to return (default: 10)

        Returns:
            JSON response with search results
        """
        try:
            # Get query parameters
            category_id = request.args.get('category')
            limit = request.args.get('limit', default=settings.DEFAULT_SEARCH_LIMIT, type=int)

            if not category_id:
                return jsonify({
                    "success": False,
                    "error": "Missing required parameter: category"
                }), 400

            # Validate limit
            if limit < 1 or limit > settings.MAX_SEARCH_LIMIT:
                return jsonify({
                    "success": False,
                    "error": f"Limit must be between 1 and {settings.MAX_SEARCH_LIMIT}"
                }), 400

            # Run async functions in sync context
            ad_ids = asyncio.run(fetch_search_results(category_id, limit))

            if not ad_ids:
                return jsonify({
                    "success": False,
                    "error": "No listings found for this category"
                }), 404

            # Fetch full details for all listings
            listings = asyncio.run(fetch_multiple_listings(ad_ids))

            return jsonify({
                "success": True,
                "data": {
                    "total_fetched": len(listings),
                    "category": category_id,
                    "requested_limit": limit,
                    "listings": listings
                }
            }), 200

        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/search/recent', methods=['GET'])
    def search_recent_listings():
        """
        Search for recent listings by category and time window

        Query Parameters:
            category: Category ID (required)
            hours: Maximum age of listings in hours (default: 1)
            limit: Number of listings to return (default: 50)

        Returns:
            JSON response with recent listings
        """
        try:
            # Get query parameters
            category_id = request.args.get('category')
            hours = request.args.get('hours', default=1, type=int)
            limit = request.args.get('limit', default=50, type=int)

            if not category_id:
                return jsonify({
                    "success": False,
                    "error": "Missing required parameter: category"
                }), 400

            # Validate hours
            if hours < 1 or hours > 168:  # Max 1 week
                return jsonify({
                    "success": False,
                    "error": "Hours must be between 1 and 168 (1 week)"
                }), 400

            # Validate limit
            if limit < 1 or limit > 99:
                return jsonify({
                    "success": False,
                    "error": "Limit must be between 1 and 99"
                }), 400

            # Run async function to get recent ad IDs
            ad_ids = asyncio.run(fetch_recent_search_results(category_id, hours, limit))

            if not ad_ids:
                return jsonify({
                    "success": True,
                    "data": {
                        "total_fetched": 0,
                        "category": category_id,
                        "max_age_hours": hours,
                        "requested_limit": limit,
                        "listings": []
                    }
                }), 200

            # Fetch full details for all listings
            listings = asyncio.run(fetch_multiple_listings(ad_ids))

            return jsonify({
                "success": True,
                "data": {
                    "total_fetched": len(listings),
                    "category": category_id,
                    "max_age_hours": hours,
                    "requested_limit": limit,
                    "listings": listings
                }
            }), 200

        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            "status": "healthy",
            "service": "blocket-api"
        }), 200

    def get_db_connection():
        """Create and return a database connection"""
        return psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD
        )

    @app.route('/')
    def deals_page():
        """Serve the deals frontend page"""
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DealRadar - Evaluated Deals</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        header h1 {
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        .search-box {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .search-box input[type="text"] {
            flex: 1;
            padding: 12px 18px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 15px;
            transition: border-color 0.3s;
        }
        .search-box input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        .search-box button {
            padding: 12px 30px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            font-size: 15px;
            transition: background 0.3s;
            white-space: nowrap;
        }
        .search-box button:hover {
            background: #5568d3;
        }
        .search-box button.secondary {
            background: #6c757d;
        }
        .search-box button.secondary:hover {
            background: #5a6268;
        }
        .filters {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }
        .filters label {
            font-weight: 600;
            color: #333;
        }
        .filters select, .filters input {
            padding: 8px 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
        }
        .filters button {
            padding: 8px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            transition: background 0.3s;
        }
        .filters button:hover {
            background: #5568d3;
        }
        #deals-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
        }
        .deal-card {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .deal-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.15);
        }
        .deal-header {
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .deal-score {
            display: inline-block;
            background: rgba(255,255,255,0.3);
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 1.2em;
            margin-bottom: 10px;
        }
        .deal-title {
            font-size: 1.3em;
            font-weight: 600;
            margin-bottom: 8px;
        }
        .deal-price {
            font-size: 1.5em;
            font-weight: bold;
        }
        .deal-body {
            padding: 20px;
        }
        .deal-info {
            margin-bottom: 15px;
        }
        .deal-info-label {
            font-weight: 600;
            color: #666;
            font-size: 0.9em;
            margin-bottom: 5px;
        }
        .deal-info-value {
            color: #333;
        }
        .deal-specs {
            background: #f8f9fa;
            padding: 12px;
            border-radius: 8px;
            margin: 15px 0;
            font-size: 0.9em;
        }
        .deal-specs-item {
            margin: 5px 0;
        }
        .deal-notification {
            background: #e3f2fd;
            padding: 12px;
            border-radius: 8px;
            border-left: 4px solid #2196F3;
            margin: 15px 0;
            font-size: 0.95em;
            color: #1565C0;
        }
        .deal-footer {
            padding: 15px 20px;
            border-top: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .deal-footer a {
            background: #667eea;
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 600;
            transition: background 0.3s;
        }
        .deal-footer a:hover {
            background: #5568d3;
        }
        .deal-date {
            color: #666;
            font-size: 0.85em;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: white;
            font-size: 1.2em;
        }
        .no-deals {
            text-align: center;
            padding: 60px 20px;
            background: white;
            border-radius: 12px;
            color: #666;
        }
        .no-deals h2 {
            font-size: 2em;
            margin-bottom: 10px;
            color: #333;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 DealRadar</h1>
            <p>AI-Evaluated Blocket Deals</p>
        </header>

        <div class="search-box">
            <input type="text"
                   id="search-query"
                   name="query"
                   placeholder="Ask me anything... e.g., 'I have 7000 kr budget, what are the best computer deals?'"
                   />
            <button
                hx-get="/api/search"
                hx-target="#deals-container"
                hx-include="[name='query']"
                hx-indicator="#loading">
                Search
            </button>
            <button
                hx-get="/api/deals?min_score=8&limit=20"
                hx-target="#deals-container"
                hx-indicator="#loading"
                class="secondary">
                Show All
            </button>
        </div>

        <div class="filters">
            <label>Min Score:</label>
            <select id="min-score" name="min_score">
                <option value="1">1+</option>
                <option value="5">5+</option>
                <option value="7">7+</option>
                <option value="8" selected>8+ (High Value)</option>
                <option value="9">9+ (Excellent)</option>
            </select>

            <label>Limit:</label>
            <input type="number" id="limit" name="limit" value="20" min="1" max="100">

            <button
                hx-get="/api/deals"
                hx-target="#deals-container"
                hx-include="[name='min_score'], [name='limit']"
                hx-indicator="#loading">
                Refresh
            </button>
        </div>

        <div id="loading" class="loading htmx-indicator">
            Loading deals...
        </div>

        <div
            id="deals-container"
            hx-get="/api/deals?min_score=8&limit=20"
            hx-trigger="load"
            hx-swap="innerHTML">
        </div>
    </div>

    <script>
        // Auto-refresh every 5 minutes
        setInterval(() => {
            htmx.trigger('#deals-container', 'load');
        }, 300000);
    </script>
</body>
</html>
"""
        return render_template_string(html)

    @app.route('/api/deals', methods=['GET'])
    def get_deals():
        """API endpoint to fetch evaluated deals"""
        try:
            min_score = request.args.get('min_score', default=8, type=float)
            limit = request.args.get('limit', default=20, type=int)

            # Validate inputs
            if min_score < 1 or min_score > 10:
                min_score = 8
            if limit < 1 or limit > 100:
                limit = 20

            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Query evaluated posts
            query = """
                SELECT
                    p.ad_id,
                    p.title,
                    p.price,
                    p.description,
                    p.location,
                    p.category,
                    p.company_ad,
                    e.value_score,
                    e.evaluation_notes,
                    e.notification_message,
                    e.estimated_market_value,
                    e.specs,
                    e.evaluated_at
                FROM posts p
                INNER JOIN evaluations e ON p.ad_id = e.ad_id
                WHERE e.value_score >= %s
                  AND e.status = 'completed'
                ORDER BY e.value_score DESC, e.evaluated_at DESC
                LIMIT %s
            """

            cursor.execute(query, (min_score, limit))
            deals = cursor.fetchall()

            cursor.close()
            conn.close()

            # Return HTML for HTMX
            if not deals:
                return """
                <div class="no-deals">
                    <h2>No deals found</h2>
                    <p>Try lowering the minimum score filter</p>
                </div>
                """

            html_parts = []
            for deal in deals:
                specs_html = ""
                if deal['specs']:
                    specs_items = []
                    for key, value in deal['specs'].items():
                        specs_items.append(f'<div class="deal-specs-item"><strong>{key}:</strong> {value}</div>')
                    specs_html = f'<div class="deal-specs">{"".join(specs_items)}</div>'

                notification_html = ""
                if deal['notification_message']:
                    notification_html = f'<div class="deal-notification">{deal["notification_message"]}</div>'

                market_value_html = ""
                if deal['estimated_market_value']:
                    market_value_html = f'''
                    <div class="deal-info">
                        <div class="deal-info-label">Market Value</div>
                        <div class="deal-info-value">{deal["estimated_market_value"]}</div>
                    </div>
                    '''

                evaluated_date = deal['evaluated_at'].strftime('%Y-%m-%d %H:%M') if deal['evaluated_at'] else 'N/A'

                card_html = f'''
                <div class="deal-card">
                    <div class="deal-header">
                        <div class="deal-score">⭐ {deal["value_score"]}/10</div>
                        <div class="deal-title">{deal["title"]}</div>
                        <div class="deal-price">{deal["price"]}</div>
                    </div>
                    <div class="deal-body">
                        {notification_html}
                        {market_value_html}
                        {specs_html}
                    </div>
                    <div class="deal-footer">
                        <span class="deal-date">Evaluated: {evaluated_date}</span>
                        <a href="https://www.blocket.se/annons/{deal["ad_id"]}" target="_blank">View on Blocket →</a>
                    </div>
                </div>
                '''
                html_parts.append(card_html)

            return "".join(html_parts)

        except Exception as e:
            return f'<div class="no-deals"><h2>Error</h2><p>{str(e)}</p></div>', 500

    @app.route('/api/search', methods=['GET'])
    def search_deals():
        """Natural language search endpoint for deals"""
        try:
            query = request.args.get('query', '').strip()

            if not query:
                return """
                <div class="no-deals">
                    <h2>No search query</h2>
                    <p>Please enter a search query above</p>
                </div>
                """

            # Extract budget/price from query (look for numbers)
            import re
            numbers = re.findall(r'\d+', query)
            max_price = None
            if numbers:
                # Take the largest number as the budget
                max_price = max([int(n) for n in numbers])

            # Extract keywords from query (remove common words)
            stop_words = {'i', 'have', 'the', 'a', 'an', 'are', 'is', 'what', 'for', 'if', 'want', 'need',
                         'looking', 'budget', 'kr', 'sek', 'best', 'good', 'deals', 'deal'}
            keywords = [word.lower() for word in re.findall(r'\b\w+\b', query)
                       if word.lower() not in stop_words and len(word) > 2]

            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Build the search query
            sql_conditions = ["e.status = 'completed'"]
            sql_params = []

            # Add price filter if budget was specified
            if max_price:
                # Extract numeric price from price string
                sql_conditions.append("CAST(regexp_replace(p.price, '[^0-9]', '', 'g') AS INTEGER) <= %s")
                sql_params.append(max_price)

            # Add text search conditions if keywords exist
            if keywords:
                keyword_conditions = []
                for keyword in keywords[:5]:  # Limit to 5 keywords
                    keyword_conditions.append(
                        "(p.title ILIKE %s OR p.description ILIKE %s OR "
                        "e.evaluation_notes ILIKE %s OR e.notification_message ILIKE %s OR "
                        "e.specs::text ILIKE %s)"
                    )
                    keyword_pattern = f'%{keyword}%'
                    sql_params.extend([keyword_pattern] * 5)

                if keyword_conditions:
                    sql_conditions.append(f"({' OR '.join(keyword_conditions)})")

            query_sql = f"""
                SELECT
                    p.ad_id,
                    p.title,
                    p.price,
                    p.description,
                    p.location,
                    p.category,
                    p.company_ad,
                    e.value_score,
                    e.evaluation_notes,
                    e.notification_message,
                    e.estimated_market_value,
                    e.specs,
                    e.evaluated_at
                FROM posts p
                INNER JOIN evaluations e ON p.ad_id = e.ad_id
                WHERE {' AND '.join(sql_conditions)}
                ORDER BY e.value_score DESC, e.evaluated_at DESC
                LIMIT 50
            """

            cursor.execute(query_sql, sql_params)
            deals = cursor.fetchall()

            cursor.close()
            conn.close()

            # Return HTML for HTMX
            if not deals:
                search_info = f"<p><strong>Search:</strong> {query}</p>"
                if max_price:
                    search_info += f"<p><strong>Budget:</strong> Up to {max_price} kr</p>"
                if keywords:
                    search_info += f"<p><strong>Keywords:</strong> {', '.join(keywords)}</p>"

                return f"""
                <div class="no-deals">
                    <h2>No deals found</h2>
                    {search_info}
                    <p>Try adjusting your search or removing some filters</p>
                </div>
                """

            html_parts = []

            # Add search summary
            search_summary = f"""
            <div style="grid-column: 1 / -1; background: white; padding: 20px; border-radius: 12px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 10px;">
                <h3 style="margin-bottom: 10px; color: #333;">Search Results ({len(deals)} found)</h3>
                <p style="color: #666; margin-bottom: 5px;"><strong>Query:</strong> {query}</p>
                {f'<p style="color: #666; margin-bottom: 5px;"><strong>Budget:</strong> Up to {max_price} kr</p>' if max_price else ''}
                {f'<p style="color: #666;"><strong>Keywords:</strong> {", ".join(keywords)}</p>' if keywords else ''}
            </div>
            """
            html_parts.append(search_summary)

            for deal in deals:
                specs_html = ""
                if deal['specs']:
                    specs_items = []
                    for key, value in deal['specs'].items():
                        specs_items.append(f'<div class="deal-specs-item"><strong>{key}:</strong> {value}</div>')
                    specs_html = f'<div class="deal-specs">{"".join(specs_items)}</div>'

                notification_html = ""
                if deal['notification_message']:
                    notification_html = f'<div class="deal-notification">{deal["notification_message"]}</div>'

                market_value_html = ""
                if deal['estimated_market_value']:
                    market_value_html = f'''
                    <div class="deal-info">
                        <div class="deal-info-label">Market Value</div>
                        <div class="deal-info-value">{deal["estimated_market_value"]}</div>
                    </div>
                    '''

                evaluated_date = deal['evaluated_at'].strftime('%Y-%m-%d %H:%M') if deal['evaluated_at'] else 'N/A'

                card_html = f'''
                <div class="deal-card">
                    <div class="deal-header">
                        <div class="deal-score">⭐ {deal["value_score"]}/10</div>
                        <div class="deal-title">{deal["title"]}</div>
                        <div class="deal-price">{deal["price"]}</div>
                    </div>
                    <div class="deal-body">
                        {notification_html}
                        {market_value_html}
                        {specs_html}
                    </div>
                    <div class="deal-footer">
                        <span class="deal-date">Evaluated: {evaluated_date}</span>
                        <a href="https://www.blocket.se/annons/{deal["ad_id"]}" target="_blank">View on Blocket →</a>
                    </div>
                </div>
                '''
                html_parts.append(card_html)

            return "".join(html_parts)

        except Exception as e:
            return f'<div class="no-deals"><h2>Search Error</h2><p>{str(e)}</p></div>', 500
