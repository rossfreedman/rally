#!/usr/bin/env python3

"""
Production-ready Rally server for Railway deployment
Uses direct Python execution instead of gunicorn for Railway compatibility
"""

import os
import sys
import traceback
from datetime import datetime

# Add startup debugging
print("🚀 Starting Rally production server...")

try:
    from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
    from flask_cors import CORS
    from flask_socketio import SocketIO
    from flask_login import LoginManager, login_user, logout_user, login_required, current_user
    from flask_sqlalchemy import SQLAlchemy
    import logging
    
    print("✅ All Flask imports successful")
    
except Exception as e:
    print(f"❌ Import error: {e}")
    traceback.print_exc()
    sys.exit(1)

# Import our modules
try:
    from database_config import get_db_engine, test_db_connection
    from utils.ai import get_openai_client
    print("✅ Database and AI imports successful")
except Exception as e:
    print(f"❌ Module import error: {e}")
    traceback.print_exc()
    sys.exit(1)

# Create Flask app
try:
    app = Flask(__name__)
    print("✅ Flask app created successfully")
except Exception as e:
    print(f"❌ Flask app creation error: {e}")
    traceback.print_exc()
    sys.exit(1)

# Configure app
try:
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://localhost/rally')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db = SQLAlchemy(app)
    socketio = SocketIO(app, cors_allowed_origins="*")
    CORS(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    print("✅ App configuration and extensions initialized")
except Exception as e:
    print(f"❌ App configuration error: {e}")
    traceback.print_exc()
    sys.exit(1)

# Health endpoints
@app.route("/health")
def health():
    """Health check with database connectivity test"""
    try:
        # Test database connection
        test_db_connection()
        return jsonify({
            "status": "healthy",
            "message": "Rally server is running with database connectivity",
            "timestamp": datetime.now().isoformat(),
            "database": "connected"
        })
    except Exception as e:
        return jsonify({
            "status": "degraded",
            "message": f"Rally server is running but database connection failed: {str(e)}",
            "timestamp": datetime.now().isoformat(),
            "database": "disconnected"
        }), 200

@app.route("/health-minimal")
def health_minimal():
    """Minimal health check with no dependencies"""
    return jsonify({
        "status": "healthy",
        "message": "Minimal health check passed",
        "timestamp": datetime.now().isoformat()
    })

@app.route("/")
def home():
    """Home page"""
    return "Rally server is running! 🎾"

@app.route("/basic-test")
def basic_test():
    """Basic test endpoint"""
    return "Rally app is running!"

if __name__ == "__main__":
    try:
        port = int(os.environ.get("PORT", 8080))
        print(f"🌐 Starting production server on port {port}")
        print(f"🔗 Health check URL: http://localhost:{port}/health-minimal")
        
        # Start the server
        app.run(
            host="0.0.0.0", 
            port=port, 
            debug=False,
            threaded=True
        )
    except Exception as e:
        print(f"❌ Server startup error: {e}")
        traceback.print_exc()
        sys.exit(1) 