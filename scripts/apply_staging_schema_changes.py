#!/usr/bin/env python3
"""
Script to apply database schema changes to the staging environment.

This applies the same changes we made locally:
1. Remove season_year from unique constraints
2. Make season_year nullable
3. Update unique constraint to (player_id, team_id, league_id)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def apply_staging_schema_changes():
    """Apply schema changes to staging database"""
    try:
        logger.info("🚀 Applying schema changes to staging database...")
        
        # Check if we're in the right environment
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.error("❌ DATABASE_URL environment variable not set")
            return False
        
        if "railway.app" not in database_url:
            logger.warning("⚠️  DATABASE_URL doesn't appear to be staging (no railway.app)")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                logger.info("Aborted by user")
                return False
        
        logger.info("📝 Applying database schema changes...")
        
        # Import database utilities
        from utils.db import execute_update
        
        # Step 1: Drop the existing unique constraint
        logger.info("📝 Step 1: Dropping existing unique constraint...")
        drop_constraint_query = """
            ALTER TABLE player_season_tracking 
            DROP CONSTRAINT IF EXISTS unique_player_season_tracking
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
        
        logger.info("🎉 Successfully applied schema changes to staging!")
        logger.info("✅ The system now works with team-specific tracking without season complexity")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error applying staging schema changes: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Main function"""
    try:
        success = apply_staging_schema_changes()
        
        if success:
            logger.info("🎉 Successfully updated staging database schema!")
            logger.info("✅ Season year complexity removed from tracking system")
            logger.info("✅ Team-specific tracking now works with existing data")
            logger.info("✅ Next: Deploy code changes and test the functionality")
            return True
        else:
            logger.error("❌ Failed to update staging database schema")
            return False
            
    except Exception as e:
        logger.error(f"❌ Script execution failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
