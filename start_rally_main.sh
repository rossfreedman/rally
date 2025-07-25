#!/bin/bash

# Rally - Main Database
# ====================
# Starts Rally using the main database (rally)

echo "🚀 Starting Rally with MAIN database"
echo "====================================="
echo

# Set environment for main database
export RALLY_DATABASE=main
export FLASK_ENV=development
export FLASK_DEBUG=True

# Check database connection
echo "Database: rally (main)"
echo "URL: http://localhost:5000"
echo

# Start the server
python server.py 