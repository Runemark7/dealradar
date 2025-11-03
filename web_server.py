#!/usr/bin/env python
"""
DealRadar Web Server Entry Point
Flask REST API for Blocket scraper
"""
import sys
import os

# Add src to path so we can import dealradar
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dealradar.web.app import run_server

if __name__ == "__main__":
    run_server(debug=True, host='0.0.0.0', port=5001)
