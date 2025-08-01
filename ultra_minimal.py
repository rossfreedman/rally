#!/usr/bin/env python3

"""
Ultra-minimal Flask app for Railway testing
"""

from flask import Flask, jsonify
import os
from datetime import datetime

print("🚀 Starting ultra-minimal Flask app...")

app = Flask(__name__)

@app.route("/")
def home():
    return "Ultra-minimal Rally server is running!"

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "message": "Ultra-minimal server is running",
        "timestamp": datetime.now().isoformat()
    })

@app.route("/health-minimal")
def health_minimal():
    return jsonify({
        "status": "healthy",
        "message": "Ultra-minimal health check passed",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🌐 Starting ultra-minimal app on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False) 