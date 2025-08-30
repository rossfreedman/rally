#!/usr/bin/env python3
"""
Script to continue production migration from step 4.

This continues the migration that was partially completed:
- Steps 1-3: ✅ Completed (team_id column added, populated, indexed)
- Steps 4-8: Need to complete
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def continue_production_migration():
    """Continue production migration from step 4"""
    try:
        logger.info("🚀 Continuing production migration from step 4...")
        
        # Check if we're in the right environment
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.error("❌ DATABASE_URL environment variable not set")
            return False
        
        if "ballast.proxy.rlwy.net" not in database_url:
            logger.error("❌ NOT connected to production database!")
            return False
        
        logger.info("📝 Continuing database schema changes to PRODUCTION...")
        
        # Import database utilities
        from utils.db import execute_update
        
        # Step 4: Make team_id NOT NULL
        logger.info("📝 Step 4: Making team_id NOT NULL...")
        make_not_null_query = """
            ALTER TABLE player_season_tracking 
            ALTER COLUMN team_id SET NOT NULL
        """
        
        success = execute_update(make_not_null_query)
        if success:
            logger.info("    ✅ Successfully made team_id NOT NULL")
        else:
            logger.error("    ❌ Failed to make team_id NOT NULL")
            return False
        
        # Step 5: Drop existing unique constraint if it exists
        logger.info("📝 Step 5: Dropping existing unique constraint...")
        drop_constraint_query = """
            ALTER TABLE player_season_tracking 
            DROP CONSTRAINT IF EXISTS unique_player_season_tracking
        """
        
        success = execute_update(drop_constraint_query)
        if success:
            logger.info("    ✅ Successfully dropped existing unique constraint")
        else:
            logger.error("    ❌ Failed to drop existing unique constraint")
            return False
        
        # Step 6: Create new unique constraint without season_year
        logger.info("📝 Step 6: Creating new unique constraint...")
        create_constraint_query = """
            ALTER TABLE player_season_tracking 
            ADD CONSTRAINT unique_player_season_tracking 
            UNIQUE (player_id, team_id, league_id)
        """
        
        success = execute_update(create_constraint_query)
        if success:
            logger.info("    ✅ Successfully created new unique constraint")
        else:
            logger.error("    ❌ Failed to create new unique constraint")
            return False
        
        # Step 7: Make season_year nullable
        logger.info("📝 Step 7: Making season_year nullable...")
        alter_column_query = """
            ALTER TABLE player_season_tracking 
            ALTER COLUMN season_year DROP NOT NULL
        """
        
        success = execute_update(alter_column_query)
        if success:
            logger.info("    ✅ Successfully made season_year nullable")
        else:
            logger.error("    ❌ Failed to make season_year nullable")
            return False
        
        # Step 8: Add foreign key constraint for team_id
        logger.info("📝 Step 8: Adding foreign key constraint...")
        add_fk_query = """
            ALTER TABLE player_season_tracking 
            ADD CONSTRAINT fk_player_season_tracking_team_id 
            FOREIGN KEY (team_id) REFERENCES teams(id)
        """
        
        success = execute_update(add_fk_query)
        if success:
            logger.info("    ✅ Successfully added foreign key constraint")
        else:
            logger.error("    ❌ Failed to add foreign key constraint")
            return False
        
        logger.info("🎉 Successfully completed production migration!")
        logger.info("✅ The system now works with team-specific tracking without season complexity")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error continuing production migration: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Main function"""
    try:
        success = continue_production_migration()
        
        if success:
            logger.info("🎉 Successfully completed production migration!")
            logger.info("✅ Database schema updated for team-specific tracking")
            logger.info("✅ Season year complexity removed")
            logger.info("✅ Next: Deploy code changes and test the functionality")
            return True
        else:
            logger.error("❌ Failed to complete production migration")
            return False
            
    except Exception as e:
        logger.error(f"❌ Script execution failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
