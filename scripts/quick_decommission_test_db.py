#!/usr/bin/env python3
"""
Quick decommission of the local test database to prevent accidental usage.

This script will simply rename the test database to prevent accidental connections.
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

def quick_decommission_test_database():
    """Quickly decommission the test database by renaming it"""
    
    try:
        # Connect to main database to perform the rename
        os.environ["RALLY_DATABASE"] = "main"
        main_conn = psycopg2.connect(get_db_url())
        main_cursor = main_conn.cursor()
        
        # Check if test database exists
        main_cursor.execute("""
            SELECT datname FROM pg_database 
            WHERE datname = 'rally_test'
        """)
        
        if not main_cursor.fetchone():
            logger.info("✅ Test database 'rally_test' does not exist - already decommissioned")
            return
        
        # Create backup name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_db_name = f"rally_test_backup_{timestamp}"
        
        logger.info(f"🔄 Renaming test database to '{backup_db_name}'...")
        
        # Terminate all connections to test database first
        main_cursor.execute("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = 'rally_test'
            AND pid <> pg_backend_pid()
        """)
        
        # Rename the test database
        main_cursor.execute(f"ALTER DATABASE rally_test RENAME TO {backup_db_name}")
        logger.info(f"✅ Test database renamed to '{backup_db_name}' successfully")
        
        # Add a comment to the backup database
        main_cursor.execute(f"""
            COMMENT ON DATABASE {backup_db_name} IS 
            'DECOMMISSIONED: This database was decommissioned to prevent accidental usage. 
            Original name: rally_test. Decommissioned on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        """)
        
        main_cursor.close()
        main_conn.close()
        
        logger.info("🎉 Test database decommissioning completed successfully!")
        logger.info(f"📦 Backup available as: {backup_db_name}")
        logger.info("⚠️  The test database is no longer accessible via RALLY_DATABASE=test")
        
    except Exception as e:
        logger.error(f"❌ Error during decommissioning: {e}")
        raise

def main():
    """Main function"""
    logger.info("🔧 Starting quick test database decommissioning...")
    
    # Confirm with user
    response = input("Are you sure you want to decommission the test database? (yes/no): ")
    if response.lower() != "yes":
        logger.info("❌ Decommissioning cancelled by user")
        return
    
    quick_decommission_test_database()
    logger.info("✅ Quick decommissioning completed!")

if __name__ == "__main__":
    main() 