#!/usr/bin/env python3
"""
Clone Production Database to Local
==================================

This script clones the production database to the local development environment.
It will OVERWRITE the local database with production data.

⚠️  WARNING: This will completely replace your local database!
⚠️  Make sure to backup your local data if needed before running this script.

Usage:
    python data/clone/clone_production_to_local.py

Requirements:
    - pg_dump and psql must be installed and in PATH
    - Network access to production database
    - Local PostgreSQL server running
"""

import os
import sys
import subprocess
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database URLs
PRODUCTION_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"
LOCAL_URL = "postgresql://postgres:postgres@localhost:5432/rally"

def run_command(cmd, description):
    """Run a command and handle errors"""
    logger.info(f"🔄 {description}")
    logger.debug(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"✅ {description} - Success")
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} - Failed")
        logger.error(f"Command: {' '.join(cmd)}")
        logger.error(f"Return code: {e.returncode}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        raise

def check_dependencies():
    """Check if required tools are available"""
    logger.info("🔍 Checking dependencies...")
    
    # Check pg_dump
    try:
        subprocess.run(['pg_dump', '--version'], check=True, capture_output=True)
        logger.info("✅ pg_dump is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("❌ pg_dump not found. Please install PostgreSQL client tools.")
        sys.exit(1)
    
    # Check psql
    try:
        subprocess.run(['psql', '--version'], check=True, capture_output=True)
        logger.info("✅ psql is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("❌ psql not found. Please install PostgreSQL client tools.")
        sys.exit(1)

def test_connections():
    """Test database connections"""
    logger.info("🔍 Testing database connections...")
    
    # Test production connection
    try:
        cmd = ['psql', PRODUCTION_URL, '-c', 'SELECT 1;']
        run_command(cmd, "Testing production database connection")
        logger.info("✅ Production database connection successful")
    except subprocess.CalledProcessError:
        logger.error("❌ Cannot connect to production database")
        logger.error("Please check your network connection and database URL")
        sys.exit(1)
    
    # Test local connection
    try:
        cmd = ['psql', LOCAL_URL, '-c', 'SELECT 1;']
        run_command(cmd, "Testing local database connection")
        logger.info("✅ Local database connection successful")
    except subprocess.CalledProcessError:
        logger.error("❌ Cannot connect to local database")
        logger.error("Please ensure PostgreSQL is running locally and the database exists")
        sys.exit(1)

def create_backup():
    """Create a backup of the current local database"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"data/backups/local_backup_before_prod_clone_{timestamp}.sql"
    
    logger.info(f"💾 Creating backup of local database to {backup_file}")
    
    # Ensure backup directory exists
    os.makedirs(os.path.dirname(backup_file), exist_ok=True)
    
    try:
        cmd = ['pg_dump', LOCAL_URL, '-f', backup_file]
        run_command(cmd, f"Creating local database backup")
        logger.info(f"✅ Local database backed up to {backup_file}")
        return backup_file
    except subprocess.CalledProcessError:
        logger.warning("⚠️  Failed to create backup, but continuing with clone...")
        return None

def drop_and_recreate_local_db():
    """Drop and recreate the local database"""
    logger.info("🗑️  Dropping and recreating local database...")
    
    # Connect to postgres database to drop/recreate rally database
    postgres_url = LOCAL_URL.replace('/rally', '/postgres')
    
    # First, terminate all connections to the rally database
    try:
        logger.info("🔌 Terminating active connections to rally database...")
        cmd = ['psql', postgres_url, '-c', '''
            SELECT pg_terminate_backend(pid) 
            FROM pg_stat_activity 
            WHERE datname = 'rally' AND pid <> pg_backend_pid();
        ''']
        run_command(cmd, "Terminating active connections to rally database")
        logger.info("✅ Active connections terminated")
    except subprocess.CalledProcessError:
        logger.warning("⚠️  Failed to terminate connections, but continuing...")
    
    # Drop database if it exists
    try:
        cmd = ['psql', postgres_url, '-c', 'DROP DATABASE IF EXISTS rally;']
        run_command(cmd, "Dropping existing local database")
    except subprocess.CalledProcessError:
        logger.warning("⚠️  Failed to drop database, but continuing...")
    
    # Create new database
    try:
        cmd = ['psql', postgres_url, '-c', 'CREATE DATABASE rally;']
        run_command(cmd, "Creating new local database")
        logger.info("✅ Local database recreated successfully")
    except subprocess.CalledProcessError:
        logger.error("❌ Failed to create local database")
        sys.exit(1)

def clone_database():
    """Clone production database to local"""
    logger.info("📥 Cloning production database to local...")
    
    # Use pg_dump to export from production and pipe to psql to import to local
    dump_cmd = ['pg_dump', PRODUCTION_URL, '--no-owner', '--no-privileges', '--clean', '--if-exists']
    import_cmd = ['psql', LOCAL_URL]
    
    try:
        # Pipe pg_dump output to psql
        dump_process = subprocess.Popen(dump_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        import_process = subprocess.Popen(import_cmd, stdin=dump_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        dump_process.stdout.close()
        stdout, stderr = import_process.communicate()
        
        if import_process.returncode != 0:
            logger.error("❌ Database clone failed")
            logger.error(f"STDERR: {stderr.decode()}")
            sys.exit(1)
        
        logger.info("✅ Database clone completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Database clone failed: {e}")
        sys.exit(1)

def verify_clone():
    """Verify the clone was successful"""
    logger.info("🔍 Verifying database clone...")
    
    try:
        # Check if we can connect and get basic info
        cmd = ['psql', LOCAL_URL, '-c', 'SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = \'public\';']
        result = run_command(cmd, "Counting tables in local database")
        
        # Extract table count from output
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if line.strip().isdigit():
                table_count = int(line.strip())
                logger.info(f"✅ Local database has {table_count} tables")
                break
        
        # Check for some key tables
        key_tables = ['users', 'players', 'teams', 'leagues', 'match_scores']
        table_list = ','.join([f"'{t}'" for t in key_tables])
        cmd = ['psql', LOCAL_URL, '-c', f"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ({table_list});"]
        result = run_command(cmd, "Checking for key tables")
        
        found_tables = [line.strip() for line in result.stdout.split('\n') if line.strip() and not line.startswith('table_name')]
        logger.info(f"✅ Found key tables: {found_tables}")
        
        logger.info("✅ Database clone verification successful")
        
    except subprocess.CalledProcessError as e:
        logger.error("❌ Database clone verification failed")
        logger.error(f"Error: {e.stderr}")
        sys.exit(1)

def main():
    """Main function"""
    logger.info("🚀 Starting production to local database clone")
    logger.info("=" * 50)
    
    # Safety check
    logger.warning("⚠️  WARNING: This will completely replace your local database!")
    logger.warning("⚠️  Make sure you have backed up any important local data.")
    logger.warning("⚠️  IMPORTANT: Stop your development server before running this script!")
    logger.warning("⚠️  (Press Ctrl+C to stop the server, then run this script)")
    
    response = input("\nDo you want to continue? (yes/no): ").lower().strip()
    if response not in ['yes', 'y']:
        logger.info("❌ Operation cancelled by user")
        sys.exit(0)
    
    try:
        # Step 1: Check dependencies
        check_dependencies()
        
        # Step 2: Test connections
        test_connections()
        
        # Step 3: Create backup
        backup_file = create_backup()
        
        # Step 4: Drop and recreate local database
        drop_and_recreate_local_db()
        
        # Step 5: Clone database
        clone_database()
        
        # Step 6: Verify clone
        verify_clone()
        
        logger.info("🎉 Production to local database clone completed successfully!")
        logger.info("=" * 50)
        logger.info("Next steps:")
        logger.info("1. Start your local development server")
        logger.info("2. Verify the application works with production data")
        if backup_file:
            logger.info(f"3. Your previous local data was backed up to: {backup_file}")
        
    except KeyboardInterrupt:
        logger.info("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
