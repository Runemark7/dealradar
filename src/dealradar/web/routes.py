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
        Search listings by category with optional keyword search

        Query Parameters:
            category: Category ID (required)
            limit: Number of listings to return (default: 10)
            keywords: Search keywords to pass to Blocket API (optional)

        Returns:
            JSON response with search results
        """
        try:
            # Get query parameters
            category_id = request.args.get('category')
            limit = request.args.get('limit', default=settings.DEFAULT_SEARCH_LIMIT, type=int)
            keywords = request.args.get('keywords', '').strip()

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

            # Run async functions in sync context - pass keywords to Blocket API
            ad_ids = asyncio.run(fetch_search_results(category_id, limit, keywords if keywords else None))

            if not ad_ids:
                return jsonify({
                    "success": False,
                    "error": "No listings found for this category"
                }), 404

            # Fetch full details for all listings, passing category_id
            listings = asyncio.run(fetch_multiple_listings(ad_ids, category_id=category_id))

            return jsonify({
                "success": True,
                "data": {
                    "total_fetched": len(listings),
                    "category": category_id,
                    "requested_limit": limit,
                    "keywords": keywords if keywords else None,
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
        """Unified API endpoint to fetch and filter evaluated deals"""
        try:
            min_score = request.args.get('min_score', default=8, type=float)
            max_price = request.args.get('max_price', type=int)
            category = request.args.get('category', '').strip()
            query_text = request.args.get('query', '').strip()
            limit = request.args.get('limit', default=99999, type=int)

            # Validate inputs
            if min_score < 1 or min_score > 10:
                min_score = 8
            if limit < 1 or limit > 99999:
                limit = 99999

            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Build dynamic query with filters
            sql_conditions = ["e.status = 'completed'", "e.value_score >= %s"]
            sql_params = [min_score]

            # Add price filter if specified
            if max_price:
                sql_conditions.append("""
                    (regexp_replace(p.price, '[^0-9]', '', 'g') != '' AND
                     CAST(regexp_replace(p.price, '[^0-9]', '', 'g') AS INTEGER) <= %s)
                """)
                sql_params.append(max_price)

            # Add category filter if specified
            if category:
                sql_conditions.append("p.category = %s")
                sql_params.append(category)

            # Add text search if specified
            if query_text:
                import re
                stop_words = {'i', 'have', 'the', 'a', 'an', 'are', 'is', 'what', 'for', 'if', 'want', 'need',
                             'looking', 'budget', 'kr', 'sek', 'best', 'good', 'deals', 'deal'}
                keywords = [word.lower() for word in re.findall(r'\b\w+\b', query_text)
                           if word.lower() not in stop_words and len(word) > 2]

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

            # Query evaluated posts with all filters
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
                LIMIT %s
            """

            sql_params.append(limit)
            cursor.execute(query_sql, sql_params)
            deals = cursor.fetchall()

            cursor.close()
            conn.close()

            # Return HTML for HTMX using template
            return render_template('deals_list.html', deals=deals)

        except Exception as e:
            return render_template('deals_list.html', deals=[], error=str(e)), 500


    @app.route('/requests')
    def requests_list():
        """List all active deal requests"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Get all requests with counts
            query = """
                SELECT dr.*,
                       COUNT(DISTINCT rs.id) as subscriber_count,
                       COUNT(DISTINCT rm.id) as match_count,
                       MAX(rm.value_score) as best_match_score
                FROM deal_requests dr
                LEFT JOIN request_subscriptions rs ON dr.id = rs.request_id
                LEFT JOIN request_matches rm ON dr.id = rm.request_id
                GROUP BY dr.id
                ORDER BY
                    CASE WHEN dr.status = 'active' THEN 1
                         WHEN dr.status = 'fulfilled' THEN 2
                         WHEN dr.status = 'pending' THEN 3
                         ELSE 4 END,
                    dr.created_at DESC
            """

            cursor.execute(query)
            requests = cursor.fetchall()

            cursor.close()
            conn.close()

            return render_template('requests_list.html', requests=requests)

        except Exception as e:
            return f'<div class="no-deals"><h2>Error</h2><p>{str(e)}</p></div>', 500

    @app.route('/requests/new')
    def request_form():
        """Show form to create new request"""
        return render_template('request_form.html')

    @app.route('/requests/<int:request_id>')
    def request_detail(request_id):
        """Show details for a specific request"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Get request details
            cursor.execute("SELECT * FROM deal_requests WHERE id = %s", (request_id,))
            request = cursor.fetchone()

            if not request:
                cursor.close()
                conn.close()
                return "Request not found", 404

            # Get subscriptions
            cursor.execute("SELECT * FROM request_subscriptions WHERE request_id = %s", (request_id,))
            subscriptions = cursor.fetchall()

            # Get matches with full post details
            cursor.execute("""
                SELECT p.*, e.value_score, e.evaluation_notes, e.notification_message,
                       e.estimated_market_value, e.specs, e.evaluated_at, rm.matched_at
                FROM request_matches rm
                INNER JOIN posts p ON rm.ad_id = p.ad_id
                LEFT JOIN evaluations e ON p.ad_id = e.ad_id
                WHERE rm.request_id = %s
                ORDER BY rm.value_score DESC, rm.matched_at DESC
            """, (request_id,))
            matches = cursor.fetchall()

            cursor.close()
            conn.close()

            return render_template(
                'request_detail.html',
                request=request,
                subscriptions=subscriptions,
                matches=matches
            )

        except Exception as e:
            return f'<div class="no-deals"><h2>Error</h2><p>{str(e)}</p></div>', 500

    @app.route('/api/requests', methods=['POST'])
    def create_request():
        """API endpoint to create a new deal request"""
        try:
            title = request.form.get('title', '').strip()
            category = request.form.get('category', '').strip()
            max_budget = request.form.get('max_budget', '').strip()
            requirements = request.form.get('requirements', '').strip()
            email = request.form.get('email', '').strip()

            # Validation
            if not title or not category or not requirements or not email:
                return "Missing required fields", 400

            if len(title) > 200:
                return "Title too long (max 200 characters)", 400

            # Validate email format (basic)
            import re
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                return "Invalid email format", 400

            # Parse budget
            budget_int = None
            if max_budget:
                try:
                    budget_int = int(max_budget)
                    if budget_int < 0:
                        return "Budget must be positive", 400
                except ValueError:
                    return "Invalid budget format", 400

            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Insert request using parameterized query
            cursor.execute("""
                INSERT INTO deal_requests
                (title, description, category, max_budget, requirements, status)
                VALUES (%s, %s, %s, %s, %s, 'pending')
                RETURNING id
            """, (title, requirements, category, budget_int, requirements))

            request_id = cursor.fetchone()['id']

            # Add creator as first subscriber using parameterized query
            cursor.execute("""
                INSERT INTO request_subscriptions (request_id, email)
                VALUES (%s, %s)
            """, (request_id, email))

            conn.commit()
            cursor.close()
            conn.close()

            return "Success", 200

        except Exception as e:
            return f"Error: {str(e)}", 500

    @app.route('/api/requests/<int:request_id>/subscribe', methods=['POST'])
    def subscribe_to_request(request_id):
        """API endpoint to subscribe to a request"""
        try:
            email = request.form.get('email', '').strip()

            # Validation
            if not email:
                return "Email is required", 400

            # Validate email format
            import re
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                return "Invalid email format", 400

            conn = get_db_connection()
            cursor = conn.cursor()

            # Check if request exists
            cursor.execute("SELECT id FROM deal_requests WHERE id = %s", (request_id,))
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return "Request not found", 404

            # Insert subscription using parameterized query (will fail if duplicate due to UNIQUE constraint)
            try:
                cursor.execute("""
                    INSERT INTO request_subscriptions (request_id, email)
                    VALUES (%s, %s)
                """, (request_id, email))
                conn.commit()
            except psycopg2.IntegrityError:
                conn.rollback()
                cursor.close()
                conn.close()
                return "Already subscribed", 400

            cursor.close()
            conn.close()

            return "Success", 200

        except Exception as e:
            return f"Error: {str(e)}", 500
