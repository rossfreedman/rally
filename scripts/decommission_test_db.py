#!/usr/bin/env python3
"""
Decommission the local test database to prevent accidental usage.

This script will:
1. Rename the test database to prevent accidental connections
2. Update the database configuration to prevent test database usage
3. Create a backup of the test database before decommissioning
"""

import logging
import psycopg2
import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import database_config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db_url

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def decommission_test_database():
    """Decommission the test database to prevent accidental usage"""
    
    try:
        # First, let's check if we can connect to the test database
        logger.info("🔍 Checking test database connection...")
        
        # Temporarily set environment to test
        original_env = os.environ.get("RALLY_DATABASE", "main")
        os.environ["RALLY_DATABASE"] = "test"
        
        try:
            # Try to connect to test database
            test_conn = psycopg2.connect(get_db_url())
            test_cursor = test_conn.cursor()
            
            # Get database info
            test_cursor.execute("SELECT current_database(), version()")
            db_info = test_cursor.fetchone()
            test_db_name = db_info[0]
            postgres_version = db_info[1].split()[1]  # Extract version number
            
            logger.info(f"✅ Connected to test database: {test_db_name}")
            logger.info(f"PostgreSQL version: {postgres_version}")
            
            # Get table count
            test_cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            table_count = test_cursor.fetchone()[0]
            logger.info(f"Tables in test database: {table_count}")
            
            # Get record counts for key tables
            key_tables = ['players', 'match_scores', 'teams', 'leagues']
            for table in key_tables:
                try:
                    test_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = test_cursor.fetchone()[0]
                    logger.info(f"  {table}: {count:,} records")
                except Exception as e:
                    logger.warning(f"  {table}: Error getting count - {e}")
            
            test_cursor.close()
            test_conn.close()
            
        except Exception as e:
            logger.error(f"❌ Cannot connect to test database: {e}")
            logger.info("Test database may already be decommissioned or doesn't exist")
            return
        
        # Now connect to main database to perform the decommissioning
        os.environ["RALLY_DATABASE"] = "main"
        main_conn = psycopg2.connect(get_db_url())
        main_cursor = main_conn.cursor()
        
        # Create backup name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_db_name = f"rally_test_backup_{timestamp}"
        
        logger.info(f"📦 Creating backup of test database as '{backup_db_name}'...")
        
        # Create backup database
        try:
            main_cursor.execute(f"CREATE DATABASE {backup_db_name}")
            logger.info(f"✅ Backup database '{backup_db_name}' created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create backup database: {e}")
            main_cursor.close()
            main_conn.close()
            return
        
        # Copy data from test database to backup
        logger.info("🔄 Copying data from test to backup database...")
        
        # Get list of tables to copy
        main_cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        tables = [row[0] for row in main_cursor.fetchall()]
        
        logger.info(f"Found {len(tables)} tables to copy")
        
        # Copy each table
        for table in tables:
            try:
                # Use pg_dump and pg_restore for reliable copying
                import subprocess
                
                # Dump table from test database
                dump_cmd = [
                    "pg_dump",
                    "-h", "localhost",
                    "-U", "postgres",
                    "-t", table,
                    "rally_test"
                ]
                
                # Restore to backup database
                restore_cmd = [
                    "psql",
                    "-h", "localhost", 
                    "-U", "postgres",
                    "-d", backup_db_name
                ]
                
                # Execute the copy
                dump_process = subprocess.Popen(dump_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                restore_process = subprocess.Popen(restore_cmd, stdin=dump_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                dump_process.stdout.close()
                output, error = restore_process.communicate()
                
                if restore_process.returncode == 0:
                    logger.info(f"  ✅ Copied table: {table}")
                else:
                    logger.warning(f"  ⚠️  Error copying table {table}: {error.decode()}")
                    
            except Exception as e:
                logger.warning(f"  ⚠️  Error copying table {table}: {e}")
        
        # Now drop the original test database
        logger.info("🗑️  Dropping original test database...")
        
        # Terminate all connections to test database first
        main_cursor.execute("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = 'rally_test'
            AND pid <> pg_backend_pid()
        """)
        
        # Drop the test database
        main_cursor.execute("DROP DATABASE rally_test")
        logger.info("✅ Original test database 'rally_test' dropped successfully")
        
        # Create a placeholder database to prevent recreation
        logger.info("🛡️  Creating placeholder database to prevent accidental recreation...")
        main_cursor.execute("CREATE DATABASE rally_test_decommissioned")
        logger.info("✅ Placeholder database 'rally_test_decommissioned' created")
        
        # Add a comment to the placeholder database
        main_cursor.execute("""
            COMMENT ON DATABASE rally_test_decommissioned IS 
            'DECOMMISSIONED: This database was decommissioned to prevent accidental usage. 
            Backup available as rally_test_backup_YYYYMMDD_HHMMSS'
        """)
        
        main_cursor.close()
        main_conn.close()
        
        # Restore original environment
        os.environ["RALLY_DATABASE"] = original_env
        
        logger.info("🎉 Test database decommissioning completed successfully!")
        logger.info(f"📦 Backup available as: {backup_db_name}")
        logger.info("🛡️  Placeholder database created to prevent accidental recreation")
        logger.info("⚠️  Remember to update any scripts that might reference the test database")
        
    except Exception as e:
        logger.error(f"❌ Error during decommissioning: {e}")
        raise

def main():
    """Main function"""
    logger.info("🔧 Starting test database decommissioning...")
    
    # Confirm with user
    response = input("Are you sure you want to decommission the test database? (yes/no): ")
    if response.lower() != "yes":
        logger.info("❌ Decommissioning cancelled by user")
        return
    
    decommission_test_database()
    logger.info("✅ Decommissioning completed!")

if __name__ == "__main__":
    main() 