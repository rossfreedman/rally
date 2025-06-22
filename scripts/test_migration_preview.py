#!/usr/bin/env python3
"""
Test migration preview and small-scale test
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


def preview_migration_plan():
    """Preview what will be migrated vs preserved"""
    logger.info("🔍 MIGRATION PLAN PREVIEW")
    logger.info("=" * 60)

    with get_db() as local_conn:
        railway_conn = connect_to_railway()

        local_cursor = local_conn.cursor()
        railway_cursor = railway_conn.cursor()

        # Tables to migrate (will be replaced)
        migrate_tables = [
            "players",
            "match_scores",
            "player_history",
            "schedule",
            "series_stats",
            "player_availability",
            "user_player_associations",
        ]

        # Tables to preserve (Railway data kept)
        preserve_tables = ["users", "clubs", "series", "leagues"]

        print("\n📋 MIGRATION STRATEGY:")
        print("=" * 80)

        print(f"\n🔄 TABLES TO MIGRATE (Local → Railway):")
        print(f"{'Table':<25} {'Local':<15} {'Railway':<15} {'Action':<20}")
        print("-" * 80)

        total_to_migrate = 0
        for table in migrate_tables:
            local_cursor.execute(f"SELECT COUNT(*) FROM {table}")
            local_count = local_cursor.fetchone()[0]

            railway_cursor.execute(f"SELECT COUNT(*) FROM {table}")
            railway_count = railway_cursor.fetchone()[0]

            action = f"Replace {railway_count} with {local_count}"
            total_to_migrate += local_count

            print(f"{table:<25} {local_count:<15} {railway_count:<15} {action:<20}")

        print(f"\n🔒 TABLES TO PRESERVE (Keep Railway Data):")
        print(f"{'Table':<25} {'Local':<15} {'Railway':<15} {'Action':<20}")
        print("-" * 80)

        for table in preserve_tables:
            local_cursor.execute(f"SELECT COUNT(*) FROM {table}")
            local_count = local_cursor.fetchone()[0]

            railway_cursor.execute(f"SELECT COUNT(*) FROM {table}")
            railway_count = railway_cursor.fetchone()[0]

            action = f"Keep Railway's {railway_count}"

            print(f"{table:<25} {local_count:<15} {railway_count:<15} {action:<20}")

        print(f"\n📊 MIGRATION TOTALS:")
        print(f"  • Records to migrate: {total_to_migrate:,}")
        print(f"  • Tables to migrate: {len(migrate_tables)}")
        print(f"  • Tables to preserve: {len(preserve_tables)}")

        railway_conn.close()
        return migrate_tables, preserve_tables, total_to_migrate


def test_migration_sample():
    """Perform a small test migration with 5 records from each table"""
    logger.info("\n🧪 PERFORMING TEST MIGRATION (5 records per table)")
    logger.info("=" * 60)

    test_tables = [
        "players",
        "match_scores",
        "player_history",
        "schedule",
        "series_stats",
        "player_availability",
    ]

    with get_db() as local_conn:
        railway_conn = connect_to_railway()
        local_cursor = local_conn.cursor()
        railway_cursor = railway_conn.cursor()

        test_results = {}

        for table in test_tables:
            try:
                # Check if local has data
                local_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                local_count = local_cursor.fetchone()[0]

                if local_count == 0:
                    logger.info(f"  📭 {table}: No data in local, skipping")
                    test_results[table] = {
                        "status": "skipped",
                        "reason": "no local data",
                    }
                    continue

                # Get table structure
                local_cursor.execute(f"SELECT * FROM {table} LIMIT 1")
                columns = [desc[0] for desc in local_cursor.description]

                # Create test table name
                test_table = f"{table}_test_migration"

                # Drop test table if exists
                railway_cursor.execute(f"DROP TABLE IF EXISTS {test_table}")

                # Create test table with same structure as original
                railway_cursor.execute(
                    f"CREATE TABLE {test_table} AS SELECT * FROM {table} LIMIT 0"
                )

                # Get sample data from local (5 records)
                local_cursor.execute(
                    f"SELECT * FROM {table} ORDER BY {columns[0]} LIMIT 5"
                )
                sample_data = local_cursor.fetchall()

                if not sample_data:
                    logger.info(f"  📭 {table}: No sample data available")
                    test_results[table] = {
                        "status": "skipped",
                        "reason": "no sample data",
                    }
                    continue

                # Insert sample data into test table
                placeholders = ", ".join(["%s"] * len(columns))
                column_names = ", ".join(columns)

                insert_sql = f"""
                    INSERT INTO {test_table} ({column_names}) 
                    VALUES ({placeholders})
                """

                railway_cursor.executemany(insert_sql, sample_data)

                # Verify insertion
                railway_cursor.execute(f"SELECT COUNT(*) FROM {test_table}")
                inserted_count = railway_cursor.fetchone()[0]

                logger.info(
                    f"  ✅ {table}: Successfully migrated {inserted_count} test records"
                )
                test_results[table] = {
                    "status": "success",
                    "records": inserted_count,
                    "sample": sample_data[0][:3] if sample_data else None,
                }

            except Exception as e:
                logger.error(f"  ❌ {table}: Test failed - {e}")
                test_results[table] = {"status": "error", "error": str(e)}

        railway_conn.commit()

        # Summary of test results
        logger.info(f"\n📋 TEST MIGRATION RESULTS:")
        print("=" * 60)

        successful_tests = 0
        failed_tests = 0

        for table, result in test_results.items():
            if result["status"] == "success":
                successful_tests += 1
                print(f"  ✅ {table}: {result['records']} records migrated")
                if result["sample"]:
                    print(f"     Sample: {result['sample']}")
            elif result["status"] == "error":
                failed_tests += 1
                print(f"  ❌ {table}: {result['error']}")
            else:
                print(f"  ⚠️  {table}: {result['reason']}")

        print(f"\n📊 TEST SUMMARY:")
        print(f"  • Successful migrations: {successful_tests}")
        print(f"  • Failed migrations: {failed_tests}")
        print(f"  • Tables tested: {len(test_results)}")

        # Cleanup test tables
        logger.info(f"\n🧹 CLEANING UP TEST TABLES...")
        for table in test_tables:
            try:
                railway_cursor.execute(f"DROP TABLE IF EXISTS {table}_test_migration")
            except:
                pass

        railway_conn.commit()
        railway_conn.close()

        return successful_tests, failed_tests, test_results


def verify_current_railway_functionality():
    """Check what's currently working in Railway"""
    logger.info("\n🔍 VERIFYING CURRENT RAILWAY FUNCTIONALITY")
    logger.info("=" * 60)

    railway_conn = connect_to_railway()
    cursor = railway_conn.cursor()

    # Check key functionality
    tests = [
        ("Users exist", "SELECT COUNT(*) FROM users"),
        (
            "Leagues configured",
            "SELECT COUNT(*) FROM leagues WHERE league_id IN ('APTA_CHICAGO', 'NSTF')",
        ),
        ("Clubs available", "SELECT COUNT(*) FROM clubs"),
        ("Series configured", "SELECT COUNT(*) FROM series"),
        ("Players exist", "SELECT COUNT(*) FROM players"),
        ("Matches recorded", "SELECT COUNT(*) FROM match_scores"),
        ("Schedules exist", "SELECT COUNT(*) FROM schedule"),
    ]

    functionality_status = {}

    for test_name, sql in tests:
        try:
            cursor.execute(sql)
            count = cursor.fetchone()[0]
            status = "✅ Working" if count > 0 else "❌ Empty"
            functionality_status[test_name] = {"count": count, "status": status}
            print(f"  {status} {test_name}: {count} records")
        except Exception as e:
            functionality_status[test_name] = {"error": str(e), "status": "❌ Error"}
            print(f"  ❌ Error {test_name}: {e}")

    railway_conn.close()
    return functionality_status


def main():
    """Run comprehensive migration preview and test"""
    logger.info("🎯 RAILWAY MIGRATION PREVIEW & TEST")
    logger.info("=" * 80)

    # 1. Preview migration plan
    migrate_tables, preserve_tables, total_records = preview_migration_plan()

    # 2. Check current Railway functionality
    current_functionality = verify_current_railway_functionality()

    # 3. Perform test migration
    successful_tests, failed_tests, test_results = test_migration_sample()

    # 4. Final recommendation
    logger.info(f"\n" + "=" * 80)
    logger.info(f"🎯 MIGRATION READINESS ASSESSMENT")
    logger.info(f"=" * 80)

    if failed_tests == 0:
        logger.info(f"✅ TEST MIGRATION: ALL TESTS PASSED!")
        logger.info(f"✅ RECOMMENDATION: Safe to proceed with full migration")

        logger.info(f"\n🚀 TO PROCEED WITH FULL MIGRATION:")
        logger.info(f"   python scripts/migrate_local_to_railway.py")

        logger.info(f"\n📊 WHAT WILL HAPPEN:")
        logger.info(f"   • {total_records:,} records will be migrated")
        logger.info(f"   • Railway's existing users/clubs/series will be preserved")
        logger.info(f"   • Missing player/match/schedule data will be populated")
        logger.info(f"   • Your app will become fully functional with real tennis data")

        return True
    else:
        logger.error(f"❌ TEST MIGRATION: {failed_tests} FAILURES DETECTED")
        logger.error(f"⚠️  RECOMMENDATION: Fix issues before full migration")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
