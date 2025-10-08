#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/fix_collation.sh "$STAGING_DB_URL"
#   ./scripts/fix_collation.sh "$PROD_DB_URL"
#   ./scripts/fix_collation.sh "<full URL>" --maintenance
#
# --maintenance = faster but stronger locks (use during a short maintenance window)

DB_URL="${1:-}"
MODE="${2:-}"   # optional

if [[ -z "$DB_URL" ]]; then
  echo "Usage: $0 <DATABASE_URL> [--maintenance]"
  exit 2
fi

timestamp() { date +"%Y-%m-%d_%H-%M-%S"; }
run_sql() { psql "$DB_URL" -v ON_ERROR_STOP=1 -c "$1"; }
section() { echo; echo "== $1 =="; }

section "Environment check"
run_sql "SHOW server_version;"
run_sql "SELECT datname, datcollate, datctype, datcollversion FROM pg_database WHERE datname = current_database();"

section "Backup (pg_dump -Fc)"
BACKUP_FILE="backup_$(timestamp).dump"
pg_dump -Fc -d "$DB_URL" -f "$BACKUP_FILE"
echo "Backup written: $BACKUP_FILE"

section "ALTER DATABASE ... REFRESH COLLATION VERSION"
run_sql "ALTER DATABASE railway REFRESH COLLATION VERSION;"

if [[ "$MODE" == "--maintenance" ]]; then
  section "REINDEX DATABASE (maintenance window mode)"
  run_sql "REINDEX DATABASE railway;"
else
  section "REINDEX DATABASE CONCURRENTLY (minimal downtime)"
  if run_sql "REINDEX DATABASE CONCURRENTLY railway;"; then
    echo "Concurrent database reindex completed."
  else
    echo "DB-level concurrent reindex not supported. Falling back to per-index concurrent reindex..."
    TMPFILE="reindex_$(timestamp).sql"
    psql "$DB_URL" -At -c "
      SELECT format('REINDEX INDEX CONCURRENTLY %I.%I;', schemaname, indexname)
      FROM pg_indexes
      WHERE schemaname NOT IN ('pg_catalog','information_schema');
    " > "$TMPFILE"

    if [[ ! -s "$TMPFILE" ]]; then
      echo "No user indexes found to reindex. Proceeding."
    else
      psql "$DB_URL" -v ON_ERROR_STOP=1 -f "$TMPFILE"
      echo "Per-index concurrent reindex completed. File kept at: $TMPFILE"
    fi
  fi
fi

section "Validation"
run_sql "SELECT datname, datcollversion FROM pg_database WHERE datname = current_database();"

echo
echo "Done. Check your app logs for any remaining collation warnings on new connections."
