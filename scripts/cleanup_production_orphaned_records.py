#!/usr/bin/env python3
"""
Script to clean up orphaned records in production before completing migration.

This identifies and removes records that can't be properly migrated
due to missing player data.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def cleanup_production_orphaned_records():
    """Clean up orphaned records in production"""
    try:
        logger.info("🧹 Cleaning up orphaned records in production...")
        
        # Check if we're in the right environment
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.error("❌ DATABASE_URL environment variable not set")
            return False
        
        if "ballast.proxy.rlwy.net" not in database_url:
            logger.error("❌ NOT connected to production database!")
            return False
        
        logger.info("📝 Identifying orphaned records...")
        
        # Import database utilities
        from utils.db import execute_query, execute_update
        
        # Find records that can't be populated with team_id
        orphaned_records = execute_query("""
            SELECT pst.id, pst.player_id, pst.league_id, pst.season_year
            FROM player_season_tracking pst
            LEFT JOIN players p ON pst.player_id = p.tenniscores_player_id
            WHERE p.tenniscores_player_id IS NULL
            AND pst.team_id IS NULL
        """)
        
        if not orphaned_records:
            logger.info("✅ No orphaned records found")
            return True
        
        logger.info(f"Found {len(orphaned_records)} orphaned records:")
        for record in orphaned_records:
            logger.info(f"  - ID {record['id']}: {record['player_id']} (League: {record['league_id']}, Season: {record['season_year']})")
        
        # Get confirmation before deletion
        print(f"\n🚨 Found {len(orphaned_records)} orphaned records that will be deleted")
        print("These records cannot be migrated because the players don't exist")
        response = input("Delete these orphaned records? (y/N): ")
        if response.lower() != 'y':
            logger.info("❌ Cleanup cancelled by user")
            return False
        
        # Delete orphaned records
        logger.info("🗑️  Deleting orphaned records...")
        delete_query = """
            DELETE FROM player_season_tracking 
            WHERE id = %s
        """
        
        deleted_count = 0
        for record in orphaned_records:
            success = execute_update(delete_query, [record['id']])
            if success:
                deleted_count += 1
                logger.info(f"    ✅ Deleted orphaned record {record['id']}")
            else:
                logger.error(f"    ❌ Failed to delete record {record['id']}")
        
        logger.info(f"✅ Successfully deleted {deleted_count} orphaned records")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error cleaning up orphaned records: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Main function"""
    try:
        success = cleanup_production_orphaned_records()
        
        if success:
            logger.info("🎉 Successfully cleaned up orphaned records!")
            logger.info("✅ Production database is now ready for migration")
            return True
        else:
            logger.error("❌ Failed to clean up orphaned records")
            return False
            
    except Exception as e:
        logger.error(f"❌ Script execution failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
