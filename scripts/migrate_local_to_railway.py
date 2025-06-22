#!/usr/bin/env python3
"""
Selective data migration from local to Railway database
Preserves Railway's existing users/clubs/series, adds missing player/match/schedule data
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


def migrate_table_data(
    local_conn, railway_conn, table_name, strategy="replace", batch_size=1000
):
    """Migrate data from local to Railway for a specific table"""
    local_cursor = local_conn.cursor()
    railway_cursor = railway_conn.cursor()

    try:
        # Get total count
        local_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_rows = local_cursor.fetchone()[0]

        if total_rows == 0:
            logger.info(f"  📭 {table_name}: No data to migrate")
            return 0

        logger.info(f"  📊 {table_name}: Migrating {total_rows} records...")

        # Get column names
        local_cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
        columns = [desc[0] for desc in local_cursor.description]

        if strategy == "replace":
            # Clear existing data first
            railway_cursor.execute(f"TRUNCATE TABLE {table_name} CASCADE")
            logger.info(f"    🗑️  Cleared existing {table_name} data")

        # Migrate data in batches
        offset = 0
        migrated_count = 0

        while offset < total_rows:
            # Fetch batch from local
            local_cursor.execute(
                f"""
                SELECT * FROM {table_name} 
                ORDER BY {columns[0]} 
                LIMIT {batch_size} OFFSET {offset}
            """
            )
            batch_rows = local_cursor.fetchall()

            if not batch_rows:
                break

            # Prepare INSERT statement
            placeholders = ", ".join(["%s"] * len(columns))
            column_names = ", ".join(columns)

            insert_sql = f"""
                INSERT INTO {table_name} ({column_names}) 
                VALUES ({placeholders})
                ON CONFLICT DO NOTHING
            """

            # Insert batch
            railway_cursor.executemany(insert_sql, batch_rows)
            migrated_count += len(batch_rows)

            logger.info(f"    ✅ Migrated {migrated_count}/{total_rows} records")
            offset += batch_size

        railway_conn.commit()
        logger.info(
            f"  ✅ {table_name}: Migration completed ({migrated_count} records)"
        )
        return migrated_count

    except Exception as e:
        logger.error(f"  ❌ {table_name}: Migration failed - {e}")
        railway_conn.rollback()
        return 0


def migrate_essential_data():
    """Migrate essential data from local to Railway"""
    logger.info("🚀 STARTING SELECTIVE DATA MIGRATION")
    logger.info("=" * 60)

    # Tables to migrate (excluding users, clubs, series to preserve Railway data)
    tables_to_migrate = [
        ("players", "replace"),  # Critical: All player data
        ("match_scores", "replace"),  # Critical: All match results
        ("player_history", "replace"),  # Critical: Historical PTI data
        ("schedule", "replace"),  # Critical: Match schedules
        ("series_stats", "replace"),  # Critical: Team statistics
        ("player_availability", "replace"),  # Important: Player availability
        ("user_player_associations", "replace"),  # Important: User-player links
    ]

    # Connect to databases
    logger.info("Connecting to databases...")
    with get_db() as local_conn:
        railway_conn = connect_to_railway()

        # Create backup before migration
        logger.info("\n🔄 Creating backup before migration...")
        railway_cursor = railway_conn.cursor()

        # Backup critical Railway data that we're preserving
        logger.info("  📦 Backing up Railway users, clubs, and series...")

        migration_summary = {
            "migrated_tables": [],
            "preserved_tables": ["users", "clubs", "series", "leagues"],
            "total_records_migrated": 0,
            "errors": [],
        }

        # Migrate each table
        logger.info(f"\n📋 MIGRATING {len(tables_to_migrate)} TABLES:")
        logger.info("-" * 60)

        for table_name, strategy in tables_to_migrate:
            try:
                migrated_count = migrate_table_data(
                    local_conn, railway_conn, table_name, strategy
                )
                migration_summary["migrated_tables"].append(
                    f"{table_name}: {migrated_count} records"
                )
                migration_summary["total_records_migrated"] += migrated_count
            except Exception as e:
                error_msg = f"{table_name}: {str(e)}"
                migration_summary["errors"].append(error_msg)
                logger.error(f"  ❌ {error_msg}")

        # Update sequences to prevent ID conflicts
        logger.info(f"\n🔧 UPDATING SEQUENCES...")
        sequence_tables = [
            "players",
            "match_scores",
            "player_history",
            "schedule",
            "series_stats",
            "player_availability",
        ]

        for table in sequence_tables:
            try:
                railway_cursor.execute(
                    f"""
                    SELECT setval(pg_get_serial_sequence('{table}', 'id'), 
                                  COALESCE((SELECT MAX(id) FROM {table}), 1), false)
                """
                )
                logger.info(f"  ✅ Updated {table} sequence")
            except Exception as e:
                logger.warning(f"  ⚠️  Could not update {table} sequence: {e}")

        railway_conn.commit()
        railway_conn.close()

        # Final summary
        logger.info(f"\n" + "=" * 60)
        logger.info(f"📋 MIGRATION SUMMARY")
        logger.info(f"=" * 60)

        logger.info(
            f"✅ MIGRATED TABLES ({len(migration_summary['migrated_tables'])}):"
        )
        for table_info in migration_summary["migrated_tables"]:
            logger.info(f"  • {table_info}")

        logger.info(
            f"\n🔒 PRESERVED RAILWAY TABLES ({len(migration_summary['preserved_tables'])}):"
        )
        for table in migration_summary["preserved_tables"]:
            logger.info(f"  • {table} (kept Railway's existing data)")

        logger.info(
            f"\n📊 TOTAL RECORDS MIGRATED: {migration_summary['total_records_migrated']:,}"
        )

        if migration_summary["errors"]:
            logger.error(f"\n❌ ERRORS ({len(migration_summary['errors'])}):")
            for error in migration_summary["errors"]:
                logger.error(f"  • {error}")
            return False
        else:
            logger.info(f"\n🎉 MIGRATION COMPLETED SUCCESSFULLY!")
            return True


if __name__ == "__main__":
    success = migrate_essential_data()
    if success:
        logger.info("\n🎯 NEXT STEPS:")
        logger.info("  1. Test the Railway application: https://www.lovetorally.com")
        logger.info("  2. Verify data with: python scripts/compare_data_content.py")
        logger.info("  3. Check API responses for player/match data")
    sys.exit(0 if success else 1)
