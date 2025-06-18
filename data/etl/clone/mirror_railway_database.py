#!/usr/bin/env python3
"""
Mirror Railway Database Locally using Alembic

This script creates an exact mirror of the Railway database (schema + data) locally
and ensures Alembic migration state is synchronized.

Usage:
    python scripts/mirror_railway_database.py

Requirements:
    - Railway database must be accessible via proxy URL
    - Local PostgreSQL server must be running
    - Alembic must be properly configured
"""

import os
import sys
import subprocess
import tempfile
import logging
from datetime import datetime
from contextlib import contextmanager

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text
from database_config import get_db, parse_db_url

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../../../logs/database_mirror.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database URLs
LOCAL_DB_URL = "postgresql://postgres:postgres@localhost:5432/rally"
RAILWAY_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

class DatabaseMirror:
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
            railway_params['connect_timeout'] = 30  # Longer timeout for Railway
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
        """Create a backup of the current local database"""
        backup_file = f"local_backup_before_mirror_{self.backup_timestamp}.sql"
        logger.info(f"Creating local database backup: {backup_file}")
        
        try:
            # Use pg_dump to create backup
            cmd = [
                "pg_dump",
                "--host=localhost",
                "--port=5432", 
                "--username=postgres",
                "--dbname=rally",
                "--file=" + backup_file,
                "--verbose",
                "--clean",
                "--if-exists",
                "--create"
            ]
            
            # Set PGPASSWORD environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = 'postgres'
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ Local database backed up successfully to {backup_file}")
                return backup_file
            else:
                logger.error(f"❌ Backup failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Backup error: {e}")
            return None
    
    def get_railway_migration_version(self):
        """Get the current Alembic migration version from Railway database"""
        logger.info("Checking Railway database migration version...")
        
        try:
            railway_params = parse_db_url(self.railway_url)
            railway_params['connect_timeout'] = 30
            conn = psycopg2.connect(**railway_params)
            
            with conn.cursor() as cursor:
                # Check if alembic_version table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'alembic_version'
                    )
                """)
                
                if cursor.fetchone()[0]:
                    cursor.execute("SELECT version_num FROM alembic_version")
                    version = cursor.fetchone()
                    if version:
                        logger.info(f"Railway database migration version: {version[0]}")
                        return version[0]
                    else:
                        logger.warning("Railway database has alembic_version table but no version")
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
        dump_file = f"railway_dump_{self.backup_timestamp}.sql"
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
                f"--file={dump_file}",
                "--verbose",
                "--clean",
                "--if-exists",
                "--create",
                "--no-owner",
                "--no-privileges"
            ]
            
            # Set password in environment
            env = os.environ.copy()
            env['PGPASSWORD'] = parsed.password
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ Railway database dumped successfully to {dump_file}")
                return dump_file
            else:
                logger.error(f"❌ Railway dump failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Railway dump error: {e}")
            return None
    
    def drop_and_recreate_local_database(self):
        """Drop and recreate the local rally database"""
        logger.info("Dropping and recreating local rally database...")
        
        try:
            # Connect to postgres database to drop rally
            postgres_params = parse_db_url("postgresql://postgres:postgres@localhost:5432/postgres")
            conn = psycopg2.connect(**postgres_params)
            conn.autocommit = True
            
            with conn.cursor() as cursor:
                # Terminate existing connections
                cursor.execute("""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = 'rally'
                    AND pid <> pg_backend_pid()
                """)
                
                # Drop database
                cursor.execute("DROP DATABASE IF EXISTS rally")
                logger.info("✅ Dropped existing rally database")
                
                # Create database
                cursor.execute("CREATE DATABASE rally")
                logger.info("✅ Created new rally database")
                
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to recreate database: {e}")
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
                "--file=" + dump_file,
                "--quiet"
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = 'postgres'
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Railway dump restored to local database successfully")
                return True
            else:
                logger.error(f"❌ Restore failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Restore error: {e}")
            return False
    
    def sync_alembic_migration_state(self, railway_version):
        """Sync local Alembic state with Railway"""
        if not railway_version:
            logger.warning("⚠️  No Railway migration version found, skipping Alembic sync")
            return True
            
        logger.info(f"Syncing Alembic migration state to {railway_version}...")
        
        try:
            # Set the local alembic version to match Railway
            cmd = ["alembic", "stamp", railway_version]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ Alembic migration state synced to {railway_version}")
                
                # Verify the sync
                verify_cmd = ["alembic", "current"]
                verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
                logger.info(f"Current local migration state: {verify_result.stdout.strip()}")
                return True
            else:
                logger.error(f"❌ Alembic sync failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Alembic sync error: {e}")
            return False
    
    def verify_mirror_success(self):
        """Verify that the mirror was successful by comparing table counts"""
        logger.info("Verifying mirror success...")
        
        try:
            # Get table counts from both databases
            local_counts = self.get_table_counts(self.local_url)
            railway_counts = self.get_table_counts(self.railway_url)
            
            if not local_counts or not railway_counts:
                logger.error("❌ Failed to get table counts for verification")
                return False
                
            # Compare counts
            all_match = True
            for table in railway_counts:
                local_count = local_counts.get(table, 0)
                railway_count = railway_counts[table]
                
                if local_count == railway_count:
                    logger.info(f"✅ {table}: {local_count} rows (matches)")
                else:
                    logger.error(f"❌ {table}: Local={local_count}, Railway={railway_count} (MISMATCH)")
                    all_match = False
            
            if all_match:
                logger.info("✅ Mirror verification successful - all table counts match!")
            else:
                logger.error("❌ Mirror verification failed - table count mismatches detected")
                
            return all_match
            
        except Exception as e:
            logger.error(f"❌ Verification error: {e}")
            return False
    
    def get_table_counts(self, db_url):
        """Get row counts for all tables in a database"""
        try:
            params = parse_db_url(db_url)
            if 'railway' in db_url:
                params['connect_timeout'] = 30
                
            conn = psycopg2.connect(**params)
            table_counts = {}
            
            with conn.cursor() as cursor:
                # Get all table names
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
                
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
    
    def mirror_database(self):
        """Execute the complete database mirroring process"""
        logger.info("🚀 Starting Railway database mirror process...")
        
        # Step 1: Test connections
        if not self.test_connections():
            logger.error("❌ Connection tests failed. Aborting mirror process.")
            return False
        
        # Step 2: Get Railway migration version
        railway_version = self.get_railway_migration_version()
        
        # Step 3: Backup local database
        backup_file = self.backup_local_database()
        if not backup_file:
            logger.error("❌ Failed to backup local database. Aborting for safety.")
            return False
        
        # Step 4: Dump Railway database
        dump_file = self.dump_railway_database()
        if not dump_file:
            logger.error("❌ Failed to dump Railway database. Aborting.")
            return False
        
        # Step 5: Drop and recreate local database
        if not self.drop_and_recreate_local_database():
            logger.error("❌ Failed to recreate local database. Aborting.")
            return False
        
        # Step 6: Restore Railway dump to local
        if not self.restore_railway_dump_to_local(dump_file):
            logger.error("❌ Failed to restore Railway dump. Aborting.")
            return False
        
        # Step 7: Sync Alembic migration state
        if not self.sync_alembic_migration_state(railway_version):
            logger.error("❌ Failed to sync Alembic state. Manual intervention may be needed.")
            # Don't return False here as the data mirror may still be successful
        
        # Step 8: Verify mirror success
        if not self.verify_mirror_success():
            logger.error("❌ Mirror verification failed. Check logs for details.")
            return False
        
        # Cleanup
        try:
            os.remove(dump_file)
            logger.info(f"Cleaned up temporary dump file: {dump_file}")
        except:
            pass
        
        logger.info("🎉 Railway database mirror completed successfully!")
        logger.info(f"📁 Local backup created: {backup_file}")
        logger.info("🔄 Local database now matches Railway exactly (schema + data)")
        
        return True

def main():
    """Main function"""
    print("Railway Database Mirror Tool")
    print("=" * 50)
    
    mirror = DatabaseMirror()
    
    # Confirm with user
    response = input("\n⚠️  This will REPLACE your local database with Railway data. Continue? (y/N): ")
    if response.lower() not in ['y', 'yes']:
        print("Operation cancelled by user.")
        return
    
    # Create logs directory if it doesn't exist
    os.makedirs("../../../logs", exist_ok=True)
    
    # Execute mirror
    success = mirror.mirror_database()
    
    if success:
        print("\n✅ Database mirror completed successfully!")
        print("Your local database now exactly matches Railway.")
    else:
        print("\n❌ Database mirror failed. Check logs for details.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 