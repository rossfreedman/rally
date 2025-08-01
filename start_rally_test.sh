#!/bin/bash

# Start Rally with test database
export RALLY_DATABASE=test
echo "🧪 Starting Rally with TEST database (rally_test)"
echo "📊 Database: rally_test"
echo "🌐 URL: http://localhost:5000"
echo ""

python server.py 