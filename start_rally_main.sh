#!/bin/bash

# Start Rally with main database
export RALLY_DATABASE=main
echo "🚀 Starting Rally with MAIN database (rally)"
echo "📊 Database: rally"
echo "🌐 URL: http://localhost:5000"
echo ""

python server.py 