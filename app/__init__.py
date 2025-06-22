"""
Flask Application Factory
"""

from flask import Flask

from .routes.admin_routes import admin_bp
from .routes.api_routes import api_bp
from .routes.auth_routes import auth_bp
from .routes.mobile_routes import mobile_bp
from .routes.player_routes import player_bp


def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)

    # Register blueprints
    app.register_blueprint(player_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(mobile_bp)
    app.register_blueprint(api_bp)

    return app
