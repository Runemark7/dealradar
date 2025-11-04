"""
Flask API routes
Defines all HTTP endpoints for the web service
"""
import asyncio
from flask import jsonify, request, render_template
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
        return render_template('index.html')

    @app.route('/api/deals', methods=['GET'])
    def get_deals():
        """API endpoint to fetch evaluated deals"""
        try:
            min_score = request.args.get('min_score', default=8, type=float)
            limit = request.args.get('limit', default=99999, type=int)

            # Validate inputs
            if min_score < 1 or min_score > 10:
                min_score = 8
            if limit < 1 or limit > 99999:
                limit = 99999

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

            # Return HTML for HTMX using template
            return render_template('deals_list.html', deals=deals)

        except Exception as e:
            return render_template('deals_list.html', deals=[], error=str(e)), 500

    @app.route('/api/deals/search', methods=['GET'])
    def search_deals():
        """Natural language search endpoint for deals"""
        try:
            query = request.args.get('query', '').strip()

            if not query:
                return render_template(
                    'search_results.html',
                    deals=[],
                    query='',
                    max_price=None,
                    keywords=[]
                )

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
                # Extract numeric price from price string, handle empty strings
                sql_conditions.append("""
                    (regexp_replace(p.price, '[^0-9]', '', 'g') != '' AND
                     CAST(regexp_replace(p.price, '[^0-9]', '', 'g') AS INTEGER) <= %s)
                """)
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

            # Return HTML for HTMX using template
            return render_template(
                'search_results.html',
                deals=deals,
                query=query,
                max_price=max_price,
                keywords=keywords
            )

        except Exception as e:
            return render_template(
                'search_results.html',
                deals=[],
                query=query if 'query' in locals() else '',
                max_price=None,
                keywords=[],
                error=str(e)
            ), 500
