#!/bin/bash

# Clone Main Database to Test Database
# ====================================
# Copies all data from rally (main) to rally_test (test)

echo "🔄 Cloning main database to test database"
echo "=========================================="
echo
echo "⚠️  WARNING: Test database has been decommissioned!"
echo "   This script will fail because rally_test no longer exists."
echo "   All operations now use the main database (rally)."
echo

# Check if test database exists
if psql -U postgres -h localhost -lqt | cut -d \| -f 1 | grep -qw rally_test; then
    echo "❌ Test database rally_test still exists - decommissioning failed"
    exit 1
else
    echo "✅ Test database rally_test has been decommissioned"
fi

echo
echo "📊 Available databases:"
echo "  • Main: rally (active)"
echo "  • Test: rally_test (decommissioned)"
echo
echo "🚀 Start scripts:"
echo "  • Main: ./start_rally_main.sh"
echo "  • Test: ./start_rally_test.sh (now uses main DB)"
echo
echo "⚠️  Note: Test database has been decommissioned to prevent accidental usage" 