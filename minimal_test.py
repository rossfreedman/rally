#!/usr/bin/env python3

"""
Minimal Flask app test
"""

from flask import Flask, jsonify
import os

print("🚀 Creating minimal Flask app...")

app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello, World!"

@app.route("/health")
def health():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🌐 Starting minimal app on port {port}")
    app.run(host="0.0.0.0", port=port) 