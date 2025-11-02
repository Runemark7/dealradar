"""
Blocket API interaction module
"""

from .scraper import fetch_blocket_api, fetch_search_results, fetch_multiple_listings, fetch_recent_search_results

__all__ = ['fetch_blocket_api', 'fetch_search_results', 'fetch_multiple_listings', 'fetch_recent_search_results']
