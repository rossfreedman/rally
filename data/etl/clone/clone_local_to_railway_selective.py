#!/usr/bin/env python3
"""
Clone Specific Tables from Local Database to Railway using Alembic (Selective Mode)

This script creates a selective clone of specified tables from the local database
to Railway, preserving data integrity and relationships.

Usage:
    python data/etl/clone/clone_local_to_railway_selective.py

Requirements:
    - Railway database must be accessible via proxy URL
    - Local PostgreSQL server must be running
    - Alembic must be properly configured
"""

import logging
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime

# Add project root to path
sys.path.append(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
)

import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text

from database_config import get_db, parse_db_url

# =============================================================================
# CONFIGURATION: Specify which tables to clone
# =============================================================================

# Tables to clone (in dependency order to handle foreign keys)
TABLES_TO_CLONE = [
    # Core lookup tables first
    "users",
    "companies",
    "contacts",
    # Main data tables
    "activities",
    "opportunities",
    "deals",
    # Junction/relationship tables last
    "activity_contacts",
    "opportunity_contacts",
    # Add more tables as needed
    # 'table_name',
]

# Whether to truncate existing data in Railway tables before cloning
TRUNCATE_BEFORE_CLONE = True

# Whether to disable foreign key checks during the process (recommended)
DISABLE_FK_CHECKS = True

# =============================================================================

# Set up logging with absolute path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
logs_dir = os.path.join(project_root, "logs")
os.makedirs(logs_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "selective_database_clone.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Database URLs
LOCAL_DB_URL = "postgresql://postgres:postgres@localhost:5432/rally"
RAILWAY_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"


class SelectiveDatabaseCloner:
    def __init__(self, tables_to_clone=None):
        self.local_url = LOCAL_DB_URL
        self.railway_url = RAILWAY_DB_URL
        self.backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.tables_to_clone = tables_to_clone or TABLES_TO_CLONE

        if not self.tables_to_clone:
            raise ValueError(
                "No tables specified for cloning. Please configure TABLES_TO_CLONE."
            )

    def test_connections(self):
        """Test both local and Railway database connections"""
        logger.info("Testing database connections...")

        # Test local connection
        try:
            local_params = parse_db_url(self.local_url)
            conn = psycopg2.connect(**local_params)
            with conn.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                logger.info(f"✅ Local database connected: {version}")
            conn.close()
        except Exception as e:
            logger.error(f"❌ Local database connection failed: {e}")
            return False

        # Test Railway connection
        try:
            railway_params = parse_db_url(self.railway_url)
            railway_params["connect_timeout"] = 30  # Longer timeout for Railway
            conn = psycopg2.connect(**railway_params)
            with conn.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                logger.info(f"✅ Railway database connected: {version}")
            conn.close()
        except Exception as e:
            logger.error(f"❌ Railway database connection failed: {e}")
            return False

        return True

    def verify_tables_exist(self):
        """Verify that all specified tables exist in both databases"""
        logger.info(f"Verifying that tables exist: {', '.join(self.tables_to_clone)}")

        # Check local database
        local_tables = self.get_existing_tables(self.local_url)
        if not local_tables:
            logger.error("❌ Failed to get table list from local database")
            return False

        # Check Railway database
        railway_tables = self.get_existing_tables(self.railway_url)
        if not railway_tables:
            logger.error("❌ Failed to get table list from Railway database")
            return False

        missing_local = []
        missing_railway = []

        for table in self.tables_to_clone:
            if table not in local_tables:
                missing_local.append(table)
            if table not in railway_tables:
                missing_railway.append(table)

        if missing_local:
            logger.error(
                f"❌ Tables missing from local database: {', '.join(missing_local)}"
            )
        if missing_railway:
            logger.error(
                f"❌ Tables missing from Railway database: {', '.join(missing_railway)}"
            )

        return len(missing_local) == 0 and len(missing_railway) == 0

    def get_existing_tables(self, db_url):
        """Get list of existing tables in a database"""
        try:
            params = parse_db_url(db_url)
            if "railway" in db_url:
                params["connect_timeout"] = 30

            conn = psycopg2.connect(**params)

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

            conn.close()
            return tables

        except Exception as e:
            logger.error(f"Failed to get table list: {e}")
            return None

    def backup_railway_tables(self):
        """Create a backup of the specified Railway tables before overwriting"""
        backup_file = f"railway_selective_backup_{self.backup_timestamp}.sql"
        logger.info(f"Creating selective Railway backup: {backup_file}")

        try:
            # Parse Railway URL for pg_dump
            from urllib.parse import urlparse

            parsed = urlparse(self.railway_url)

            # Build table list for pg_dump
            table_args = []
            for table in self.tables_to_clone:
                table_args.extend(["-t", table])

            cmd = [
                "pg_dump",
                f"--host={parsed.hostname}",
                f"--port={parsed.port or 5432}",
                f"--username={parsed.username}",
                f"--dbname={parsed.path[1:]}",  # Remove leading /
                f"--file={backup_file}",
                "--verbose",
                "--data-only",  # Only data for selective backup
                "--no-owner",
                "--no-privileges",
                "--disable-triggers",
            ] + table_args

            # Set password in environment
            env = os.environ.copy()
            env["PGPASSWORD"] = parsed.password

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(
                    f"✅ Railway tables backed up successfully to {backup_file}"
                )
                return backup_file
            else:
                logger.error(f"❌ Railway backup failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"❌ Railway backup error: {e}")
            return None

    def dump_local_tables(self):
        """Create a dump of the specified local tables"""
        dump_file = f"local_selective_dump_{self.backup_timestamp}.sql"
        logger.info(f"Creating selective local dump: {dump_file}")

        try:
            # Build table list for pg_dump
            table_args = []
            for table in self.tables_to_clone:
                table_args.extend(["-t", table])

            cmd = [
                "pg_dump",
                "--host=localhost",
                "--port=5432",
                "--username=postgres",
                "--dbname=rally",
                "--file=" + dump_file,
                "--verbose",
                "--data-only",  # Only data since schema should already exist
                "--no-owner",
                "--no-privileges",
                "--disable-triggers",
            ] + table_args

            # Set PGPASSWORD environment variable
            env = os.environ.copy()
            env["PGPASSWORD"] = "postgres"

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"✅ Local tables dumped successfully to {dump_file}")

                # Verify dump file contains data
                try:
                    with open(dump_file, "r") as f:
                        dump_content = f.read()
                        insert_count = dump_content.count("INSERT INTO")
                        copy_count = dump_content.count("COPY ")
                        data_statements = insert_count + copy_count

                        if data_statements > 0:
                            logger.info(
                                f"✅ Dump file verification: Found {data_statements} data statements"
                            )
                        else:
                            logger.warning(
                                f"⚠️  Dump file verification: No INSERT or COPY statements found!"
                            )
                            logger.warning(f"⚠️  This might indicate empty tables")

                except Exception as e:
                    logger.warning(f"⚠️  Could not verify dump file content: {e}")

                return dump_file
            else:
                logger.error(f"❌ Local dump failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"❌ Local dump error: {e}")
            return None

    def truncate_railway_tables(self):
        """Truncate specified tables in Railway database"""
        if not TRUNCATE_BEFORE_CLONE:
            logger.info("Skipping table truncation (TRUNCATE_BEFORE_CLONE=False)")
            return True

        logger.info(f"Truncating Railway tables: {', '.join(self.tables_to_clone)}")

        try:
            railway_params = parse_db_url(self.railway_url)
            railway_params["connect_timeout"] = 30
            conn = psycopg2.connect(**railway_params)
            conn.autocommit = True

            with conn.cursor() as cursor:
                if DISABLE_FK_CHECKS:
                    # Disable foreign key checks temporarily
                    cursor.execute("SET session_replication_role = replica;")
                    logger.info("Disabled foreign key checks")

                # Truncate tables in reverse order to handle dependencies
                for table in reversed(self.tables_to_clone):
                    try:
                        cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
                        logger.info(f"✅ Truncated table: {table}")
                    except Exception as e:
                        logger.warning(f"⚠️  Failed to truncate {table}: {e}")

                if DISABLE_FK_CHECKS:
                    # Re-enable foreign key checks
                    cursor.execute("SET session_replication_role = DEFAULT;")
                    logger.info("Re-enabled foreign key checks")

            conn.close()
            return True

        except Exception as e:
            logger.error(f"❌ Failed to truncate Railway tables: {e}")
            return False

    def restore_tables_to_railway(self, dump_file):
        """Restore local table dump to Railway database"""
        logger.info(f"Restoring selective dump {dump_file} to Railway database...")

        try:
            # Parse Railway URL for psql
            from urllib.parse import urlparse

            parsed = urlparse(self.railway_url)

            cmd = [
                "psql",
                f"--host={parsed.hostname}",
                f"--port={parsed.port or 5432}",
                f"--username={parsed.username}",
                f"--dbname={parsed.path[1:]}",  # Remove leading /
                f"--file={dump_file}",
                "--echo-errors",
                "--set=ON_ERROR_STOP=off",  # Continue on errors but report them
                "--quiet",  # Reduce noise but keep errors
            ]

            env = os.environ.copy()
            env["PGPASSWORD"] = parsed.password

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            # Check if data was actually inserted
            data_copied = False
            if result.stdout:
                copy_count = result.stdout.count("COPY ")
                insert_count = result.stdout.count("INSERT ")
                data_copied = copy_count > 0 or insert_count > 0
                if data_copied:
                    logger.info(
                        f"✅ Data insertion detected: {copy_count} COPY operations, {insert_count} INSERT operations"
                    )
                else:
                    logger.warning(
                        "⚠️  No data insertion operations detected in restore output"
                    )

            constraint_errors = (
                "violates foreign key constraint" in result.stderr
                if result.stderr
                else False
            )

            if result.returncode == 0:
                logger.info("✅ Local tables restored to Railway database successfully")
                if result.stderr:
                    logger.warning(f"Restore warnings: {result.stderr}")
                return True
            elif constraint_errors and not data_copied:
                logger.error(
                    f"❌ Restore failed: Foreign key constraints but no data was copied"
                )
                logger.error(
                    f"❌ This suggests the restore process isn't working properly"
                )
                logger.error(f"❌ Stderr: {result.stderr}")
                return False
            elif data_copied and constraint_errors:
                logger.warning(
                    f"⚠️  Restore completed with foreign key constraint errors (exit code {result.returncode})"
                )
                logger.warning(
                    "⚠️  This indicates data integrity issues in the source database"
                )
                logger.warning(f"⚠️  Constraint errors: {result.stderr}")
                logger.info("✅ Data was successfully copied despite constraint issues")
                return True  # Consider this a success since data was copied
            else:
                logger.error(f"❌ Restore failed with exit code {result.returncode}")
                logger.error(f"❌ Restore stderr: {result.stderr}")
                if result.stdout:
                    logger.error(f"❌ Restore stdout: {result.stdout}")
                return False

        except Exception as e:
            logger.error(f"❌ Restore error: {e}")
            return False

    def verify_clone_success(self):
        """Verify that the selective clone was successful by comparing table counts"""
        logger.info("Verifying selective clone success...")

        try:
            # Get table counts from both databases for specified tables only
            local_counts = self.get_selective_table_counts(self.local_url)
            railway_counts = self.get_selective_table_counts(self.railway_url)

            if not local_counts or not railway_counts:
                logger.error("❌ Failed to get table counts for verification")
                return False

            # Compare counts
            all_match = True
            for table in self.tables_to_clone:
                local_count = local_counts.get(table, 0)
                railway_count = railway_counts.get(table, 0)

                if local_count == railway_count:
                    logger.info(f"✅ {table}: {local_count} rows (matches)")
                else:
                    logger.error(
                        f"❌ {table}: Local={local_count}, Railway={railway_count} (MISMATCH)"
                    )
                    all_match = False

            if all_match:
                logger.info(
                    "✅ Selective clone verification successful - all specified table counts match!"
                )
            else:
                logger.error(
                    "❌ Selective clone verification failed - table count mismatches detected"
                )

            return all_match

        except Exception as e:
            logger.error(f"❌ Verification error: {e}")
            return False

    def get_selective_table_counts(self, db_url):
        """Get row counts for specified tables in a database"""
        try:
            params = parse_db_url(db_url)
            if "railway" in db_url:
                params["connect_timeout"] = 30

            conn = psycopg2.connect(**params)
            table_counts = {}

            with conn.cursor() as cursor:
                # Get count for each specified table
                for table in self.tables_to_clone:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        table_counts[table] = count
                    except Exception as e:
                        logger.error(f"Failed to count rows in {table}: {e}")
                        table_counts[table] = -1  # Indicate error

            conn.close()
            return table_counts

        except Exception as e:
            logger.error(f"Failed to get selective table counts: {e}")
            return None

    def clone_tables(self):
        """Execute the selective table cloning process"""
        logger.info(f"🚀 Starting selective table clone process...")
        logger.info(f"📋 Tables to clone: {', '.join(self.tables_to_clone)}")

        # Step 1: Test connections
        if not self.test_connections():
            logger.error("❌ Connection tests failed. Aborting clone process.")
            return False

        # Step 2: Verify tables exist
        if not self.verify_tables_exist():
            logger.error("❌ Table verification failed. Aborting clone process.")
            return False

        # Step 3: Backup Railway tables (optional)
        backup_file = self.backup_railway_tables()
        if not backup_file:
            logger.warning(
                "⚠️  Failed to backup Railway tables. Proceeding without backup."
            )
            backup_file = None

        # Step 4: Dump local tables
        dump_file = self.dump_local_tables()
        if not dump_file:
            logger.error("❌ Failed to dump local tables. Aborting.")
            return False

        # Step 5: Truncate Railway tables
        if not self.truncate_railway_tables():
            logger.error("❌ Failed to truncate Railway tables. Aborting.")
            return False

        # Step 6: Restore local dump to Railway
        if not self.restore_tables_to_railway(dump_file):
            logger.error("❌ Failed to restore local tables to Railway. Aborting.")
            return False

        # Step 7: Verify clone success
        if not self.verify_clone_success():
            logger.error("❌ Clone verification failed. Check logs for details.")
            return False

        # Cleanup
        try:
            os.remove(dump_file)
            logger.info(f"Cleaned up temporary dump file: {dump_file}")
        except:
            pass

        logger.info("🎉 Selective table clone completed successfully!")
        if backup_file:
            logger.info(f"📁 Railway backup created: {backup_file}")
        logger.info(
            f"🔄 Railway tables now match local: {', '.join(self.tables_to_clone)}"
        )

        return True


def main():
    """Main function - runs automatically without confirmation"""
    print("Selective Table Clone Tool (Local to Railway)")
    print("=" * 60)
    print(f"📋 Tables to clone: {', '.join(TABLES_TO_CLONE)}")
    print(f"🗑️  Truncate before clone: {TRUNCATE_BEFORE_CLONE}")
    print(f"🔗 Disable FK checks: {DISABLE_FK_CHECKS}")
    print("⚠️  This will REPLACE specified Railway table data with local data!")
    print("Starting in 3 seconds...")

    import time

    time.sleep(3)

    cloner = SelectiveDatabaseCloner()

    # Execute selective clone
    success = cloner.clone_tables()

    if success:
        print(f"\n✅ Selective table clone completed successfully!")
        print(f"Railway tables now match local data: {', '.join(TABLES_TO_CLONE)}")
    else:
        print(f"\n❌ Selective table clone failed. Check logs for details.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
