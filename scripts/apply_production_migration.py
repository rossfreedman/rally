#!/usr/bin/env python3
"""
PRODUCTION MIGRATION SCRIPT - Apply team-specific tracking changes to production.

⚠️  WARNING: This script modifies the PRODUCTION database.
⚠️  Ensure you have a backup before proceeding.
⚠️  Test thoroughly on staging first.

This applies the exact same changes as staging:
1. Add team_id column to player_season_tracking
2. Populate team_id for existing records
3. Make team_id NOT NULL
4. Update unique constraints
5. Remove season_year complexity
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def confirm_production_migration():
    """Get explicit confirmation before proceeding with production changes"""
    logger.warning("🚨 PRODUCTION MIGRATION CONFIRMATION REQUIRED")
    logger.warning("⚠️  This script will modify the PRODUCTION database")
    logger.warning("⚠️  Ensure you have a backup before proceeding")
    
    print("\n" + "="*80)
    print("🚨 PRODUCTION DATABASE MIGRATION CONFIRMATION")
    print("="*80)
    print("This script will apply the following changes to PRODUCTION:")
    print("1. Add team_id column to player_season_tracking")
    print("2. Populate team_id for existing records")
    print("3. Make team_id NOT NULL")
    print("4. Update unique constraints")
    print("5. Remove season_year complexity")
    print("="*80)
    
    # Check if we're connected to production
    database_url = os.getenv("DATABASE_URL")
    if database_url and "ballast.proxy.rlwy.net" in database_url:
        logger.info("✅ Connected to PRODUCTION database")
    else:
        logger.error("❌ NOT connected to production database!")
        logger.error("Expected: ballast.proxy.rlwy.net")
        logger.error(f"Found: {database_url}")
        return False
    
    # Get explicit confirmation
    response = input("\n🚨 Type 'PRODUCTION' to confirm: ")
    if response != "PRODUCTION":
        logger.info("❌ Migration cancelled by user")
        return False
    
    # Double confirmation
    response2 = input("🚨 Type 'YES' to proceed with production changes: ")
    if response2 != "YES":
        logger.info("❌ Migration cancelled by user")
        return False
    
    logger.info("✅ Production migration confirmed - proceeding...")
    return True

def apply_production_migration():
    """Apply complete migration to production database"""
    try:
        logger.info("🚀 Applying complete migration to PRODUCTION database...")
        
        # Check if we're in the right environment
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.error("❌ DATABASE_URL environment variable not set")
            return False
        
        if "ballast.proxy.rlwy.net" not in database_url:
            logger.error("❌ NOT connected to production database!")
            logger.error("Expected: ballast.proxy.rlwy.net")
            logger.error(f"Found: {database_url}")
            return False
        
        logger.info("📝 Applying database schema changes to PRODUCTION...")
        
        # Import database utilities
        from utils.db import execute_update, execute_query, execute_query_one
        
        # Step 1: Add team_id column if it doesn't exist
        logger.info("📝 Step 1: Adding team_id column...")
        
        # Check if team_id column exists
        column_check = execute_query("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'player_season_tracking' 
            AND column_name = 'team_id'
        """)
        
        if not column_check:
            logger.info("  Adding team_id column...")
            add_column_query = """
                ALTER TABLE player_season_tracking 
                ADD COLUMN team_id INTEGER
            """
            
            success = execute_update(add_column_query)
            if success:
                logger.info("    ✅ Successfully added team_id column")
            else:
                logger.error("    ❌ Failed to add team_id column")
                return False
        else:
            logger.info("  ✅ team_id column already exists")
        
        # Step 2: Create index on team_id
        logger.info("📝 Step 2: Creating index on team_id...")
        create_index_query = """
            CREATE INDEX IF NOT EXISTS idx_player_season_tracking_team_id 
            ON player_season_tracking(team_id)
        """
        
        success = execute_update(create_index_query)
        if success:
            logger.info("    ✅ Successfully created team_id index")
        else:
            logger.error("    ❌ Failed to create team_id index")
            return False
        
        # Step 3: Populate team_id for existing records
        logger.info("📝 Step 3: Populating team_id for existing records...")
        
        # Get records that need team_id populated
        records_to_update = execute_query("""
            SELECT pst.id, pst.player_id, p.team_id
            FROM player_season_tracking pst
            JOIN players p ON pst.player_id = p.tenniscores_player_id
            WHERE pst.team_id IS NULL
            AND p.team_id IS NOT NULL
        """)
        
        if records_to_update:
            logger.info(f"  Found {len(records_to_update)} records to update")
            
            updated_count = 0
            for record in records_to_update:
                update_query = """
                    UPDATE player_season_tracking 
                    SET team_id = %s 
                    WHERE id = %s
                """
                
                success = execute_update(update_query, [record['team_id'], record['id']])
                if success:
                    updated_count += 1
                else:
                    logger.error(f"    ❌ Failed to update record {record['id']}")
            
            logger.info(f"    ✅ Successfully updated {updated_count} records")
        else:
            logger.info("  ✅ All records already have team_id")
        
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
        
        logger.info("🎉 Successfully applied complete migration to PRODUCTION!")
        logger.info("✅ The system now works with team-specific tracking without season complexity")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error applying production migration: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Main function"""
    try:
        # Get explicit confirmation before proceeding
        if not confirm_production_migration():
            return False
        
        success = apply_production_migration()
        
        if success:
            logger.info("🎉 Successfully applied complete migration to PRODUCTION!")
            logger.info("✅ Database schema updated for team-specific tracking")
            logger.info("✅ Season year complexity removed")
            logger.info("✅ Next: Deploy code changes and test the functionality")
            return True
        else:
            logger.error("❌ Failed to apply production migration")
            return False
            
    except Exception as e:
        logger.error(f"❌ Script execution failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
