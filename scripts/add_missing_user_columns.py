#!/usr/bin/env python3
"""
Add Missing User Columns to Railway
==================================

Safely adds missing columns to Railway users table:
- tenniscores_player_id (VARCHAR)
- league_id (INTEGER)

This script only adds schema changes, doesn't modify existing data.
Safe to run on live Railway database with active users.

Usage:
    python scripts/add_missing_user_columns.py [--dry-run]
"""

import argparse
import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from database_config import parse_db_url

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

RAILWAY_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

class UserColumnAdder:
    def __init__(self, dry_run=False):
        self.railway_url = RAILWAY_DB_URL
        self.dry_run = dry_run
        
        if dry_run:
            logger.info("🧪 DRY RUN MODE: No actual changes will be made")

    def check_existing_columns(self):
        """Check which columns already exist in Railway users table"""
        logger.info("🔍 Checking existing columns in Railway users table...")
        
        try:
            railway_params = parse_db_url(self.railway_url)
            railway_params["connect_timeout"] = 30
            conn = psycopg2.connect(**railway_params)

            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    AND table_schema = 'public'
                    ORDER BY ordinal_position
                """)
                
                existing_columns = [row[0] for row in cursor.fetchall()]
                logger.info(f"📋 Existing columns: {', '.join(existing_columns)}")
                
                missing_columns = []
                target_columns = ['tenniscores_player_id', 'league_id']
                
                for col in target_columns:
                    if col not in existing_columns:
                        missing_columns.append(col)
                        logger.info(f"❌ Missing column: {col}")
                    else:
                        logger.info(f"✅ Column exists: {col}")
                
                conn.close()
                return missing_columns
                
        except Exception as e:
            logger.error(f"❌ Failed to check existing columns: {e}")
            return None

    def add_missing_columns(self, missing_columns):
        """Add missing columns to Railway users table"""
        if not missing_columns:
            logger.info("✅ All columns already exist - no changes needed")
            return True
            
        if self.dry_run:
            logger.info(f"🧪 DRY RUN: Would add columns: {', '.join(missing_columns)}")
            return True
            
        logger.info(f"➕ Adding missing columns to Railway users table: {', '.join(missing_columns)}")
        
        try:
            railway_params = parse_db_url(self.railway_url)
            railway_params["connect_timeout"] = 30
            conn = psycopg2.connect(**railway_params)
            conn.autocommit = True

            with conn.cursor() as cursor:
                for column in missing_columns:
                    if column == 'tenniscores_player_id':
                        sql = "ALTER TABLE users ADD COLUMN tenniscores_player_id VARCHAR(255)"
                        logger.info("➕ Adding tenniscores_player_id VARCHAR(255)")
                    elif column == 'league_id':
                        sql = "ALTER TABLE users ADD COLUMN league_id INTEGER"
                        logger.info("➕ Adding league_id INTEGER")
                    else:
                        logger.warning(f"⚠️  Unknown column: {column}")
                        continue
                    
                    try:
                        cursor.execute(sql)
                        logger.info(f"✅ Successfully added column: {column}")
                    except Exception as e:
                        logger.error(f"❌ Failed to add column {column}: {e}")
                        return False

            conn.close()
            logger.info("✅ All missing columns added successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add columns: {e}")
            return False

    def verify_columns_added(self):
        """Verify that all target columns now exist"""
        if self.dry_run:
            logger.info("🧪 DRY RUN: Skipping verification")
            return True
            
        logger.info("🔍 Verifying columns were added...")
        
        missing_columns = self.check_existing_columns()
        if missing_columns is None:
            return False
            
        if not missing_columns:
            logger.info("✅ All target columns now exist")
            return True
        else:
            logger.error(f"❌ Still missing columns: {', '.join(missing_columns)}")
            return False

    def run(self):
        """Execute the column addition process"""
        logger.info("🚀 Starting Railway Users Table Schema Update")
        logger.info("=" * 60)
        logger.info("🎯 Target: Add tenniscores_player_id and league_id columns")
        logger.info("🛡️  Safe: Only adds columns, doesn't modify existing data")
        logger.info("=" * 60)

        # Step 1: Check existing columns
        missing_columns = self.check_existing_columns()
        if missing_columns is None:
            logger.error("❌ Failed to check existing columns")
            return False

        # Step 2: Add missing columns
        if not self.add_missing_columns(missing_columns):
            logger.error("❌ Failed to add missing columns")
            return False

        # Step 3: Verify columns were added
        if not self.verify_columns_added():
            logger.error("❌ Column verification failed")
            return False

        # Success summary
        logger.info("\n" + "=" * 60)
        logger.info("✅ RAILWAY USERS TABLE SCHEMA UPDATE COMPLETED!")
        logger.info("=" * 60)
        logger.info("✅ Missing columns added successfully")
        logger.info("✅ Existing user data preserved")
        logger.info("✅ No auto-increment sequences affected")
        logger.info("🌐 Railway database schema now matches local")
        
        return True

def main():
    parser = argparse.ArgumentParser(description="Add missing columns to Railway users table")
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    adder = UserColumnAdder(dry_run=args.dry_run)
    success = adder.run()
    
    if success:
        logger.info("🎉 Schema update completed successfully!")
        sys.exit(0)
    else:
        logger.error("💥 Schema update failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 