#!/usr/bin/env python3
"""
Clone Production Database to Staging (Based on proven ETL pattern)

This script creates an exact clone of the production database (schema + data) on staging
using the proven approach from clone_local_to_railway_auto.py

Usage:
    python scripts/clone_production_to_staging_v2.py

Requirements:
    - Both production and staging databases must be accessible via proxy URLs
    - PostgreSQL client tools (pg_dump, psql) must be installed
"""

import logging
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import RealDictCursor

from database_config import parse_db_url

# Set up logging
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
logs_dir = os.path.join(project_root, "logs")
os.makedirs(logs_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "production_staging_clone.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Database URLs - using PUBLIC URLs for external access
PRODUCTION_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"
STAGING_DB_URL = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"


class ProductionStagingCloner:
    def __init__(self):
        self.production_url = PRODUCTION_DB_URL
        self.staging_url = STAGING_DB_URL
        self.backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def confirm_operation(self):
        """Confirm the potentially destructive operation"""
        print("🚨 PRODUCTION → STAGING DATABASE CLONE 🚨")
        print()
        print("This will:")
        print("1. ✅ Create backup of current staging data")
        print("2. ❌ DROP ALL tables/data in staging database")
        print("3. ✅ Copy complete production schema and data to staging")
        print()
        print("⚠️  This creates a COMPLETE MIRROR of production")
        print("⚠️  All current staging data will be PERMANENTLY LOST")
        print()
        print(f"Production: {self.production_url[:50]}...")
        print(f"Staging:    {self.staging_url[:50]}...")
        print()

        response = input("Type 'yes' to proceed: ")
        return response.lower() == "yes"

    def test_connections(self):
        """Test both production and staging database connections"""
        logger.info("Testing database connections...")

        # Test production connection
        try:
            prod_params = parse_db_url(self.production_url)
            prod_params["connect_timeout"] = 30
            conn = psycopg2.connect(**prod_params)
            with conn.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                logger.info(f"✅ Production database connected: {version[:50]}...")
            conn.close()
        except Exception as e:
            logger.error(f"❌ Production database connection failed: {e}")
            return False

        # Test staging connection
        try:
            staging_params = parse_db_url(self.staging_url)
            staging_params["connect_timeout"] = 30
            conn = psycopg2.connect(**staging_params)
            with conn.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                logger.info(f"✅ Staging database connected: {version[:50]}...")
            conn.close()
        except Exception as e:
            logger.error(f"❌ Staging database connection failed: {e}")
            return False

        return True

    def backup_staging_database(self):
        """Create a backup of the current staging database before overwriting"""
        backup_file = f"staging_backup_before_prod_clone_{self.backup_timestamp}.sql"
        backup_path = os.path.join("data", "backups", backup_file)
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)

        logger.info(f"Creating staging database backup: {backup_path}")

        try:
            parsed = urlparse(self.staging_url)

            cmd = [
                "pg_dump",
                f"--host={parsed.hostname}",
                f"--port={parsed.port or 5432}",
                f"--username={parsed.username}",
                f"--dbname={parsed.path[1:]}",  # Remove leading /
                f"--file={backup_path}",
                "--verbose",
                "--clean",
                "--if-exists",
                "--create",
                "--no-owner",
                "--no-privileges",
                "--disable-triggers",
            ]

            env = os.environ.copy()
            env["PGPASSWORD"] = parsed.password

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"✅ Staging backup created: {backup_path}")
                return backup_path
            else:
                logger.error(f"❌ Staging backup failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"❌ Staging backup error: {e}")
            return None

    def get_table_counts(self, db_url, db_name):
        """Get row counts for all tables in a database"""
        logger.info(f"Getting table counts for {db_name} database...")

        try:
            params = parse_db_url(db_url)
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
                logger.info(f"{db_name} has {len(tables)} tables")

                # Get count for each table
                total_rows = 0
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    table_counts[table] = count
                    total_rows += count

                logger.info(f"{db_name} total rows: {total_rows}")

            conn.close()
            return table_counts

        except Exception as e:
            logger.error(f"Failed to get {db_name} table counts: {e}")
            return {}

    def dump_production_database(self):
        """Create a complete dump of the production database"""
        dump_file = f"production_dump_for_staging_{self.backup_timestamp}.sql"
        dump_path = os.path.join(tempfile.gettempdir(), dump_file)
        logger.info(f"Creating production database dump: {dump_path}")

        try:
            parsed = urlparse(self.production_url)

            cmd = [
                "pg_dump",
                f"--host={parsed.hostname}",
                f"--port={parsed.port or 5432}",
                f"--username={parsed.username}",
                f"--dbname={parsed.path[1:]}",  # Remove leading /
                f"--file={dump_path}",
                "--verbose",
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-privileges",
                "--disable-triggers",
                # Note: No --create flag to avoid database creation conflicts
            ]

            env = os.environ.copy()
            env["PGPASSWORD"] = parsed.password

            result = subprocess.run(
                cmd, env=env, capture_output=True, text=True, timeout=600
            )

            if result.returncode == 0:
                logger.info(f"✅ Production dump created: {dump_path}")

                # Verify dump file contains data
                try:
                    with open(dump_path, "r") as f:
                        dump_content = f.read()
                        insert_count = dump_content.count("INSERT INTO")
                        copy_count = dump_content.count("COPY ")
                        data_statements = insert_count + copy_count

                        if data_statements > 0:
                            logger.info(
                                f"✅ Dump verification: {data_statements} data statements found"
                            )
                        else:
                            logger.warning(
                                "⚠️  Dump verification: No data statements found!"
                            )

                        file_size = os.path.getsize(dump_path)
                        logger.info(f"Dump file size: {file_size:,} bytes")

                except Exception as e:
                    logger.warning(f"⚠️  Could not verify dump content: {e}")

                return dump_path
            else:
                logger.error(f"❌ Production dump failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"❌ Production dump error: {e}")
            return None

    def clear_staging_database(self):
        """Drop all objects in staging database to prepare for restore"""
        logger.info("Clearing staging database...")

        try:
            staging_params = parse_db_url(self.staging_url)
            staging_params["connect_timeout"] = 30
            conn = psycopg2.connect(**staging_params)
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

                logger.info("✅ Staging database cleared successfully")

            conn.close()
            return True

        except Exception as e:
            logger.error(f"❌ Failed to clear staging database: {e}")
            return False

    def restore_production_dump_to_staging(self, dump_file):
        """Restore production dump to staging database"""
        logger.info(f"Restoring production dump to staging database...")

        try:
            parsed = urlparse(self.staging_url)

            cmd = [
                "psql",
                f"--host={parsed.hostname}",
                f"--port={parsed.port or 5432}",
                f"--username={parsed.username}",
                f"--dbname={parsed.path[1:]}",  # Remove leading /
                f"--file={dump_file}",
                "--echo-errors",
                "--set=ON_ERROR_STOP=off",  # Continue on errors but report them
            ]

            env = os.environ.copy()
            env["PGPASSWORD"] = parsed.password

            result = subprocess.run(
                cmd, env=env, capture_output=True, text=True, timeout=600
            )

            # Check if data was actually inserted
            data_copied = False
            if result.stdout:
                copy_count = result.stdout.count("COPY ")
                insert_count = result.stdout.count("INSERT ")
                data_copied = copy_count > 0 or insert_count > 0
                if data_copied:
                    logger.info(
                        f"✅ Data detected: {copy_count} COPY ops, {insert_count} INSERT ops"
                    )

            if result.returncode == 0:
                logger.info("✅ Production dump restored to staging successfully")
                if result.stderr:
                    logger.warning(f"Restore warnings: {result.stderr}")
                return True
            elif data_copied:
                logger.warning(
                    f"⚠️  Restore completed with warnings (exit code {result.returncode})"
                )
                logger.warning("⚠️  But data was successfully copied")
                if result.stderr:
                    logger.warning(f"Warnings: {result.stderr}")
                return True
            else:
                logger.error(f"❌ Restore failed with exit code {result.returncode}")
                logger.error(f"❌ Stderr: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Restore error: {e}")
            return False

    def verify_clone_success(self):
        """Verify clone success by comparing table counts"""
        logger.info("🔍 Verifying clone success...")

        try:
            prod_counts = self.get_table_counts(self.production_url, "Production")
            staging_counts = self.get_table_counts(self.staging_url, "Staging")

            if not prod_counts or not staging_counts:
                logger.error("❌ Failed to get table counts for verification")
                return False

            # Compare counts
            all_match = True
            mismatches = []

            for table in prod_counts:
                prod_count = prod_counts[table]
                staging_count = staging_counts.get(table, 0)

                if prod_count == staging_count:
                    logger.info(f"✅ {table}: {prod_count} rows (matches)")
                else:
                    logger.error(
                        f"❌ {table}: Prod={prod_count}, Staging={staging_count} (MISMATCH)"
                    )
                    mismatches.append(table)
                    all_match = False

            # Check for extra tables in staging
            for table in staging_counts:
                if table not in prod_counts:
                    logger.warning(f"⚠️  {table}: Exists in staging but not production")

            if all_match:
                logger.info("🎉 Clone verification SUCCESS - all table counts match!")
            else:
                logger.error(
                    f"❌ Clone verification FAILED - {len(mismatches)} mismatches: {mismatches}"
                )

            return all_match

        except Exception as e:
            logger.error(f"❌ Verification error: {e}")
            return False

    def cleanup_dump_file(self, dump_file):
        """Clean up temporary dump file"""
        try:
            if dump_file and os.path.exists(dump_file):
                os.unlink(dump_file)
                logger.info(f"🧹 Cleaned up dump file: {dump_file}")
        except Exception as e:
            logger.warning(f"⚠️  Could not cleanup dump file: {e}")

    def clone_database(self):
        """Execute the complete production → staging clone process"""
        logger.info("🚀 Starting production → staging database clone...")

        # Step 1: Confirm operation
        if not self.confirm_operation():
            logger.info("❌ Operation cancelled by user")
            return False

        # Step 2: Test connections
        if not self.test_connections():
            logger.error("❌ Database connection test failed")
            return False

        # Step 3: Get initial statistics
        logger.info("📊 Getting initial database statistics...")
        self.get_table_counts(self.production_url, "Production (source)")
        self.get_table_counts(self.staging_url, "Staging (before clone)")

        # Step 4: Backup staging database
        backup_file = self.backup_staging_database()
        if not backup_file:
            logger.error("❌ Failed to backup staging database")
            return False

        dump_file = None
        try:
            # Step 5: Dump production database
            dump_file = self.dump_production_database()
            if not dump_file:
                logger.error("❌ Failed to dump production database")
                return False

            # Step 6: Clear staging database
            if not self.clear_staging_database():
                logger.error("❌ Failed to clear staging database")
                return False

            # Step 7: Restore production dump to staging
            if not self.restore_production_dump_to_staging(dump_file):
                logger.error("❌ Failed to restore production data to staging")
                return False

            # Step 8: Verify clone success
            if not self.verify_clone_success():
                logger.error("❌ Clone verification failed")
                return False

            logger.info("🎉 Production → Staging clone completed successfully!")
            logger.info(f"💾 Staging backup preserved at: {backup_file}")
            logger.info("✅ Staging now contains complete production data")

            return True

        except Exception as e:
            logger.error(f"❌ Clone process failed: {e}")
            return False

        finally:
            # Always cleanup dump file
            self.cleanup_dump_file(dump_file)


def main():
    """Main function"""
    try:
        cloner = ProductionStagingCloner()
        success = cloner.clone_database()

        if success:
            print("\n🎉 SUCCESS! Production data cloned to staging.")
            print(
                "Your staging environment now has complete production data for testing."
            )
            sys.exit(0)
        else:
            print("\n❌ FAILED! Clone operation was not successful.")
            print("Check the logs for details.")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
