#!/usr/bin/env python3
"""
Investigate schema mismatches between local and Railway
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


def compare_table_schemas(table_name):
    """Compare column schemas between local and Railway"""
    logger.info(f"🔍 Analyzing {table_name} schema differences...")

    with get_db() as local_conn:
        railway_conn = connect_to_railway()

        # Get local schema
        local_cursor = local_conn.cursor()
        local_cursor.execute(
            f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """
        )
        local_schema = {
            row[0]: {"type": row[1], "nullable": row[2], "default": row[3]}
            for row in local_cursor.fetchall()
        }

        # Get Railway schema
        railway_cursor = railway_conn.cursor()
        railway_cursor.execute(
            f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """
        )
        railway_schema = {
            row[0]: {"type": row[1], "nullable": row[2], "default": row[3]}
            for row in railway_cursor.fetchall()
        }

        print(f"\n📊 {table_name.upper()} SCHEMA COMPARISON:")
        print("=" * 80)
        print(f"{'Column':<25} {'Local Type':<20} {'Railway Type':<20} {'Status'}")
        print("-" * 80)

        all_columns = set(local_schema.keys()) | set(railway_schema.keys())
        mismatches = []

        for column in sorted(all_columns):
            local_info = local_schema.get(column, {})
            railway_info = railway_schema.get(column, {})

            local_type = local_info.get("type", "MISSING")
            railway_type = railway_info.get("type", "MISSING")

            if column not in local_schema:
                status = "⚠️  Railway only"
            elif column not in railway_schema:
                status = "⚠️  Local only"
            elif local_type != railway_type:
                status = "❌ TYPE MISMATCH"
                mismatches.append(
                    {
                        "column": column,
                        "local_type": local_type,
                        "railway_type": railway_type,
                    }
                )
            else:
                status = "✅ Match"

            print(f"{column:<25} {local_type:<20} {railway_type:<20} {status}")

        railway_conn.close()
        return mismatches


def check_data_samples(table_name, problematic_columns):
    """Check sample data for problematic columns"""
    logger.info(f"🔍 Checking sample data for {table_name}...")

    with get_db() as local_conn:
        cursor = local_conn.cursor()

        for column_info in problematic_columns:
            column = column_info["column"]
            logger.info(f"\n📋 Sample values for {table_name}.{column}:")

            try:
                cursor.execute(
                    f"""
                    SELECT {column}, COUNT(*) as count
                    FROM {table_name} 
                    WHERE {column} IS NOT NULL
                    GROUP BY {column}
                    ORDER BY count DESC
                    LIMIT 10
                """
                )

                results = cursor.fetchall()
                print(f"  Distinct values in {column}:")
                for value, count in results:
                    print(f"    '{value}' appears {count} times")

                # Check data type conversion possibilities
                if column_info["railway_type"] == "boolean":
                    print(
                        f"  🔧 Conversion needed: {column_info['local_type']} → boolean"
                    )
                    if isinstance(results[0][0], str):
                        print(f"    Suggestion: Map string values to boolean")
                        print(
                            f"    Example mapping: 'C' → true, '' → false, NULL → NULL"
                        )

            except Exception as e:
                print(f"    Error checking {column}: {e}")


def fix_schema_mismatches():
    """Generate fixes for schema mismatches"""
    logger.info(f"\n🔧 GENERATING SCHEMA FIXES")
    logger.info("=" * 60)

    tables_to_check = [
        "players",
        "match_scores",
        "player_history",
        "schedule",
        "series_stats",
    ]

    all_mismatches = []

    for table in tables_to_check:
        mismatches = compare_table_schemas(table)
        if mismatches:
            all_mismatches.extend([(table, mismatch) for mismatch in mismatches])
            check_data_samples(table, mismatches)

    if all_mismatches:
        print(f"\n🔧 REQUIRED FIXES:")
        print("=" * 60)

        for table, mismatch in all_mismatches:
            column = mismatch["column"]
            local_type = mismatch["local_type"]
            railway_type = mismatch["railway_type"]

            print(f"\n📋 {table}.{column}:")
            print(f"  Problem: Local has {local_type}, Railway has {railway_type}")

            # Generate fix suggestions
            if railway_type == "boolean" and local_type in [
                "character varying",
                "text",
            ]:
                print(
                    f"  Fix: Convert Railway column to TEXT or map local data to boolean"
                )
                print(f"  SQL: ALTER TABLE {table} ALTER COLUMN {column} TYPE TEXT;")
            elif local_type == "boolean" and railway_type in [
                "character varying",
                "text",
            ]:
                print(
                    f"  Fix: Convert local boolean values to strings during migration"
                )
            else:
                print(
                    f"  Fix: Manual review required for {local_type} → {railway_type}"
                )

    return all_mismatches


if __name__ == "__main__":
    logger.info("🔍 SCHEMA MISMATCH INVESTIGATION")
    logger.info("=" * 60)

    mismatches = fix_schema_mismatches()

    if mismatches:
        logger.info(f"\n❌ Found {len(mismatches)} schema mismatches that need fixing")
        logger.info(
            f"🔧 Review the suggested fixes above before proceeding with migration"
        )
    else:
        logger.info(f"\n✅ No schema mismatches found - safe to proceed with migration")

    sys.exit(1 if mismatches else 0)
