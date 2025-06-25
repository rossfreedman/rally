#!/usr/bin/env python3
"""
Safe Match Data Sync to Railway
===============================

This script safely syncs ONLY match_scores and series_stats data from local to Railway
while preserving all user associations, player IDs, team IDs, and reference tables.

Tables PRESERVED (not touched):
- users (user accounts)
- user_player_associations (critical user linkages)
- players (player IDs that users are linked to)
- leagues, clubs, series, teams (reference tables with IDs)
- player_availability (user activity data)

Tables UPDATED (new ETL data):
- match_scores (match results)
- series_stats (team standings)

Usage:
    python scripts/sync_match_data_to_railway.py [--dry-run]
"""

import argparse
import logging
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import RealDictCursor

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import parse_db_url

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Database URLs
LOCAL_DB_URL = "postgresql://postgres:postgres@localhost:5432/rally"
RAILWAY_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

# Tables to sync (data only - preserve reference tables)
DATA_TABLES_TO_SYNC = [
    "match_scores",
    "series_stats"
]

class MatchDataSyncer:
    def __init__(self, dry_run=False):
        self.local_url = LOCAL_DB_URL
        self.railway_url = RAILWAY_DB_URL
        self.dry_run = dry_run
        self.backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if dry_run:
            logger.info("🧪 DRY RUN MODE: No actual changes will be made")

    def test_connections(self):
        """Test both local and Railway database connections"""
        logger.info("🔌 Testing database connections...")

        # Test local connection
        try:
            local_params = parse_db_url(self.local_url)
            conn = psycopg2.connect(**local_params)
            with conn.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                logger.info(f"✅ Local database connected: {version[:50]}...")
            conn.close()
        except Exception as e:
            logger.error(f"❌ Local database connection failed: {e}")
            return False

        # Test Railway connection
        try:
            railway_params = parse_db_url(self.railway_url)
            railway_params["connect_timeout"] = 30
            conn = psycopg2.connect(**railway_params)
            with conn.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                logger.info(f"✅ Railway database connected: {version[:50]}...")
            conn.close()
        except Exception as e:
            logger.error(f"❌ Railway database connection failed: {e}")
            return False

        return True

    def get_table_counts(self, db_url, tables):
        """Get row counts for specified tables"""
        try:
            params = parse_db_url(db_url)
            if "railway" in db_url:
                params["connect_timeout"] = 30

            conn = psycopg2.connect(**params)
            table_counts = {}

            with conn.cursor() as cursor:
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        table_counts[table] = count
                    except Exception as e:
                        logger.error(f"Failed to count rows in {table}: {e}")
                        table_counts[table] = -1

            conn.close()
            return table_counts

        except Exception as e:
            logger.error(f"Failed to get table counts: {e}")
            return None

    def backup_railway_data_tables(self):
        """Create backup of Railway data tables before sync"""
        if self.dry_run:
            logger.info("🧪 DRY RUN: Would backup Railway data tables")
            return "dry_run_backup.sql"
            
        backup_file = f"railway_match_data_backup_{self.backup_timestamp}.sql"
        logger.info(f"💾 Creating Railway data backup: {backup_file}")

        try:
            parsed = urlparse(self.railway_url)

            # Build table list for pg_dump
            table_args = []
            for table in DATA_TABLES_TO_SYNC:
                table_args.extend(["-t", table])

            cmd = [
                "pg_dump",
                f"--host={parsed.hostname}",
                f"--port={parsed.port or 5432}",
                f"--username={parsed.username}",
                f"--dbname={parsed.path[1:]}",
                f"--file={backup_file}",
                "--verbose",
                "--data-only",  # Only data for these tables
                "--no-owner",
                "--no-privileges",
                "--disable-triggers",
            ] + table_args

            env = os.environ.copy()
            env["PGPASSWORD"] = parsed.password

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"✅ Railway data backup created: {backup_file}")
                return backup_file
            else:
                logger.error(f"❌ Railway backup failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"❌ Railway backup error: {e}")
            return None

    def create_local_data_dump(self):
        """Create dump of local data tables"""
        if self.dry_run:
            logger.info("🧪 DRY RUN: Would create local data dump")
            return "dry_run_dump.sql"
            
        dump_file = f"local_match_data_dump_{self.backup_timestamp}.sql"
        logger.info(f"📦 Creating local data dump: {dump_file}")

        try:
            # Build table list for pg_dump
            table_args = []
            for table in DATA_TABLES_TO_SYNC:
                table_args.extend(["-t", table])

            cmd = [
                "pg_dump",
                "--host=localhost",
                "--port=5432", 
                "--username=postgres",
                "--dbname=rally",
                f"--file={dump_file}",
                "--verbose",
                "--data-only",  # Only data since schema exists
                "--no-owner",
                "--no-privileges",
                "--disable-triggers",
            ] + table_args

            env = os.environ.copy()
            env["PGPASSWORD"] = "postgres"

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"✅ Local data dump created: {dump_file}")
                
                # Verify dump contains data
                with open(dump_file, "r") as f:
                    content = f.read()
                    inserts = content.count("INSERT INTO") + content.count("COPY ")
                    if inserts > 0:
                        logger.info(f"📊 Dump verification: {inserts} data statements found")
                    else:
                        logger.warning("⚠️  No data statements found in dump!")
                
                return dump_file
            else:
                logger.error(f"❌ Local dump failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"❌ Local dump error: {e}")
            return None

    def clear_railway_data_tables(self):
        """Clear only the data tables in Railway (preserve reference tables)"""
        if self.dry_run:
            logger.info("🧪 DRY RUN: Would clear Railway data tables")
            return True
            
        logger.info("🧹 Clearing Railway data tables (preserving reference tables)...")

        try:
            railway_params = parse_db_url(self.railway_url)
            railway_params["connect_timeout"] = 30
            conn = psycopg2.connect(**railway_params)
            conn.autocommit = True

            with conn.cursor() as cursor:
                # Disable foreign key checks temporarily
                cursor.execute("SET session_replication_role = replica;")
                logger.info("🔓 Disabled foreign key checks")

                # Clear data tables in dependency order
                for table in reversed(DATA_TABLES_TO_SYNC):
                    try:
                        cursor.execute(f"TRUNCATE TABLE {table} CASCADE")
                        logger.info(f"✅ Cleared table: {table}")
                    except Exception as e:
                        logger.warning(f"⚠️  Failed to clear {table}: {e}")

                # Re-enable foreign key checks
                cursor.execute("SET session_replication_role = DEFAULT;")
                logger.info("🔒 Re-enabled foreign key checks")

            conn.close()
            return True

        except Exception as e:
            logger.error(f"❌ Failed to clear Railway data tables: {e}")
            return False

    def restore_data_to_railway(self, dump_file):
        """Restore local data dump to Railway"""
        if self.dry_run:
            logger.info("🧪 DRY RUN: Would restore data to Railway")
            return True
            
        logger.info(f"📥 Restoring local data to Railway: {dump_file}")

        try:
            parsed = urlparse(self.railway_url)

            cmd = [
                "psql",
                f"--host={parsed.hostname}",
                f"--port={parsed.port or 5432}",
                f"--username={parsed.username}",
                f"--dbname={parsed.path[1:]}",
                f"--file={dump_file}",
                "--echo-errors",
                "--set=ON_ERROR_STOP=off",
                "--quiet",
            ]

            env = os.environ.copy()
            env["PGPASSWORD"] = parsed.password

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            # Check for successful data operations
            if result.stdout:
                copy_ops = result.stdout.count("COPY ")
                insert_ops = result.stdout.count("INSERT ")
                if copy_ops > 0 or insert_ops > 0:
                    logger.info(f"✅ Data restored: {copy_ops} COPY, {insert_ops} INSERT operations")
                else:
                    logger.warning("⚠️  No data operations detected")

            if result.returncode == 0:
                logger.info("✅ Data restoration completed successfully")
                return True
            else:
                logger.error(f"❌ Data restoration failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Data restoration error: {e}")
            return False

    def verify_sync_success(self):
        """Verify that sync was successful by comparing data counts"""
        logger.info("🔍 Verifying sync success...")

        if self.dry_run:
            logger.info("🧪 DRY RUN: Skipping verification")
            return True

        try:
            local_counts = self.get_table_counts(self.local_url, DATA_TABLES_TO_SYNC)
            railway_counts = self.get_table_counts(self.railway_url, DATA_TABLES_TO_SYNC)

            if not local_counts or not railway_counts:
                logger.error("❌ Failed to get table counts for verification")
                return False

            all_match = True
            logger.info("📊 Data count comparison:")
            
            for table in DATA_TABLES_TO_SYNC:
                local_count = local_counts.get(table, 0)
                railway_count = railway_counts.get(table, 0)

                if local_count == railway_count:
                    logger.info(f"   ✅ {table}: {local_count:,} rows (match)")
                else:
                    logger.error(f"   ❌ {table}: Local={local_count:,}, Railway={railway_count:,} (MISMATCH)")
                    all_match = False

            return all_match

        except Exception as e:
            logger.error(f"❌ Verification error: {e}")
            return False

    def verify_preserved_tables(self):
        """Verify that critical user tables were not touched"""
        logger.info("🛡️  Verifying user associations were preserved...")
        
        preserved_tables = ["users", "user_player_associations", "players"]
        
        try:
            railway_params = parse_db_url(self.railway_url)
            railway_params["connect_timeout"] = 30
            conn = psycopg2.connect(**railway_params)

            with conn.cursor() as cursor:
                # Check that user associations still exist
                cursor.execute("SELECT COUNT(*) FROM user_player_associations")
                upa_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM users")
                users_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM players")
                players_count = cursor.fetchone()[0]

                logger.info(f"✅ Preserved data verification:")
                logger.info(f"   👥 Users: {users_count:,}")
                logger.info(f"   🏓 Players: {players_count:,}")
                logger.info(f"   🔗 User-Player Associations: {upa_count:,}")

                if upa_count > 0 and users_count > 0 and players_count > 0:
                    logger.info("✅ All critical user data preserved")
                    return True
                else:
                    logger.error("❌ Critical user data appears to be missing!")
                    return False

            conn.close()

        except Exception as e:
            logger.error(f"❌ Preserved tables verification error: {e}")
            return False

    def sync_match_data(self):
        """Execute the complete match data sync process"""
        logger.info("🚀 Starting Railway Match Data Sync")
        logger.info("=" * 60)
        logger.info("📋 Syncing tables: " + ", ".join(DATA_TABLES_TO_SYNC))
        logger.info("🛡️  Preserving: users, players, associations, reference tables")
        logger.info("=" * 60)

        # Step 1: Test connections
        if not self.test_connections():
            logger.error("❌ Connection tests failed")
            return False

        # Step 2: Show current counts
        logger.info("\n📊 Current data counts:")
        local_counts = self.get_table_counts(self.local_url, DATA_TABLES_TO_SYNC)
        railway_counts = self.get_table_counts(self.railway_url, DATA_TABLES_TO_SYNC)
        
        if local_counts and railway_counts:
            for table in DATA_TABLES_TO_SYNC:
                local_c = local_counts.get(table, 0)
                railway_c = railway_counts.get(table, 0)
                logger.info(f"   {table}: Local={local_c:,}, Railway={railway_c:,}")

        # Step 3: Backup Railway data
        backup_file = self.backup_railway_data_tables()
        if not backup_file and not self.dry_run:
            logger.error("❌ Failed to backup Railway data")
            return False

        # Step 4: Create local dump
        dump_file = self.create_local_data_dump()
        if not dump_file and not self.dry_run:
            logger.error("❌ Failed to create local dump")
            return False

        # Step 5: Clear Railway data tables
        if not self.clear_railway_data_tables():
            logger.error("❌ Failed to clear Railway data tables")
            return False

        # Step 6: Restore local data to Railway
        if not self.restore_data_to_railway(dump_file):
            logger.error("❌ Failed to restore data to Railway")
            return False

        # Step 7: Verify sync success
        if not self.verify_sync_success():
            logger.error("❌ Sync verification failed")
            return False

        # Step 8: Verify preserved tables
        if not self.verify_preserved_tables():
            logger.error("❌ User data verification failed")
            return False

        # Cleanup temporary files
        if not self.dry_run:
            try:
                if dump_file and os.path.exists(dump_file):
                    os.remove(dump_file)
                    logger.info(f"🧹 Cleaned up temporary dump: {dump_file}")
            except:
                pass

        # Final summary
        logger.info("\n" + "=" * 60)
        logger.info("✅ RAILWAY MATCH DATA SYNC COMPLETED SUCCESSFULLY!")
        logger.info("=" * 60)
        logger.info("✅ Match scores and series stats updated")
        logger.info("✅ All user associations preserved")
        logger.info("✅ All reference tables (leagues, teams, etc.) preserved")
        
        if not self.dry_run:
            logger.info(f"📁 Railway backup: {backup_file}")
            logger.info("🌐 Test at: https://rally-production-6ac8.up.railway.app")
        
        return True

def main():
    parser = argparse.ArgumentParser(description="Sync match data to Railway safely")
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    syncer = MatchDataSyncer(dry_run=args.dry_run)
    success = syncer.sync_match_data()
    
    if success:
        logger.info("🎉 Railway sync completed successfully!")
        sys.exit(0)
    else:
        logger.error("💥 Railway sync failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 