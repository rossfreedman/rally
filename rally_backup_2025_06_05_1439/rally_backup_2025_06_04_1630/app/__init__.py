from flask import Flask
from .routes.api import api

def create_app():
    app = Flask(__name__)
    
    # Register blueprints
    app.register_blueprint(api)
    
    return app 