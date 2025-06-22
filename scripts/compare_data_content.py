#!/usr/bin/env python3
"""
Compare data content between local and Railway databases
"""

import logging
import os
import sys
from urllib.parse import urlparse

import psycopg2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

RAILWAY_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"


def connect_to_railway():
    """Connect to Railway database"""
    parsed = urlparse(RAILWAY_URL)
    conn_params = {
        "dbname": parsed.path[1:],
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "sslmode": "require",
        "connect_timeout": 10,
    }
    return psycopg2.connect(**conn_params)


def get_table_counts(conn, label):
    """Get row counts for all tables"""
    cursor = conn.cursor()

    tables = [
        "users",
        "leagues",
        "clubs",
        "players",
        "series",
        "series_stats",
        "match_scores",
        "player_availability",
        "schedule",
        "player_history",
        "user_player_associations",
        "user_instructions",
        "user_activity_logs",
    ]

    counts = {}
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]
        except Exception as e:
            counts[table] = f"ERROR: {e}"

    return counts


def get_sample_data(conn, table, limit=5):
    """Get sample data from a table"""
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT * FROM {table} LIMIT {limit}")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return columns, rows
    except Exception as e:
        return None, f"ERROR: {e}"


def compare_databases():
    """Compare data content between local and Railway"""
    logger.info("📊 COMPARING DATABASE CONTENT")
    logger.info("=" * 60)

    # Connect to both databases
    logger.info("Connecting to local database...")
    with get_db() as local_conn:
        local_counts = get_table_counts(local_conn, "LOCAL")

    logger.info("Connecting to Railway database...")
    railway_conn = connect_to_railway()
    railway_counts = get_table_counts(railway_conn, "RAILWAY")

    # Compare counts
    print("\n" + "=" * 80)
    print("📊 DATA CONTENT COMPARISON")
    print("=" * 80)
    print(f"{'Table':<25} {'Local':<15} {'Railway':<15} {'Status':<20}")
    print("-" * 80)

    data_sync_needed = False
    critical_differences = []

    for table in sorted(local_counts.keys()):
        local_count = local_counts.get(table, 0)
        railway_count = railway_counts.get(table, 0)

        if isinstance(local_count, str) or isinstance(railway_count, str):
            status = "ERROR"
        elif local_count == railway_count:
            status = "✅ MATCH"
        elif railway_count == 0 and local_count > 0:
            status = "❌ RAILWAY EMPTY"
            data_sync_needed = True
            if table in ["leagues", "clubs", "players", "series"]:
                critical_differences.append(
                    f"{table}: Local has {local_count}, Railway has 0"
                )
        elif local_count == 0 and railway_count > 0:
            status = "⚠️  LOCAL EMPTY"
        else:
            status = "⚠️  DIFFERENT"
            if abs(local_count - railway_count) > local_count * 0.1:  # >10% difference
                data_sync_needed = True
                critical_differences.append(
                    f"{table}: Local has {local_count}, Railway has {railway_count}"
                )

        print(
            f"{table:<25} {str(local_count):<15} {str(railway_count):<15} {status:<20}"
        )

    # Check sample data for key tables
    print("\n" + "=" * 80)
    print("🔍 SAMPLE DATA ANALYSIS")
    print("=" * 80)

    key_tables = ["leagues", "clubs", "players"]

    with get_db() as local_conn:
        for table in key_tables:
            if local_counts.get(table, 0) > 0:
                print(f"\n📋 {table.upper()} - Sample Data:")

                # Local sample
                local_cols, local_rows = get_sample_data(local_conn, table, 3)
                print(f"  LOCAL: {len(local_rows) if local_rows else 0} sample records")
                if local_rows and len(local_rows) > 0:
                    print(
                        f"    First record: {dict(zip(local_cols[:3], local_rows[0][:3]))}"
                    )

                # Railway sample
                railway_cols, railway_rows = get_sample_data(railway_conn, table, 3)
                print(
                    f"  RAILWAY: {len(railway_rows) if railway_rows else 0} sample records"
                )
                if railway_rows and len(railway_rows) > 0:
                    print(
                        f"    First record: {dict(zip(railway_cols[:3], railway_rows[0][:3]))}"
                    )
                elif railway_counts.get(table, 0) == 0:
                    print(f"    ❌ Table is empty!")

    railway_conn.close()

    # Summary and recommendations
    print("\n" + "=" * 80)
    print("📋 DATA SYNC ANALYSIS")
    print("=" * 80)

    if critical_differences:
        print(f"❌ CRITICAL DATA DIFFERENCES FOUND ({len(critical_differences)}):")
        for diff in critical_differences:
            print(f"  • {diff}")
        print(f"\n🚨 RECOMMENDATION: Data migration needed!")
        print(f"   Railway appears to be missing critical application data.")

    elif data_sync_needed:
        print(f"⚠️  MINOR DATA DIFFERENCES DETECTED")
        print(f"   Some tables have different counts but core data exists.")

    else:
        print(f"✅ DATA IS SYNCHRONIZED!")
        print(f"   Both databases have matching data content.")

    # Migration recommendations
    if data_sync_needed or critical_differences:
        print(f"\n🔧 MIGRATION OPTIONS:")
        print(f"  1. Full sync: Migrate all data from local to Railway")
        print(f"  2. Selective sync: Migrate only missing/critical tables")
        print(
            f"  3. Reverse sync: Migrate from Railway to local (if Railway has newer data)"
        )

        print(f"\n💡 COMMANDS TO RUN:")
        print(f"  # Create data migration script:")
        print(f"  python scripts/create_data_migration.py")
        print(f"  ")
        print(f"  # Or use ETL commands to populate Railway:")
        print(f"  python scripts/migrate_local_to_railway.py")

    return data_sync_needed, critical_differences


if __name__ == "__main__":
    needs_sync, critical_diffs = compare_databases()
    sys.exit(1 if critical_diffs else 0)
