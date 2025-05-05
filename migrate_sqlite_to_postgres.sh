#!/bin/bash

# Usage: ./migrate_sqlite_to_postgres.sh <sqlite_db> <postgres_url>
# Example: ./migrate_sqlite_to_postgres.sh paddlepro.db "postgresql://USER:PASSWORD@HOST:PORT/DATABASE"

set -e

SQLITE_DB="$1"
PG_URL="$2"

if [ -z "$SQLITE_DB" ] || [ -z "$PG_URL" ]; then
  echo "Usage: $0 <sqlite_db> <postgres_url>"
  exit 1
fi

echo "Exporting all tables from $SQLITE_DB to CSV..."

# Get all table names
TABLES=$(sqlite3 "$SQLITE_DB" ".tables" | tr ' ' '\n')

# Export each table to CSV
for TABLE in $TABLES; do
  echo "Exporting $TABLE..."
  sqlite3 "$SQLITE_DB" <<EOF
.headers on
.mode csv
.output ${TABLE}.csv
SELECT * FROM $TABLE;
.output stdout
EOF
done

echo "Exported all tables to CSV."

echo "Extracting SQLite schema for manual review..."
sqlite3 "$SQLITE_DB" .schema > sqlite_schema.sql
echo "Schema saved to sqlite_schema.sql. Please review and adapt for Postgres (e.g., change AUTOINCREMENT to SERIAL, etc)."

echo "Pausing for schema review. Press Enter to continue when ready to import CSVs into Postgres."
read

echo "Importing CSVs into Postgres..."

for TABLE in $TABLES; do
  echo "Importing $TABLE..."
  # Remove any existing data (optional, comment out if not desired)
  # psql "$PG_URL" -c "TRUNCATE TABLE $TABLE RESTART IDENTITY CASCADE;"
  # Import CSV
  psql "$PG_URL" -c "\copy $TABLE FROM '$(pwd)/${TABLE}.csv' DELIMITER ',' CSV HEADER;"
done

echo "Migration complete!" 