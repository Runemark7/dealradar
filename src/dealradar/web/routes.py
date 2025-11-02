"""
Flask API routes
Defines all HTTP endpoints for the web service
"""
import asyncio
from flask import jsonify, request

from ..api import fetch_blocket_api, fetch_search_results, fetch_multiple_listings, fetch_recent_search_results
from ..config import settings


def register_routes(app):
    """Register all routes with the Flask app"""

    @app.route('/')
    def index():
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
