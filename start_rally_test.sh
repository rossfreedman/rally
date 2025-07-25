#!/bin/bash

# Rally - Test Database
# =====================
# Starts Rally using the test database (rally_test)

echo "🧪 Starting Rally with TEST database"
echo "====================================="
echo

# Set environment for test database
export RALLY_DATABASE=test
export FLASK_ENV=development
export FLASK_DEBUG=True

# Check if test database exists, create if needed
echo "Checking test database..."
if ! psql -U postgres -h localhost -d rally_test -c "SELECT 1;" &> /dev/null; then
    echo "Creating test database..."
    createdb -U postgres -h localhost rally_test 2>/dev/null || echo "(Database may already exist)"
fi

echo "Database: rally_test (test)"
echo "URL: http://localhost:5000"
echo

# Start the server
python server.py 