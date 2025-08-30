#!/usr/bin/env python3
"""
Script to remove season_year from the player_season_tracking table.

This removes the confusing season-based logic and makes the system work
with the existing data structure.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import execute_update
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def remove_season_year_from_tracking():
    """Remove season_year from the unique constraint and make it nullable"""
    try:
        logger.info("🚀 Removing season_year from player_season_tracking table")
        
        # Step 1: Drop the existing unique constraint
        logger.info("📝 Step 1: Dropping existing unique constraint...")
        drop_constraint_query = """
            ALTER TABLE player_season_tracking 
            DROP CONSTRAINT unique_player_season_tracking
        """
        
        success = execute_update(drop_constraint_query)
        if success:
            logger.info("✅ Successfully dropped unique constraint")
        else:
            logger.error("❌ Failed to drop unique constraint")
            return False
        
        # Step 2: Create new unique constraint without season_year
        logger.info("📝 Step 2: Creating new unique constraint without season_year...")
        create_constraint_query = """
            ALTER TABLE player_season_tracking 
            ADD CONSTRAINT unique_player_season_tracking 
            UNIQUE (player_id, team_id, league_id)
        """
        
        success = execute_update(create_constraint_query)
        if success:
            logger.info("✅ Successfully created new unique constraint")
        else:
            logger.error("❌ Failed to create new unique constraint")
            return False
        
        # Step 3: Make season_year nullable (optional)
        logger.info("📝 Step 3: Making season_year nullable...")
        alter_column_query = """
            ALTER TABLE player_season_tracking 
            ALTER COLUMN season_year DROP NOT NULL
        """
        
        success = execute_update(alter_column_query)
        if success:
            logger.info("✅ Successfully made season_year nullable")
        else:
            logger.error("❌ Failed to make season_year nullable")
            return False
        
        logger.info("🎉 Successfully removed season_year from tracking system!")
        logger.info("✅ The system now works with team-specific tracking without season complexity")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error removing season_year: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Main function"""
    try:
        success = remove_season_year_from_tracking()
        
        if success:
            logger.info("🎉 Successfully updated database schema!")
            logger.info("✅ Season year complexity removed from tracking system")
            logger.info("✅ Team-specific tracking now works with existing data")
            return True
        else:
            logger.error("❌ Failed to update database schema")
            return False
            
    except Exception as e:
        logger.error(f"❌ Script execution failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
