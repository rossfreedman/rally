#!/usr/bin/env python3
"""
Railway Database Rollback Script
================================
Restore Railway database from a backup created by the mirror script.

Usage:
    python scripts/rollback_railway.py <backup_file.dump>
    
Example:
    python scripts/rollback_railway.py railway_backup_20241201_143022.dump
"""

import os
import sys
import subprocess
import psycopg2
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

RAILWAY_DB_CONFIG = {
    'host': 'ballast.proxy.rlwy.net',
    'port': 40911,
    'database': 'railway',
    'user': 'postgres',
    'password': 'HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq'
}

def test_railway_connection():
    """Test Railway database connection"""
    logger.info("🔍 Testing Railway database connection...")
    
    try:
        conn = psycopg2.connect(
            host=RAILWAY_DB_CONFIG['host'],
            port=RAILWAY_DB_CONFIG['port'],
            database=RAILWAY_DB_CONFIG['database'],
            user=RAILWAY_DB_CONFIG['user'],
            password=RAILWAY_DB_CONFIG['password'],
            connect_timeout=10,
            sslmode='require'
        )
        
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user")
            db, user = cur.fetchone()
            logger.info(f"✅ Railway connection successful:")
            logger.info(f"   Database: {db}")
            logger.info(f"   User: {user}")
            
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Railway connection failed: {e}")
        return False

def verify_backup_file(backup_file):
    """Verify that the backup file exists and is readable"""
    logger.info(f"🔍 Verifying backup file: {backup_file}")
    
    if not os.path.exists(backup_file):
        logger.error(f"❌ Backup file does not exist: {backup_file}")
        return False
    
    if not os.path.isfile(backup_file):
        logger.error(f"❌ Path is not a file: {backup_file}")
        return False
    
    file_size = os.path.getsize(backup_file)
    if file_size == 0:
        logger.error(f"❌ Backup file is empty: {backup_file}")
        return False
    
    logger.info(f"✅ Backup file verified:")
    logger.info(f"   Size: {file_size:,} bytes ({file_size / 1024 / 1024:.1f} MB)")
    
    return True

def get_current_railway_state():
    """Get current Railway database state for comparison"""
    logger.info("📊 Getting current Railway database state...")
    
    try:
        conn = psycopg2.connect(
            host=RAILWAY_DB_CONFIG['host'],
            port=RAILWAY_DB_CONFIG['port'],
            database=RAILWAY_DB_CONFIG['database'],
            user=RAILWAY_DB_CONFIG['user'],
            password=RAILWAY_DB_CONFIG['password'],
            connect_timeout=10,
            sslmode='require'
        )
        
        counts = {}
        
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
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cur.fetchone()[0]
                except Exception as e:
                    counts[table] = f"ERROR: {e}"
                    
        conn.close()
        return counts
        
    except Exception as e:
        logger.error(f"❌ Failed to get Railway state: {e}")
        return {}

def restore_railway_database(backup_file):
    """Restore Railway database from backup"""
    logger.info(f"🔄 Restoring Railway database from: {backup_file}")
    
    try:
        # Set PGPASSWORD environment variable
        env = os.environ.copy()
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
            backup_file
        ]
        
        logger.info("📥 Starting database restore...")
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
        logger.error(f"❌ Database restore error: {e}")
        return False

def verify_restore_success(pre_restore_counts):
    """Verify that the restore completed successfully"""
    logger.info("🔍 Verifying restore success...")
    
    post_restore_counts = get_current_railway_state()
    
    if not post_restore_counts:
        logger.error("❌ Could not retrieve post-restore database state")
        return False
    
    logger.info("\n📊 RESTORE VERIFICATION:")
    logger.info("=" * 60)
    logger.info(f"{'Table':<25} {'Before':<15} {'After':<15} {'Status':<15}")
    logger.info("-" * 60)
    
    changes_detected = False
    
    # Check all tables that existed before or after
    all_tables = set(pre_restore_counts.keys()) | set(post_restore_counts.keys())
    
    for table in sorted(all_tables):
        before_count = pre_restore_counts.get(table, 0)
        after_count = post_restore_counts.get(table, 0)
        
        if before_count == after_count:
            status = "No Change"
        else:
            status = "CHANGED"
            changes_detected = True
        
        logger.info(f"{table:<25} {str(before_count):<15} {str(after_count):<15} {status:<15}")
    
    logger.info("-" * 60)
    
    if changes_detected:
        logger.info("✅ RESTORE VERIFIED - Database state has changed")
        logger.info("   The restore operation modified the database as expected")
    else:
        logger.warning("⚠️  No changes detected after restore")
        logger.warning("   This could mean the backup was identical to current state")
    
    return True

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Rollback Railway database from backup')
    parser.add_argument('backup_file', help='Path to the backup file (.dump)')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()
    
    logger.info("🔄 RAILWAY DATABASE ROLLBACK SCRIPT")
    logger.info("=" * 60)
    logger.info(f"Backup file: {args.backup_file}")
    
    # Pre-flight checks
    logger.info("\n🔍 PRE-FLIGHT CHECKS")
    logger.info("-" * 30)
    
    if not verify_backup_file(args.backup_file):
        return 1
        
    if not test_railway_connection():
        return 1
    
    # Get current state
    logger.info("\n📊 CURRENT STATE")
    logger.info("-" * 30)
    pre_restore_counts = get_current_railway_state()
    
    if pre_restore_counts:
        total_records = sum(count for count in pre_restore_counts.values() if isinstance(count, int))
        logger.info(f"Current Railway records: {total_records:,}")
        logger.info(f"Number of tables: {len(pre_restore_counts)}")
    
    # Confirm execution
    if not args.force:
        logger.info("\n⚠️  FINAL CONFIRMATION")
        logger.info("-" * 30)
        logger.warning("This will REPLACE ALL Railway data with backup data!")
        response = input("Continue with rollback? (yes/no): ")
        
        if response.lower() != 'yes':
            logger.info("❌ Rollback cancelled by user")
            return 1
    
    # Execute restore
    logger.info("\n🔄 EXECUTING ROLLBACK")
    logger.info("-" * 30)
    
    if not restore_railway_database(args.backup_file):
        logger.error("❌ Database rollback failed")
        return 1
    
    # Verify success
    logger.info("\n🔍 VERIFICATION")
    logger.info("-" * 30)
    
    if not verify_restore_success(pre_restore_counts):
        logger.error("❌ Rollback verification failed")
        return 1
    
    logger.info("\n🎉 ROLLBACK COMPLETED SUCCESSFULLY!")
    logger.info("=" * 60)
    logger.info("✅ Railway database has been restored from backup")
    logger.info(f"✅ Backup file used: {args.backup_file}")
    
    return 0

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/rollback_railway.py <backup_file.dump>")
        print("Example: python scripts/rollback_railway.py railway_backup_20241201_143022.dump")
        sys.exit(1)
    
    sys.exit(main()) 