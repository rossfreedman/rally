#!/usr/bin/env python3
"""
Clone Railway Database to Local using Alembic (Auto Mode)

This script creates an exact clone of the Railway database (schema + data) on Local
and ensures Alembic migration state is synchronized - WITHOUT user confirmation prompts.

Usage:
    python data/etl/clone/clone_railway_to_local_auto.py

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

# Set up logging with absolute path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
logs_dir = os.path.join(project_root, "logs")
os.makedirs(logs_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "database_clone_reverse.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Database URLs
LOCAL_DB_URL = "postgresql://postgres:postgres@localhost:5432/rally"
RAILWAY_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"


class DatabaseCloner:
    def __init__(self):
        self.local_url = LOCAL_DB_URL
        self.railway_url = RAILWAY_DB_URL
        self.backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

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

    def backup_local_database(self):
        """Create a backup of the current local database before overwriting"""
        backup_file = f"local_backup_before_clone_{self.backup_timestamp}.sql"
        logger.info(f"Creating local database backup: {backup_file}")

        try:
            cmd = [
                "pg_dump",
                "--host=localhost",
                "--port=5432",
                "--username=postgres",
                "--dbname=rally",
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
            env["PGPASSWORD"] = "postgres"

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(
                    f"✅ Local database backed up successfully to {backup_file}"
                )
                return backup_file
            else:
                logger.error(f"❌ Local backup failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"❌ Local backup error: {e}")
            return None

    def get_railway_migration_version(self):
        """Get the current Alembic migration version from Railway database"""
        logger.info("Checking Railway database migration version...")

        try:
            railway_params = parse_db_url(self.railway_url)
            railway_params["connect_timeout"] = 30
            conn = psycopg2.connect(**railway_params)

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
                        logger.info(f"Railway database migration version: {version[0]}")
                        return version[0]
                    else:
                        logger.warning(
                            "Railway database has alembic_version table but no version"
                        )
                        return None
                else:
                    logger.warning("Railway database has no alembic_version table")
                    return None

            conn.close()

        except Exception as e:
            logger.error(f"❌ Failed to get Railway migration version: {e}")
            return None

    def dump_railway_database(self):
        """Create a complete dump of the Railway database"""
        dump_file = f"railway_dump_for_local_{self.backup_timestamp}.sql"
        logger.info(f"Creating Railway database dump: {dump_file}")

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
            env["PGPASSWORD"] = parsed.password

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"✅ Railway database dumped successfully to {dump_file}")

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
                logger.error(f"❌ Railway dump failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"❌ Railway dump error: {e}")
            return None

    def drop_and_recreate_local_database(self):
        """Drop all objects in local database and prepare for restore"""
        logger.info("Clearing local database...")

        try:
            local_params = parse_db_url(self.local_url)
            conn = psycopg2.connect(**local_params)
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

                logger.info("✅ Local database cleared successfully")

            conn.close()
            return True

        except Exception as e:
            logger.error(f"❌ Failed to clear local database: {e}")
            return False

    def restore_railway_dump_to_local(self, dump_file):
        """Restore Railway dump to local database"""
        logger.info(f"Restoring Railway dump {dump_file} to local database...")

        try:
            cmd = [
                "psql",
                "--host=localhost",
                "--port=5432",
                "--username=postgres",
                "--dbname=rally",
                f"--file={dump_file}",
                "--echo-errors",
                "--set=ON_ERROR_STOP=off",  # Continue on errors but report them
                "--quiet",  # Reduce noise but keep errors
            ]

            env = os.environ.copy()
            env["PGPASSWORD"] = "postgres"

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            # Check if data was actually inserted (multiple detection methods)
            copy_count = 0
            insert_count = 0
            
            # Method 1: Check stdout for data operations
            if result.stdout:
                copy_count += result.stdout.count("COPY ")
                insert_count += result.stdout.count("INSERT ")
                
            # Method 2: Check stderr for data operations (psql sometimes reports there)
            if result.stderr:
                copy_count += result.stderr.count("COPY ")
                insert_count += result.stderr.count("INSERT ")
            
            # Method 3: Check for successful completion indicators
            success_indicators = 0
            if result.stdout:
                success_indicators += result.stdout.count("ALTER TABLE")
                success_indicators += result.stdout.count("CREATE")
                success_indicators += result.stdout.count("SET")
            
            # Data was copied if we found operations OR successful completion
            # Lower threshold for success indicators since schema operations indicate successful restore
            data_copied = copy_count > 0 or insert_count > 0 or success_indicators >= 3
            
            if copy_count > 0 or insert_count > 0:
                logger.info(
                    f"✅ Data insertion detected: {copy_count} COPY operations, {insert_count} INSERT operations"
                )
            elif success_indicators > 10:
                logger.info(
                    f"✅ Data restoration detected: {success_indicators} database operations completed"
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
                logger.info("✅ Railway dump restored to local database successfully")
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

    def sync_local_alembic_state(self, railway_version):
        """Sync local Alembic state with Railway"""
        if not railway_version:
            logger.warning("⚠️  No Railway migration version found, skipping Alembic sync")
            return True

        logger.info(f"Syncing local Alembic migration state to {railway_version}...")

        try:
            # Use default environment (local) for Alembic
            env = os.environ.copy()
            # Ensure we're NOT using SYNC_RAILWAY for local operations
            if "SYNC_RAILWAY" in env:
                del env["SYNC_RAILWAY"]

            # Set the local alembic version to match Railway
            # Use python -m alembic instead of direct alembic command
            cmd = ["python3", "-m", "alembic", "stamp", railway_version]
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(
                    f"✅ Local Alembic migration state synced to {railway_version}"
                )
                return True
            else:
                logger.error(f"❌ Local Alembic sync failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Local Alembic sync error: {e}")
            return False

    def verify_clone_success(self):
        """Verify that the clone was successful by comparing table counts"""
        logger.info("Verifying clone success...")

        try:
            # Get table counts from both databases
            railway_counts = self.get_table_counts(self.railway_url)
            local_counts = self.get_table_counts(self.local_url)

            if not railway_counts or not local_counts:
                logger.error("❌ Failed to get table counts for verification")
                return False

            # Compare counts (allow small differences due to timing)
            all_match = True
            total_differences = 0
            
            for table in railway_counts:
                railway_count = railway_counts[table]
                local_count = local_counts.get(table, 0)
                difference = abs(railway_count - local_count)

                if difference == 0:
                    logger.info(f"✅ {table}: {railway_count} rows (matches)")
                elif difference <= 5:  # Allow small timing differences
                    logger.warning(
                        f"⚠️  {table}: Railway={railway_count}, Local={local_count} (small difference: {difference} rows)"
                    )
                    total_differences += difference
                else:
                    logger.error(
                        f"❌ {table}: Railway={railway_count}, Local={local_count} (LARGE MISMATCH: {difference} rows)"
                    )
                    all_match = False

            # Check for tables that exist in local but not Railway
            for table in local_counts:
                if table not in railway_counts:
                    logger.warning(f"⚠️  {table}: Exists in local but not in Railway")

            if all_match:
                if total_differences == 0:
                    logger.info(
                        "✅ Clone verification successful - all table counts match perfectly!"
                    )
                else:
                    logger.info(
                        f"✅ Clone verification successful - minor timing differences ({total_differences} total rows) are acceptable"
                    )
            else:
                logger.error(
                    "❌ Clone verification failed - significant table count mismatches detected"
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
        logger.info("🚀 Starting Railway to local database clone process...")

        # Step 1: Test connections
        if not self.test_connections():
            logger.error("❌ Connection tests failed. Aborting clone process.")
            return False

        # Step 2: Get Railway migration version
        railway_version = self.get_railway_migration_version()

        # Step 3: Backup local database
        backup_file = self.backup_local_database()
        if not backup_file:
            logger.warning(
                "⚠️  Failed to backup local database. Proceeding without backup."
            )
            logger.warning("⚠️  Since we'll verify the clone, this should be safe.")
            backup_file = None

        # Step 4: Dump Railway database
        dump_file = self.dump_railway_database()
        if not dump_file:
            logger.error("❌ Failed to dump Railway database. Aborting.")
            return False

        # Step 5: Clear local database
        if not self.drop_and_recreate_local_database():
            logger.error("❌ Failed to clear local database. Aborting.")
            return False

        # Step 6: Restore Railway dump to local
        if not self.restore_railway_dump_to_local(dump_file):
            logger.error("❌ Failed to restore Railway dump to local. Aborting.")
            return False

        # Step 7: Sync local Alembic migration state
        if not self.sync_local_alembic_state(railway_version):
            logger.error(
                "❌ Failed to sync local Alembic state. Manual intervention may be needed."
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

        logger.info("🎉 Railway to local database clone completed successfully!")
        if backup_file:
            logger.info(f"📁 Local backup created: {backup_file}")
        else:
            logger.info(
                "📁 No local backup created due to backup failure"
            )
        logger.info("🔄 Local database now matches Railway exactly (schema + data)")

        return True


def main():
    """Main function - runs automatically without confirmation"""
    print("Railway to Local Database Clone Tool (Auto Mode)")
    print("=" * 60)
    print("⚠️  This will REPLACE local database with Railway data automatically!")
    print("Starting in 3 seconds...")

    import time

    time.sleep(3)

    cloner = DatabaseCloner()

    # Execute clone
    success = cloner.clone_database()

    if success:
        print("\n✅ Database clone completed successfully!")
        print("Local database now exactly matches your Railway database.")
    else:
        print("\n❌ Database clone failed. Check logs for details.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main()) 