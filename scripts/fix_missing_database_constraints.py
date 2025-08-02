#!/usr/bin/env python3
"""
Fix Missing Database Constraints for ETL Import Scripts

This script adds the unique constraints that the import scripts expect
for their ON CONFLICT clauses to work properly.

Based on analysis of import script ON CONFLICT clauses:
- series_stats: (league_id, series, team)
- players: (tenniscores_player_id, league_id, club_id, series_id)  
- schedule: (match_date, home_team, away_team, league_id)
- match_scores: (tenniscores_match_id) WHERE tenniscores_match_id IS NOT NULL

Usage: python scripts/fix_missing_database_constraints.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseConstraintFixer:
    """Fixes missing unique constraints for ETL import operations"""
    
    def __init__(self):
        self.constraints_added = 0
        self.constraints_already_exist = 0
    
    def constraint_exists(self, table_name: str, constraint_name: str) -> bool:
        """Check if a constraint already exists"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT constraint_name 
                    FROM information_schema.table_constraints 
                    WHERE table_name = %s 
                    AND constraint_type = 'UNIQUE'
                    AND constraint_name = %s
                """, (table_name, constraint_name))
                
                result = cursor.fetchone()
                cursor.close()
                return result is not None
        except Exception as e:
            logger.error(f"❌ Error checking constraint {constraint_name}: {e}")
            return False
    
    def index_exists(self, table_name: str, index_name: str) -> bool:
        """Check if an index already exists"""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename = %s 
                    AND indexname = %s
                """, (table_name, index_name))
                
                result = cursor.fetchone()
                cursor.close()
                return result is not None
        except Exception as e:
            logger.error(f"❌ Error checking index {index_name}: {e}")
            return False
            
    def create_series_stats_constraint(self):
        """Create unique constraint for series_stats table: (league_id, series, team)"""
        table_name = "series_stats"
        constraint_name = "unique_series_stats_league_series_team"
        
        if self.constraint_exists(table_name, constraint_name):
            logger.info(f"ℹ️  Constraint already exists: {constraint_name}")
            self.constraints_already_exist += 1
            return True
            
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                logger.info(f"🔧 Creating constraint: {constraint_name}")
                
                cursor.execute(f"""
                    ALTER TABLE {table_name} 
                    ADD CONSTRAINT {constraint_name} 
                    UNIQUE (league_id, series, team)
                """)
                
                conn.commit()
                cursor.close()
                logger.info(f"✅ Created constraint: {constraint_name}")
                self.constraints_added += 1
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to create constraint {constraint_name}: {e}")
            return False
    
    def create_players_constraint(self):
        """Create unique constraint for players table: (tenniscores_player_id, league_id, club_id, series_id)"""
        table_name = "players"
        constraint_name = "unique_players_tenniscores_league_club_series"
        
        if self.constraint_exists(table_name, constraint_name):
            logger.info(f"ℹ️  Constraint already exists: {constraint_name}")
            self.constraints_already_exist += 1
            return True
            
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                logger.info(f"🔧 Creating constraint: {constraint_name}")
                
                cursor.execute(f"""
                    ALTER TABLE {table_name} 
                    ADD CONSTRAINT {constraint_name} 
                    UNIQUE (tenniscores_player_id, league_id, club_id, series_id)
                """)
                
                conn.commit()
                cursor.close()
                logger.info(f"✅ Created constraint: {constraint_name}")
                self.constraints_added += 1
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to create constraint {constraint_name}: {e}")
            return False
    
    def create_schedule_constraint(self):
        """Create unique constraint for schedule table: (match_date, home_team, away_team, league_id)"""
        table_name = "schedule"
        constraint_name = "unique_schedule_match"
        
        if self.constraint_exists(table_name, constraint_name):
            logger.info(f"ℹ️  Constraint already exists: {constraint_name}")
            self.constraints_already_exist += 1
            return True
            
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                logger.info(f"🔧 Creating constraint: {constraint_name}")
                
                cursor.execute(f"""
                    ALTER TABLE {table_name} 
                    ADD CONSTRAINT {constraint_name} 
                    UNIQUE (match_date, home_team, away_team, league_id)
                """)
                
                conn.commit()
                cursor.close()
                logger.info(f"✅ Created constraint: {constraint_name}")
                self.constraints_added += 1
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to create constraint {constraint_name}: {e}")
            return False
    
    def create_match_scores_constraint(self):
        """Create partial unique index for match_scores table: (tenniscores_match_id) WHERE tenniscores_match_id IS NOT NULL"""
        table_name = "match_scores"
        index_name = "unique_match_scores_tenniscores_match_id"
        
        if self.index_exists(table_name, index_name):
            logger.info(f"ℹ️  Index already exists: {index_name}")
            self.constraints_already_exist += 1
            return True
            
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                logger.info(f"🔧 Creating partial unique index: {index_name}")
                
                # Create partial unique index (equivalent to unique constraint with WHERE clause)
                cursor.execute(f"""
                    CREATE UNIQUE INDEX {index_name} 
                    ON {table_name} (tenniscores_match_id) 
                    WHERE tenniscores_match_id IS NOT NULL
                """)
                
                conn.commit()
                cursor.close()
                logger.info(f"✅ Created partial unique index: {index_name}")
                self.constraints_added += 1
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to create index {index_name}: {e}")
            return False
    
    def fix_all_constraints(self):
        """Fix all missing constraints for ETL import operations"""
        logger.info("🎯 Starting Database Constraint Fix")
        logger.info("="*60)
        
        success = True
        
        # Create all required constraints
        constraints = [
            ("series_stats", self.create_series_stats_constraint),
            ("players", self.create_players_constraint), 
            ("schedule", self.create_schedule_constraint),
            ("match_scores", self.create_match_scores_constraint)
        ]
        
        for table_name, create_func in constraints:
            logger.info(f"\n📋 Processing {table_name} table constraints...")
            if not create_func():
                success = False
                logger.error(f"❌ Failed to process {table_name} constraints")
            else:
                logger.info(f"✅ Successfully processed {table_name} constraints")
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("📊 CONSTRAINT FIX SUMMARY")
        logger.info("="*60)
        logger.info(f"✅ Constraints added: {self.constraints_added}")
        logger.info(f"ℹ️  Already existed: {self.constraints_already_exist}")
        logger.info(f"📈 Total processed: {self.constraints_added + self.constraints_already_exist}")
        
        if success:
            logger.info("🎉 All constraints processed successfully!")
            logger.info("💡 ETL import ON CONFLICT operations should now work properly")
        else:
            logger.error("❌ Some constraints failed to be created")
            
        return success

def main():
    """Main function"""
    print("🔧 Database Constraint Fixer for ETL Import Scripts")
    print("="*60)
    print("This script adds missing unique constraints that import scripts")
    print("expect for their ON CONFLICT clauses to work properly.")
    print("="*60)
    
    fixer = DatabaseConstraintFixer()
    success = fixer.fix_all_constraints()
    
    if success:
        print("\n🎉 SUCCESS: All database constraints have been fixed!")
        print("💡 You can now re-run the ETL import and it should work properly.")
        return 0
    else:
        print("\n❌ FAILURE: Some constraints could not be created.")
        print("💡 Check the error logs above and resolve issues manually.")
        return 1

if __name__ == "__main__":
    exit(main())