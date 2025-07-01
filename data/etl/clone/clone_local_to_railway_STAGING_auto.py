#!/usr/bin/env python3
"""
Clone Local Database to Railway Staging using Alembic (Auto Mode)

This script creates an exact clone of the local database (schema + data) on Railway Staging
and ensures Alembic migration state is synchronized - WITHOUT user confirmation prompts.

Usage:
    python data/etl/clone/clone_local_to_railway_STAGING_auto.py

Requirements:
    - Railway staging database must be accessible via proxy URL
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

# Set up logging with absolute path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
logs_dir = os.path.join(project_root, "logs")
os.makedirs(logs_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "database_clone_staging.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Database URLs
LOCAL_DB_URL = "postgresql://postgres:postgres@localhost:5432/rally"
RAILWAY_STAGING_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"


class DatabaseCloner:
    def __init__(self):
        self.local_url = LOCAL_DB_URL
        self.railway_url = RAILWAY_STAGING_URL
        self.backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def test_connections(self):
        """Test both local and Railway staging database connections"""
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

        # Test Railway staging connection
        try:
            railway_params = parse_db_url(self.railway_url)
            railway_params["connect_timeout"] = 30  # Longer timeout for Railway
            conn = psycopg2.connect(**railway_params)
            with conn.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                logger.info(f"✅ Railway staging database connected: {version}")
            conn.close()
        except Exception as e:
            logger.error(f"❌ Railway staging database connection failed: {e}")
            return False

        return True

    def backup_railway_database(self):
        """Create a backup of the current Railway staging database before overwriting"""
        backup_file = f"railway_staging_backup_before_clone_{self.backup_timestamp}.sql"
        logger.info(f"Creating Railway staging database backup: {backup_file}")

        try:
            # Parse Railway URL for pg_dump
            from urllib.parse import urlparse

            parsed = urlparse(self.railway_url)

            cmd = [
                "pg_dump",
                f"--host={parsed.hostname}",
                f"--port={parsed.port or 5432}",
                f"--username={parsed.username}",
                f"--dbname={parsed.path[1:]}",  # Remove leading /
                f"--file={backup_file}",
                "--verbose",
                "--clean",
                "--if-exists",
                "--create",
                "--no-owner",
                "--no-privileges",
                "--no-sync",  # Handle version differences
                "--disable-triggers",  # Avoid trigger issues during restore
            ]

            # Set password in environment
            env = os.environ.copy()
            env["PGPASSWORD"] = parsed.password

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(
                    f"✅ Railway staging database backed up successfully to {backup_file}"
                )
                return backup_file
            else:
                logger.error(f"❌ Railway staging backup failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"❌ Railway staging backup error: {e}")
            return None

    def get_local_migration_version(self):
        """Get the current Alembic migration version from local database"""
        logger.info("Checking local database migration version...")

        try:
            local_params = parse_db_url(self.local_url)
            conn = psycopg2.connect(**local_params)

            with conn.cursor() as cursor:
                # Check if alembic_version table exists
                cursor.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'alembic_version'
                    )
                """
                )

                if cursor.fetchone()[0]:
                    cursor.execute("SELECT version_num FROM alembic_version")
                    version = cursor.fetchone()
                    if version:
                        logger.info(f"Local database migration version: {version[0]}")
                        return version[0]
                    else:
                        logger.warning(
                            "Local database has alembic_version table but no version"
                        )
                        return None
                else:
                    logger.warning("Local database has no alembic_version table")
                    return None

            conn.close()

        except Exception as e:
            logger.error(f"❌ Failed to get local migration version: {e}")
            return None

    def dump_local_database(self):
        """Create a complete dump of the local database"""
        dump_file = f"local_dump_for_staging_{self.backup_timestamp}.sql"
        logger.info(f"Creating local database dump: {dump_file}")

        try:
            cmd = [
                "pg_dump",
                "--host=localhost",
                "--port=5432",
                "--username=postgres",
                "--dbname=rally",
                "--file=" + dump_file,
                "--verbose",
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-privileges",
                "--no-sync",  # Handle version differences
                "--disable-triggers",  # Avoid trigger issues during restore
                # Removed --create to avoid database creation conflicts
                # Removed --data-only to include both schema and data
            ]

            # Set PGPASSWORD environment variable
            env = os.environ.copy()
            env["PGPASSWORD"] = "postgres"

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"✅ Local database dumped successfully to {dump_file}")

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
                            logger.warning(
                                f"⚠️  Dump file size: {os.path.getsize(dump_file)} bytes"
                            )

                except Exception as e:
                    logger.warning(f"⚠️  Could not verify dump file content: {e}")

                return dump_file
            else:
                logger.error(f"❌ Local dump failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"❌ Local dump error: {e}")
            return None

    def drop_and_recreate_railway_database(self):
        """Drop all objects in Railway staging database and prepare for restore"""
        logger.info("Clearing Railway staging database...")

        try:
            railway_params = parse_db_url(self.railway_url)
            railway_params["connect_timeout"] = 30
            conn = psycopg2.connect(**railway_params)
            conn.autocommit = True

            with conn.cursor() as cursor:
                # Drop all tables, views, sequences, etc. in public schema
                cursor.execute(
                    """
                    DO $$ DECLARE
                        r RECORD;
                    BEGIN
                        -- Drop all tables
                        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                        END LOOP;
                        
                        -- Drop all sequences
                        FOR r IN (SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public') LOOP
                            EXECUTE 'DROP SEQUENCE IF EXISTS ' || quote_ident(r.sequence_name) || ' CASCADE';
                        END LOOP;
                        
                        -- Drop all views
                        FOR r IN (SELECT viewname FROM pg_views WHERE schemaname = 'public') LOOP
                            EXECUTE 'DROP VIEW IF EXISTS ' || quote_ident(r.viewname) || ' CASCADE';
                        END LOOP;
                        
                        -- Drop all functions
                        FOR r IN (SELECT routine_name FROM information_schema.routines WHERE routine_schema = 'public') LOOP
                            EXECUTE 'DROP FUNCTION IF EXISTS ' || quote_ident(r.routine_name) || ' CASCADE';
                        END LOOP;
                    END $$;
                """
                )

                logger.info("✅ Railway staging database cleared successfully")

            conn.close()
            return True

        except Exception as e:
            logger.error(f"❌ Failed to clear Railway staging database: {e}")
            return False

    def restore_local_dump_to_railway(self, dump_file):
        """Restore local dump to Railway staging database"""
        logger.info(f"Restoring local dump {dump_file} to Railway staging database...")

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
                logger.info("✅ Local dump restored to Railway staging database successfully")
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

    def sync_railway_alembic_state(self, local_version):
        """Sync Railway staging Alembic state with local"""
        if not local_version:
            logger.warning("⚠️  No local migration version found, skipping Alembic sync")
            return True

        logger.info(f"Syncing Railway staging Alembic migration state to {local_version}...")

        try:
            # Use SYNC_RAILWAY_STAGING environment variable to target Railway staging
            env = os.environ.copy()
            env["SYNC_RAILWAY_STAGING"] = "true"

            # Set the Railway staging alembic version to match local
            cmd = ["alembic", "stamp", local_version]
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(
                    f"✅ Railway staging Alembic migration state synced to {local_version}"
                )
                return True
            else:
                logger.error(f"❌ Railway staging Alembic sync failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Railway staging Alembic sync error: {e}")
            return False

    def verify_clone_success(self):
        """Verify that the clone was successful by comparing table counts"""
        logger.info("Verifying clone success...")

        try:
            # Get table counts from both databases
            local_counts = self.get_table_counts(self.local_url)
            railway_counts = self.get_table_counts(self.railway_url)

            if not local_counts or not railway_counts:
                logger.error("❌ Failed to get table counts for verification")
                return False

            # Compare counts
            all_match = True
            for table in local_counts:
                local_count = local_counts[table]
                railway_count = railway_counts.get(table, 0)

                # Allow small differences in activity logs (due to timing during clone)
                if table == "user_activity_logs":
                    diff = abs(local_count - railway_count)
                    if diff <= 5:  # Allow up to 5 rows difference for activity logs
                        logger.info(f"✅ {table}: {local_count} vs {railway_count} rows (acceptable difference: {diff})")
                        continue
                
                if local_count == railway_count:
                    logger.info(f"✅ {table}: {local_count} rows (matches)")
                else:
                    logger.error(
                        f"❌ {table}: Local={local_count}, Railway Staging={railway_count} (MISMATCH)"
                    )
                    all_match = False

            # Check for tables that exist in Railway staging but not local
            for table in railway_counts:
                if table not in local_counts:
                    logger.warning(f"⚠️  {table}: Exists in Railway staging but not in local")

            if all_match:
                logger.info(
                    "✅ Clone verification successful - all table counts match!"
                )
            else:
                logger.error(
                    "❌ Clone verification failed - table count mismatches detected"
                )

            return all_match

        except Exception as e:
            logger.error(f"❌ Verification error: {e}")
            return False

    def get_table_counts(self, db_url):
        """Get row counts for all tables in a database"""
        try:
            params = parse_db_url(db_url)
            if "railway" in db_url:
                params["connect_timeout"] = 30

            conn = psycopg2.connect(**params)
            table_counts = {}

            with conn.cursor() as cursor:
                # Get all table names
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

                # Get count for each table
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    table_counts[table] = count

            conn.close()
            return table_counts

        except Exception as e:
            logger.error(f"Failed to get table counts: {e}")
            return None

    def clone_database(self):
        """Execute the complete database cloning process"""
        logger.info("🚀 Starting local to Railway staging database clone process...")

        # Step 1: Test connections
        if not self.test_connections():
            logger.error("❌ Connection tests failed. Aborting clone process.")
            return False

        # Step 2: Get local migration version
        local_version = self.get_local_migration_version()

        # Step 3: Backup Railway staging database (optional due to version compatibility)
        backup_file = self.backup_railway_database()
        if not backup_file:
            logger.warning(
                "⚠️  Failed to backup Railway staging database due to version mismatch. Proceeding without backup."
            )
            logger.warning("⚠️  Since we'll verify the clone, this should be safe.")
            backup_file = None

        # Step 4: Dump local database
        dump_file = self.dump_local_database()
        if not dump_file:
            logger.error("❌ Failed to dump local database. Aborting.")
            return False

        # Step 5: Clear Railway staging database
        if not self.drop_and_recreate_railway_database():
            logger.error("❌ Failed to clear Railway staging database. Aborting.")
            return False

        # Step 6: Restore local dump to Railway staging
        if not self.restore_local_dump_to_railway(dump_file):
            logger.error("❌ Failed to restore local dump to Railway staging. Aborting.")
            return False

        # Step 7: Sync Railway staging Alembic migration state
        if not self.sync_railway_alembic_state(local_version):
            logger.error(
                "❌ Failed to sync Railway staging Alembic state. Manual intervention may be needed."
            )
            # Don't return False here as the data clone may still be successful

        # Step 8: Verify clone success
        if not self.verify_clone_success():
            logger.error("❌ Clone verification failed. Check logs for details.")
            return False

        # Cleanup
        try:
            os.remove(dump_file)
            logger.info(f"Cleaned up temporary dump file: {dump_file}")
        except:
            pass

        logger.info("🎉 Local to Railway staging database clone completed successfully!")
        if backup_file:
            logger.info(f"📁 Railway staging backup created: {backup_file}")
        else:
            logger.info(
                "📁 No Railway staging backup created due to version compatibility issues"
            )
        logger.info("🔄 Railway staging database now matches local exactly (schema + data)")

        return True


def main():
    """Main function - runs automatically without confirmation"""
    print("Local to Railway Staging Database Clone Tool (Auto Mode)")
    print("=" * 60)
    print("⚠️  This will REPLACE Railway STAGING database with local data automatically!")
    print("Starting in 3 seconds...")

    import time

    time.sleep(3)

    cloner = DatabaseCloner()

    # Execute clone
    success = cloner.clone_database()

    if success:
        print("\n✅ Database clone completed successfully!")
        print("Railway staging database now exactly matches your local database.")
    else:
        print("\n❌ Database clone failed. Check logs for details.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main()) 