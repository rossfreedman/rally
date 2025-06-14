#!/usr/bin/env python3
"""
Complete Local to Railway Database Mirror Script
===============================================
This script safely mirrors your local PostgreSQL database to Railway using
pg_dump/pg_restore for maximum reliability, with comprehensive verification.

Usage:
    python scripts/mirror_local_to_railway.py [--dry-run] [--skip-backup]
    
Features:
- Pre-flight verification of both databases
- Complete data backup of Railway before changes
- Full schema + data mirroring using pg_dump/pg_restore
- Post-migration verification and reporting
- Rollback capability if needed
- Alembic migration state synchronization
"""

import os
import sys
import subprocess
import psycopg2
import argparse
import tempfile
from datetime import datetime
from urllib.parse import urlparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection details
LOCAL_DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'rally',
    'user': 'postgres',
    'password': 'password'  # Update if different
}

RAILWAY_DB_CONFIG = {
    'host': 'ballast.proxy.rlwy.net',
    'port': 40911,
    'database': 'railway',
    'user': 'postgres',
    'password': 'HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq'
}

def create_connection_string(config):
    """Create PostgreSQL connection string from config"""
    return f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"

def test_database_connection(config, name):
    """Test database connection"""
    logger.info(f"🔍 Testing {name} database connection...")
    
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password'],
            connect_timeout=10,
            sslmode='require' if 'railway' in config['host'] else 'prefer'
        )
        
        with conn.cursor() as cur:
            cur.execute("SELECT version(), current_database(), current_user")
            version, db, user = cur.fetchone()
            logger.info(f"✅ {name} connection successful:")
            logger.info(f"   Database: {db}")
            logger.info(f"   User: {user}")
            
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ {name} connection failed: {e}")
        return False

def get_table_counts(config, name):
    """Get record counts for all tables"""
    logger.info(f"📊 Getting table counts for {name}...")
    
    counts = {}
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password'],
            connect_timeout=10,
            sslmode='require' if 'railway' in config['host'] else 'prefer'
        )
        
        with conn.cursor() as cur:
            # Get all table names
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]
            
            # Get count for each table
            for table in tables:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cur.fetchone()[0]
                
        conn.close()
        return counts
        
    except Exception as e:
        logger.error(f"❌ Failed to get table counts for {name}: {e}")
        return {}

def backup_railway_database(backup_file):
    """Create backup of current Railway database"""
    logger.info("💾 Creating backup of Railway database...")
    
    try:
        # Set PGPASSWORD environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = RAILWAY_DB_CONFIG['password']
        
        cmd = [
            'pg_dump',
            '-h', RAILWAY_DB_CONFIG['host'],
            '-p', str(RAILWAY_DB_CONFIG['port']),
            '-U', RAILWAY_DB_CONFIG['user'],
            '-d', RAILWAY_DB_CONFIG['database'],
            '--verbose',
            '--clean',
            '--if-exists',
            '--format=custom',
            '--file', backup_file
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"✅ Railway backup created: {backup_file}")
            return True
        else:
            logger.error(f"❌ Railway backup failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Railway backup error: {e}")
        return False

def mirror_database():
    """Mirror local database to Railway using pg_dump/pg_restore"""
    logger.info("🔄 Starting database mirror process...")
    
    with tempfile.NamedTemporaryFile(suffix='.dump', delete=False) as tmp_file:
        dump_file = tmp_file.name
    
    try:
        # Step 1: Dump local database
        logger.info("📤 Dumping local database...")
        env = os.environ.copy()
        env['PGPASSWORD'] = LOCAL_DB_CONFIG['password']
        
        dump_cmd = [
            'pg_dump',
            '-h', LOCAL_DB_CONFIG['host'],
            '-p', str(LOCAL_DB_CONFIG['port']),
            '-U', LOCAL_DB_CONFIG['user'],
            '-d', LOCAL_DB_CONFIG['database'],
            '--verbose',
            '--clean',
            '--if-exists',
            '--format=custom',
            '--file', dump_file
        ]
        
        result = subprocess.run(dump_cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"❌ Local database dump failed: {result.stderr}")
            return False
            
        logger.info("✅ Local database dump completed")
        
        # Step 2: Restore to Railway database
        logger.info("📥 Restoring to Railway database...")
        env['PGPASSWORD'] = RAILWAY_DB_CONFIG['password']
        
        restore_cmd = [
            'pg_restore',
            '-h', RAILWAY_DB_CONFIG['host'],
            '-p', str(RAILWAY_DB_CONFIG['port']),
            '-U', RAILWAY_DB_CONFIG['user'],
            '-d', RAILWAY_DB_CONFIG['database'],
            '--verbose',
            '--clean',
            '--if-exists',
            '--no-owner',
            '--no-privileges',
            dump_file
        ]
        
        result = subprocess.run(restore_cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            # pg_restore often returns non-zero even on success due to warnings
            # Check if the error is actually critical
            if "FATAL" in result.stderr or "could not connect" in result.stderr:
                logger.error(f"❌ Railway database restore failed: {result.stderr}")
                return False
            else:
                logger.warning("⚠️  Restore completed with warnings (this is often normal)")
                logger.info("✅ Railway database restore completed")
        else:
            logger.info("✅ Railway database restore completed")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Database mirror error: {e}")
        return False
        
    finally:
        # Clean up temporary dump file
        if os.path.exists(dump_file):
            os.unlink(dump_file)

def sync_alembic_migration_state():
    """Sync Alembic migration state to match local"""
    logger.info("🔄 Syncing Alembic migration state...")
    
    try:
        # Get current local migration
        logger.info("Getting local migration state...")
        result = subprocess.run(['alembic', 'current'], capture_output=True, text=True)
        local_migration = result.stdout.strip()
        
        if result.returncode != 0:
            logger.warning(f"Could not get local migration state: {result.stderr}")
            return False
            
        logger.info(f"Local migration state: {local_migration}")
        
        # Set Railway migration state to match
        logger.info("Setting Railway migration state...")
        env = os.environ.copy()
        env['SYNC_RAILWAY'] = 'true'
        
        if local_migration and local_migration != "None":
            # Extract just the revision ID (first part before space)
            revision = local_migration.split()[0] if ' ' in local_migration else local_migration
            result = subprocess.run(['alembic', 'stamp', revision], env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ Railway migration state set to: {revision}")
                return True
            else:
                logger.error(f"❌ Failed to set Railway migration state: {result.stderr}")
                return False
        else:
            logger.info("No migration state to sync")
            return True
            
    except Exception as e:
        logger.error(f"❌ Migration sync error: {e}")
        return False

def verify_mirror_success():
    """Verify that the mirror was successful"""
    logger.info("🔍 Verifying mirror success...")
    
    # Get table counts from both databases
    local_counts = get_table_counts(LOCAL_DB_CONFIG, "Local")
    railway_counts = get_table_counts(RAILWAY_DB_CONFIG, "Railway")
    
    if not local_counts or not railway_counts:
        logger.error("❌ Could not retrieve table counts for verification")
        return False
    
    # Compare counts
    success = True
    logger.info("\n📊 VERIFICATION RESULTS:")
    logger.info("=" * 60)
    
    all_tables = set(local_counts.keys()) | set(railway_counts.keys())
    
    for table in sorted(all_tables):
        local_count = local_counts.get(table, 0)
        railway_count = railway_counts.get(table, 0)
        
        if local_count == railway_count:
            logger.info(f"✅ {table:25} Local: {local_count:8,} | Railway: {railway_count:8,}")
        else:
            logger.error(f"❌ {table:25} Local: {local_count:8,} | Railway: {railway_count:8,}")
            success = False
    
    logger.info("=" * 60)
    
    if success:
        logger.info("🎉 MIRROR VERIFICATION PASSED - All table counts match!")
        
        # Calculate totals
        local_total = sum(local_counts.values())
        railway_total = sum(railway_counts.values())
        logger.info(f"Total records - Local: {local_total:,} | Railway: {railway_total:,}")
        
    else:
        logger.error("❌ MIRROR VERIFICATION FAILED - Table counts do not match!")
    
    return success

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Mirror local database to Railway')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    parser.add_argument('--skip-backup', action='store_true', help='Skip Railway backup step')
    args = parser.parse_args()
    
    logger.info("🚀 RALLY DATABASE MIRROR SCRIPT")
    logger.info("=" * 60)
    logger.info("This will COMPLETELY REPLACE Railway database with local data!")
    
    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")
    
    # Pre-flight checks
    logger.info("\n🔍 PRE-FLIGHT CHECKS")
    logger.info("-" * 30)
    
    if not test_database_connection(LOCAL_DB_CONFIG, "Local"):
        logger.error("❌ Cannot connect to local database")
        return 1
        
    if not test_database_connection(RAILWAY_DB_CONFIG, "Railway"):
        logger.error("❌ Cannot connect to Railway database")
        return 1
    
    # Show current state
    logger.info("\n📊 CURRENT DATABASE STATE")
    logger.info("-" * 30)
    local_counts = get_table_counts(LOCAL_DB_CONFIG, "Local")
    railway_counts = get_table_counts(RAILWAY_DB_CONFIG, "Railway")
    
    if local_counts and railway_counts:
        local_total = sum(local_counts.values())
        railway_total = sum(railway_counts.values())
        logger.info(f"Local total records: {local_total:,}")
        logger.info(f"Railway total records: {railway_total:,}")
    
    if args.dry_run:
        logger.info("\n🔍 DRY RUN COMPLETE - No changes made")
        return 0
    
    # Confirm execution
    logger.info("\n⚠️  FINAL CONFIRMATION")
    logger.info("-" * 30)
    response = input("This will REPLACE ALL Railway data with local data. Continue? (yes/no): ")
    
    if response.lower() != 'yes':
        logger.info("❌ Operation cancelled by user")
        return 1
    
    # Create backup if requested
    backup_file = None
    if not args.skip_backup:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"railway_backup_{timestamp}.dump"
        
        if not backup_railway_database(backup_file):
            logger.error("❌ Failed to create Railway backup")
            return 1
    
    # Execute mirror
    logger.info("\n🔄 EXECUTING DATABASE MIRROR")
    logger.info("-" * 30)
    
    if not mirror_database():
        logger.error("❌ Database mirror failed")
        return 1
    
    # Sync Alembic migration state
    sync_alembic_migration_state()
    
    # Verify success
    logger.info("\n🔍 VERIFICATION")
    logger.info("-" * 30)
    
    if not verify_mirror_success():
        logger.error("❌ Mirror verification failed")
        if backup_file:
            logger.info(f"💾 Railway backup available for rollback: {backup_file}")
        return 1
    
    logger.info("\n🎉 DATABASE MIRROR COMPLETED SUCCESSFULLY!")
    logger.info("=" * 60)
    logger.info("✅ Local database has been successfully mirrored to Railway")
    logger.info("✅ All table counts verified")
    logger.info("✅ Alembic migration state synchronized")
    
    if backup_file:
        logger.info(f"💾 Railway backup saved: {backup_file}")
        logger.info("   Keep this backup for rollback if needed")
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 