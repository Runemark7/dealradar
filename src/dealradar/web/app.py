"""
Flask application factory
Creates and configures the Flask web application
"""
from flask import Flask
from flask_cors import CORS

from .routes import register_routes

def create_app():
    """
    Create and configure the Flask application

    Returns:
        Configured Flask app instance
    """
    app = Flask(__name__)
    CORS(app)

    # Register all routes
    register_routes(app)

    return app


def run_server(host='0.0.0.0', port=5000, debug=True):
    """
    Run the Flask development server

    Args:
        host: Host to bind to
        port: Port to listen on
        debug: Enable debug mode
    """
    app = create_app()
    app.run(host=host, port=port, debug=debug)
