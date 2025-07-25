#!/bin/bash

# Clone Main Database to Test Database
# ====================================
# Copies all data from rally (main) to rally_test (test)

echo "🔄 Cloning main database to test database"
echo "=========================================="
echo

# Drop and recreate test database
echo "1. Recreating test database..."
dropdb -U postgres -h localhost rally_test --if-exists
createdb -U postgres -h localhost rally_test

echo "2. Dumping main database..."
pg_dump -U rossfreedman -h localhost rally > temp_rally_dump.sql

echo "3. Restoring to test database..."
psql -U postgres -h localhost -d rally_test -f temp_rally_dump.sql

echo "4. Cleaning up..."
rm temp_rally_dump.sql

echo "✅ Database cloned successfully!"
echo
echo "Now you can:"
echo "  • Test with main DB: ./start_rally_main.sh"
echo "  • Test with test DB: ./start_rally_test.sh"
echo
echo "All new ETL files are in: data/etl_new/" 