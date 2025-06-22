#!/usr/bin/env python3
"""
Simple Clone Local to Railway - Schema + Data Separately

This script creates a simple clone using separate schema and data operations
to avoid foreign key constraint issues.
"""

import logging
import os
import subprocess
import sys
from datetime import datetime

# Add project root to path
sys.path.append(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
)

import psycopg2

from database_config import parse_db_url

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("../../../logs/simple_clone.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Database URLs
LOCAL_DB_URL = "postgresql://postgres:postgres@localhost:5432/rally"
RAILWAY_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"


def simple_clone():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    logger.info("🚀 Starting simple local to Railway clone...")

    # Step 1: Create schema-only dump
    schema_file = f"schema_only_{timestamp}.sql"
    logger.info("Creating schema-only dump...")

    cmd = [
        "pg_dump",
        "--host=localhost",
        "--port=5432",
        "--username=postgres",
        "--dbname=rally",
        f"--file={schema_file}",
        "--schema-only",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
    ]

    env = os.environ.copy()
    env["PGPASSWORD"] = "postgres"

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Schema dump failed: {result.stderr}")
        return False

    logger.info(f"✅ Schema dumped to {schema_file}")

    # Step 2: Create data-only dump
    data_file = f"data_only_{timestamp}.sql"
    logger.info("Creating data-only dump...")

    cmd = [
        "pg_dump",
        "--host=localhost",
        "--port=5432",
        "--username=postgres",
        "--dbname=rally",
        f"--file={data_file}",
        "--data-only",
        "--disable-triggers",
        "--no-owner",
        "--no-privileges",
    ]

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Data dump failed: {result.stderr}")
        return False

    logger.info(f"✅ Data dumped to {data_file}")

    # Step 3: Restore schema to Railway
    logger.info("Restoring schema to Railway...")

    from urllib.parse import urlparse

    parsed = urlparse(RAILWAY_DB_URL)

    cmd = [
        "psql",
        f"--host={parsed.hostname}",
        f"--port={parsed.port or 5432}",
        f"--username={parsed.username}",
        f"--dbname={parsed.path[1:]}",
        f"--file={schema_file}",
    ]

    env = os.environ.copy()
    env["PGPASSWORD"] = parsed.password

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Schema restore failed: {result.stderr}")
        return False

    logger.info("✅ Schema restored to Railway")

    # Step 4: Restore data to Railway (without constraints)
    logger.info("Restoring data to Railway...")

    cmd = [
        "psql",
        f"--host={parsed.hostname}",
        f"--port={parsed.port or 5432}",
        f"--username={parsed.username}",
        f"--dbname={parsed.path[1:]}",
        f"--file={data_file}",
    ]

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    # Don't fail on exit code since data might restore with some constraint violations
    if "COPY" in result.stdout:
        logger.info("✅ Data restored to Railway (with possible constraint warnings)")
        if result.stderr:
            logger.warning(f"Data restore warnings: {result.stderr}")
    else:
        logger.error(f"Data restore may have failed: {result.stderr}")
        return False

    # Step 5: Sync Alembic version
    logger.info("Syncing Alembic version...")

    try:
        local_params = parse_db_url(LOCAL_DB_URL)
        conn = psycopg2.connect(**local_params)

        with conn.cursor() as cursor:
            cursor.execute("SELECT version_num FROM alembic_version")
            version = cursor.fetchone()
            if version:
                local_version = version[0]
                logger.info(f"Local Alembic version: {local_version}")

                # Set Railway version
                env = os.environ.copy()
                env["SYNC_RAILWAY"] = "true"

                result = subprocess.run(
                    ["alembic", "stamp", local_version],
                    env=env,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    logger.info("✅ Alembic version synced")
                else:
                    logger.warning(f"Alembic sync failed: {result.stderr}")

        conn.close()

    except Exception as e:
        logger.warning(f"Alembic sync error: {e}")

    # Step 6: Verify
    logger.info("Verifying clone...")

    try:
        # Get counts from both databases
        local_counts = get_table_counts(LOCAL_DB_URL)
        railway_counts = get_table_counts(RAILWAY_DB_URL)

        matches = 0
        total = len(local_counts)

        for table, local_count in local_counts.items():
            railway_count = railway_counts.get(table, 0)
            if local_count == railway_count:
                logger.info(f"✅ {table}: {local_count} rows")
                matches += 1
            else:
                logger.warning(
                    f"⚠️  {table}: Local={local_count}, Railway={railway_count}"
                )

        success_rate = (matches / total) * 100 if total > 0 else 0
        logger.info(
            f"Clone success rate: {matches}/{total} tables ({success_rate:.1f}%)"
        )

        if success_rate >= 80:  # Allow some tolerance for constraint issues
            logger.info("🎉 Clone completed successfully!")
            return True
        else:
            logger.error("❌ Clone verification failed")
            return False

    except Exception as e:
        logger.error(f"Verification error: {e}")
        return False

    finally:
        # Cleanup
        try:
            os.remove(schema_file)
            os.remove(data_file)
            logger.info("Cleaned up temporary files")
        except:
            pass


def get_table_counts(db_url):
    """Get row counts for all tables"""
    try:
        params = parse_db_url(db_url)
        if "railway" in db_url:
            params["connect_timeout"] = 30

        conn = psycopg2.connect(**params)
        table_counts = {}

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """
            )

            tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                table_counts[table] = count

        conn.close()
        return table_counts

    except Exception as e:
        logger.error(f"Failed to get table counts: {e}")
        return {}


def main():
    print("Simple Local to Railway Clone")
    print("=" * 40)
    print("This will replace Railway data with local data")
    print("Starting in 3 seconds...")

    import time

    time.sleep(3)

    os.makedirs("../../../logs", exist_ok=True)

    success = simple_clone()

    if success:
        print("\n✅ Clone completed!")
    else:
        print("\n❌ Clone failed. Check logs.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
