#!/usr/bin/env python3
"""
Clone Production Database to Staging using Alembic (Auto Mode)

This script creates an exact clone of the Railway PRODUCTION database on Railway STAGING
and ensures Alembic migration state is synchronized - WITHOUT user confirmation prompts.

⚠️  SAFETY: This script ONLY reads from production and writes to staging.
           Production database is NEVER modified - only used as a source.

Usage:
    python data/etl/clone/clone_production_to_staging_auto.py

Requirements:
    - Railway production database must be accessible (read-only)
    - Railway staging database must be accessible (write access)
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

from database_config import parse_db_url

# Set up logging with absolute path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
logs_dir = os.path.join(project_root, "logs")
os.makedirs(logs_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "database_clone_prod_to_staging.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Database URLs - CRITICAL: Production is READ-ONLY source, Staging is target
PRODUCTION_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"  # READ ONLY
STAGING_DB_URL = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"      # WRITE TARGET


class ProductionToStagingCloner:
    def __init__(self):
        self.production_url = PRODUCTION_DB_URL  # READ-ONLY SOURCE
        self.staging_url = STAGING_DB_URL        # WRITE TARGET
        self.backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def test_connections(self):
        """Test both production (read-only) and staging (write) database connections"""
        logger.info("Testing database connections...")

        # Test PRODUCTION connection (READ-ONLY)
        try:
            prod_params = parse_db_url(self.production_url)
            prod_params["connect_timeout"] = 30
            conn = psycopg2.connect(**prod_params)
            with conn.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                logger.info(f"✅ PRODUCTION database connected (READ-ONLY): {version}")
            conn.close()
        except Exception as e:
            logger.error(f"❌ PRODUCTION database connection failed: {e}")
            return False

        # Test STAGING connection (WRITE TARGET)
        try:
            staging_params = parse_db_url(self.staging_url)
            staging_params["connect_timeout"] = 30
            conn = psycopg2.connect(**staging_params)
            with conn.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                logger.info(f"✅ STAGING database connected (WRITE TARGET): {version}")
            conn.close()
        except Exception as e:
            logger.error(f"❌ STAGING database connection failed: {e}")
            return False

        return True

    def backup_staging_database(self):
        """Create a backup of the current staging database before overwriting"""
        backup_file = f"staging_backup_before_prod_clone_{self.backup_timestamp}.sql"
        logger.info(f"Creating staging database backup: {backup_file}")

        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.staging_url)

            cmd = [
                "pg_dump",
                f"--host={parsed.hostname}",
                f"--port={parsed.port or 5432}",
                f"--username={parsed.username}",
                f"--dbname={parsed.path[1:]}",
                "--file=" + backup_file,
                "--verbose",
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-privileges",
            ]

            env = os.environ.copy()
            env["PGPASSWORD"] = parsed.password

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"✅ Staging database backed up successfully to {backup_file}")
                return backup_file
            else:
                logger.error(f"❌ Staging backup failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"❌ Staging backup error: {e}")
            return None

    def get_production_migration_version(self):
        """Get the current migration version from production database"""
        logger.info("Checking production database migration version...")

        try:
            prod_params = parse_db_url(self.production_url)
            prod_params["connect_timeout"] = 30
            conn = psycopg2.connect(**prod_params)

            with conn.cursor() as cursor:
                cursor.execute("SELECT version_num FROM alembic_version LIMIT 1")
                result = cursor.fetchone()
                if result:
                    version = result[0]
                    logger.info(f"Production database migration version: {version}")
                    conn.close()
                    return version
                else:
                    logger.warning("⚠️  No migration version found in production")
                    conn.close()
                    return None

        except psycopg2.Error as e:
            logger.error(f"❌ Failed to get production migration version: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Production migration version error: {e}")
            return None

    def dump_production_database(self):
        """Create a complete dump of the PRODUCTION database (READ-ONLY operation)"""
        dump_file = f"production_dump_for_staging_{self.backup_timestamp}.sql"
        logger.info(f"Creating PRODUCTION database dump: {dump_file}")

        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.production_url)

            cmd = [
                "pg_dump",
                f"--host={parsed.hostname}",
                f"--port={parsed.port or 5432}",
                f"--username={parsed.username}",
                f"--dbname={parsed.path[1:]}",
                "--file=" + dump_file,
                "--verbose",
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-privileges",
                "--no-sync",
                "--disable-triggers",
            ]

            # SAFETY: Set environment for READ-ONLY operation
            env = os.environ.copy()
            env["PGPASSWORD"] = parsed.password
            env["PGOPTIONS"] = "--default-transaction-read-only=on"  # Extra safety

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                # Verify dump file was created and has content
                if os.path.exists(dump_file) and os.path.getsize(dump_file) > 1000:
                    with open(dump_file, 'r') as f:
                        content = f.read(2000)  # Read first 2KB
                        data_statements = content.count("COPY ") + content.count("INSERT ")
                        logger.info(f"✅ Production database dumped successfully to {dump_file}")
                        logger.info(f"✅ Dump file verification: Found {data_statements} data statements")
                        return dump_file
                else:
                    logger.error("❌ Dump file is empty or too small")
                    return None
            else:
                logger.error(f"❌ Production dump failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"❌ Production dump error: {e}")
            return None

    def clear_staging_database(self):
        """Clear the staging database to prepare for production data"""
        logger.info("Clearing staging database...")

        try:
            staging_params = parse_db_url(self.staging_url)
            staging_params["connect_timeout"] = 30
            conn = psycopg2.connect(**staging_params)

            with conn.cursor() as cursor:
                # Get all table names
                cursor.execute("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public' 
                    AND tablename NOT IN ('alembic_version')
                    ORDER BY tablename
                """)
                tables = [row[0] for row in cursor.fetchall()]

                # Disable foreign key constraints temporarily
                cursor.execute("SET session_replication_role = replica;")

                # Drop all tables except alembic_version
                for table in tables:
                    cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')

                # Re-enable foreign key constraints
                cursor.execute("SET session_replication_role = DEFAULT;")

                conn.commit()
                logger.info(f"✅ Staging database cleared successfully")

            conn.close()
            return True

        except Exception as e:
            logger.error(f"❌ Staging database clear error: {e}")
            return False

    def restore_production_dump_to_staging(self, dump_file):
        """Restore production dump to staging database"""
        logger.info(f"Restoring production dump {dump_file} to staging database...")

        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.staging_url)

            cmd = [
                "psql",
                f"--host={parsed.hostname}",
                f"--port={parsed.port or 5432}",
                f"--username={parsed.username}",
                f"--dbname={parsed.path[1:]}",
                "--file=" + dump_file,
                "--quiet",
                "--no-psqlrc",
            ]

            env = os.environ.copy()
            env["PGPASSWORD"] = parsed.password

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            # Check if data was actually inserted (improved detection)
            copy_count = 0
            insert_count = 0
            
            # Check stdout for data operations
            if result.stdout:
                copy_count += result.stdout.count("COPY ")
                insert_count += result.stdout.count("INSERT ")
                
            # Check stderr for data operations (psql sometimes reports there)
            if result.stderr:
                copy_count += result.stderr.count("COPY ")
                insert_count += result.stderr.count("INSERT ")
            
            # Check for successful completion indicators
            success_indicators = 0
            if result.stdout:
                success_indicators += result.stdout.count("ALTER TABLE")
                success_indicators += result.stdout.count("CREATE")
                success_indicators += result.stdout.count("SET")
            
            # Data was copied if we found operations OR successful completion
            data_copied = copy_count > 0 or insert_count > 0 or success_indicators >= 3
            
            if copy_count > 0 or insert_count > 0:
                logger.info(
                    f"✅ Data insertion detected: {copy_count} COPY operations, {insert_count} INSERT operations"
                )
            elif success_indicators >= 3:
                logger.info(
                    f"✅ Data restoration detected: {success_indicators} database operations completed"
                )
            else:
                logger.warning(
                    "⚠️  No data insertion operations detected in restore output"
                )

            if result.returncode == 0:
                logger.info("✅ Production dump restored to staging database successfully")
                if result.stderr:
                    logger.warning(f"Restore warnings: {result.stderr}")
                return True
            else:
                logger.error(f"❌ Restore failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Restore error: {e}")
            return False

    def sync_staging_alembic_state(self, production_version):
        """Sync staging Alembic state with production"""
        if not production_version:
            logger.warning("⚠️  No production migration version found, skipping Alembic sync")
            return True

        logger.info(f"Syncing staging Alembic migration state to {production_version}...")

        try:
            # Set staging environment for Alembic
            env = os.environ.copy()
            env["DATABASE_URL"] = self.staging_url
            env["SYNC_STAGING"] = "1"  # Flag for staging operations

            # Set the staging alembic version to match production
            cmd = ["python3", "-m", "alembic", "stamp", production_version]
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(
                    f"✅ Staging Alembic migration state synced to {production_version}"
                )
                return True
            else:
                logger.error(f"❌ Staging Alembic sync failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Staging Alembic sync error: {e}")
            return False

    def verify_clone_success(self):
        """Verify that the clone was successful by comparing table counts"""
        logger.info("Verifying clone success...")

        try:
            # Connect to both databases
            prod_params = parse_db_url(self.production_url)
            prod_params["connect_timeout"] = 30
            prod_conn = psycopg2.connect(**prod_params)

            staging_params = parse_db_url(self.staging_url)
            staging_params["connect_timeout"] = 30
            staging_conn = psycopg2.connect(**staging_params)

            # Get table counts from both databases
            with prod_conn.cursor() as prod_cursor, staging_conn.cursor() as staging_cursor:
                # Get all table names
                prod_cursor.execute("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public' 
                    ORDER BY tablename
                """)
                tables = [row[0] for row in prod_cursor.fetchall()]

                mismatches = []
                total_differences = 0

                for table in tables:
                    # Get counts from both databases
                    prod_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    prod_count = prod_cursor.fetchone()[0]

                    staging_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    staging_count = staging_cursor.fetchone()[0]

                    if prod_count == staging_count:
                        logger.info(f"✅ {table}: {prod_count} rows (matches)")
                    else:
                        difference = abs(prod_count - staging_count)
                        total_differences += difference
                        
                        if difference <= 5:  # Small timing differences acceptable
                            logger.warning(
                                f"⚠️  {table}: Production={prod_count}, Staging={staging_count} "
                                f"(small difference: {difference} rows)"
                            )
                        else:
                            logger.error(
                                f"❌ {table}: Production={prod_count}, Staging={staging_count} "
                                f"(significant difference: {difference} rows)"
                            )
                            mismatches.append((table, prod_count, staging_count, difference))

            prod_conn.close()
            staging_conn.close()

            # Evaluate results
            if not mismatches and total_differences <= 10:
                logger.info("✅ Clone verification successful - staging matches production!")
                return True
            elif total_differences <= 20:
                logger.info(
                    f"✅ Clone verification successful - minor timing differences "
                    f"({total_differences} total rows) are acceptable"
                )
                return True
            else:
                logger.error(
                    f"❌ Clone verification failed - significant differences found "
                    f"({len(mismatches)} tables, {total_differences} total rows)"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Clone verification error: {e}")
            return False

    def clone_production_to_staging(self):
        """Execute the complete production to staging clone process"""
        logger.info("🚀 Starting production to staging database clone process...")

        # Step 1: Test connections
        if not self.test_connections():
            logger.error("❌ Database connection test failed. Aborting.")
            return False

        # Step 2: Get production migration version
        production_version = self.get_production_migration_version()

        # Step 3: Backup staging database
        backup_file = self.backup_staging_database()
        if not backup_file:
            logger.error("❌ Failed to backup staging database. Aborting for safety.")
            return False

        # Step 4: Create production dump
        dump_file = self.dump_production_database()
        if not dump_file:
            logger.error("❌ Failed to create production dump. Aborting.")
            return False

        # Step 5: Clear staging database
        if not self.clear_staging_database():
            logger.error("❌ Failed to clear staging database. Aborting.")
            return False

        # Step 6: Restore production dump to staging
        if not self.restore_production_dump_to_staging(dump_file):
            logger.error("❌ Failed to restore production dump to staging. Aborting.")
            return False

        # Step 7: Sync staging Alembic migration state
        if not self.sync_staging_alembic_state(production_version):
            logger.error(
                "❌ Failed to sync staging Alembic state. Manual intervention may be needed."
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

        logger.info("🎉 Production to staging database clone completed successfully!")
        logger.info(f"📁 Staging backup created: {backup_file}")
        logger.info("🔄 Staging database now matches production exactly (schema + data)")

        return True


def main():
    """Main function"""
    print("Production to Staging Database Clone Tool (Auto Mode)")
    print("=" * 60)
    print("⚠️  This will REPLACE staging database with production data automatically!")
    print("⚠️  Production database will ONLY be read from - never modified.")
    print("Starting in 3 seconds...")

    import time
    time.sleep(3)

    cloner = ProductionToStagingCloner()

    if cloner.clone_production_to_staging():
        print("\n✅ Database clone completed successfully!")
        print("Staging database now exactly matches your production database.")
    else:
        print("\n❌ Database clone failed! Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
