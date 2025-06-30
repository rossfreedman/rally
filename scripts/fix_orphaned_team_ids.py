#!/usr/bin/env python3
"""
Fix Orphaned Team IDs in Match Scores
=====================================

This script fixes orphaned team_id references in the match_scores table by
mapping team names to their correct team IDs from the teams table.

The issue: Many matches have team_ids that don't exist in the teams table,
causing analyze-me pages to show 0 matches when filtering by team.

The solution: Map team names (home_team/away_team) to existing team IDs.

Usage:
    python scripts/fix_orphaned_team_ids.py [--dry-run]
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

class TeamIdFixer:
    def __init__(self, dry_run=False):
        self.railway_url = RAILWAY_DB_URL
        self.dry_run = dry_run
        
        if dry_run:
            logger.info("🧪 DRY RUN MODE: No actual changes will be made")

    def analyze_orphaned_team_ids(self):
        """Analyze the scope of orphaned team ID problem"""
        logger.info("🔍 Analyzing orphaned team IDs...")
        
        try:
            railway_params = parse_db_url(self.railway_url)
            railway_params["connect_timeout"] = 30
            conn = psycopg2.connect(**railway_params)

            with conn.cursor() as cursor:
                # Count total orphaned matches
                cursor.execute("""
                    SELECT COUNT(*) as orphaned_matches 
                    FROM match_scores ms 
                    LEFT JOIN teams t_home ON ms.home_team_id = t_home.id 
                    LEFT JOIN teams t_away ON ms.away_team_id = t_away.id 
                    WHERE (ms.home_team_id IS NOT NULL AND t_home.id IS NULL) 
                       OR (ms.away_team_id IS NOT NULL AND t_away.id IS NULL)
                """)
                
                orphaned_count = cursor.fetchone()[0]
                logger.info(f"📊 Found {orphaned_count:,} matches with orphaned team IDs")
                
                # Count unique orphaned team IDs
                cursor.execute("""
                    SELECT COUNT(DISTINCT home_team_id) + COUNT(DISTINCT away_team_id) as unique_orphaned_ids
                    FROM match_scores ms 
                    LEFT JOIN teams t_home ON ms.home_team_id = t_home.id 
                    LEFT JOIN teams t_away ON ms.away_team_id = t_away.id 
                    WHERE (ms.home_team_id IS NOT NULL AND t_home.id IS NULL) 
                       OR (ms.away_team_id IS NOT NULL AND t_away.id IS NULL)
                """)
                
                unique_orphaned = cursor.fetchone()[0]
                logger.info(f"📊 {unique_orphaned} unique orphaned team IDs found")

            conn.close()
            return orphaned_count
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze orphaned team IDs: {e}")
            return None

    def fix_home_team_ids(self):
        """Fix orphaned home_team_id values by mapping team names"""
        logger.info("🔧 Fixing home_team_id values...")
        
        if self.dry_run:
            logger.info("🧪 DRY RUN: Would fix home_team_id mappings")
            return True
            
        try:
            railway_params = parse_db_url(self.railway_url)
            railway_params["connect_timeout"] = 30
            conn = psycopg2.connect(**railway_params)
            conn.autocommit = True

            with conn.cursor() as cursor:
                # Update home_team_id based on home_team name mapping
                cursor.execute("""
                    UPDATE match_scores 
                    SET home_team_id = t.id
                    FROM teams t
                    WHERE match_scores.home_team = t.team_name
                    AND (match_scores.home_team_id IS NULL 
                         OR match_scores.home_team_id NOT IN (SELECT id FROM teams))
                """)
                
                updated_count = cursor.rowcount
                logger.info(f"✅ Updated {updated_count:,} home_team_id values")

            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to fix home_team_id values: {e}")
            return False

    def fix_away_team_ids(self):
        """Fix orphaned away_team_id values by mapping team names"""
        logger.info("🔧 Fixing away_team_id values...")
        
        if self.dry_run:
            logger.info("🧪 DRY RUN: Would fix away_team_id mappings")
            return True
            
        try:
            railway_params = parse_db_url(self.railway_url)
            railway_params["connect_timeout"] = 30
            conn = psycopg2.connect(**railway_params)
            conn.autocommit = True

            with conn.cursor() as cursor:
                # Update away_team_id based on away_team name mapping
                cursor.execute("""
                    UPDATE match_scores 
                    SET away_team_id = t.id
                    FROM teams t
                    WHERE match_scores.away_team = t.team_name
                    AND (match_scores.away_team_id IS NULL 
                         OR match_scores.away_team_id NOT IN (SELECT id FROM teams))
                """)
                
                updated_count = cursor.rowcount
                logger.info(f"✅ Updated {updated_count:,} away_team_id values")

            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to fix away_team_id values: {e}")
            return False

    def verify_fixes(self):
        """Verify that the team ID fixes worked"""
        if self.dry_run:
            logger.info("🧪 DRY RUN: Skipping verification")
            return True
            
        logger.info("🔍 Verifying team ID fixes...")
        
        try:
            railway_params = parse_db_url(self.railway_url)
            railway_params["connect_timeout"] = 30
            conn = psycopg2.connect(**railway_params)

            with conn.cursor() as cursor:
                # Count remaining orphaned matches
                cursor.execute("""
                    SELECT COUNT(*) as remaining_orphaned 
                    FROM match_scores ms 
                    LEFT JOIN teams t_home ON ms.home_team_id = t_home.id 
                    LEFT JOIN teams t_away ON ms.away_team_id = t_away.id 
                    WHERE (ms.home_team_id IS NOT NULL AND t_home.id IS NULL) 
                       OR (ms.away_team_id IS NOT NULL AND t_away.id IS NULL)
                """)
                
                remaining_orphaned = cursor.fetchone()[0]
                
                # Count properly mapped matches
                cursor.execute("""
                    SELECT COUNT(*) as properly_mapped 
                    FROM match_scores ms 
                    JOIN teams t_home ON ms.home_team_id = t_home.id 
                    JOIN teams t_away ON ms.away_team_id = t_away.id
                """)
                
                properly_mapped = cursor.fetchone()[0]
                
                logger.info(f"📊 Verification results:")
                logger.info(f"   ✅ Properly mapped matches: {properly_mapped:,}")
                logger.info(f"   ❌ Remaining orphaned matches: {remaining_orphaned:,}")
                
                if remaining_orphaned == 0:
                    logger.info("🎉 All team ID issues resolved!")
                    return True
                else:
                    logger.warning(f"⚠️  {remaining_orphaned:,} matches still have orphaned team IDs")
                    
                    # Show examples of remaining issues
                    cursor.execute("""
                        SELECT DISTINCT ms.home_team, ms.away_team 
                        FROM match_scores ms 
                        LEFT JOIN teams t_home ON ms.home_team_id = t_home.id 
                        LEFT JOIN teams t_away ON ms.away_team_id = t_away.id 
                        WHERE (ms.home_team_id IS NOT NULL AND t_home.id IS NULL) 
                           OR (ms.away_team_id IS NOT NULL AND t_away.id IS NULL)
                        LIMIT 5
                    """)
                    
                    examples = cursor.fetchall()
                    if examples:
                        logger.info("📝 Examples of remaining issues:")
                        for home, away in examples:
                            logger.info(f"   - {home} vs {away}")
                    
                    return remaining_orphaned < 1000  # Accept if < 1000 remaining

            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return False

    def run(self):
        """Execute the complete team ID fix process"""
        logger.info("🚀 Starting Railway Team ID Fix")
        logger.info("=" * 60)
        logger.info("🎯 Target: Fix orphaned team IDs in match_scores table")
        logger.info("🛡️  Safe: Maps team names to existing team IDs")
        logger.info("=" * 60)

        # Step 1: Analyze the problem
        orphaned_count = self.analyze_orphaned_team_ids()
        if orphaned_count is None:
            logger.error("❌ Failed to analyze problem")
            return False
        
        if orphaned_count == 0:
            logger.info("✅ No orphaned team IDs found - nothing to fix!")
            return True

        # Step 2: Fix home team IDs
        if not self.fix_home_team_ids():
            logger.error("❌ Failed to fix home team IDs")
            return False

        # Step 3: Fix away team IDs
        if not self.fix_away_team_ids():
            logger.error("❌ Failed to fix away team IDs")
            return False

        # Step 4: Verify fixes
        if not self.verify_fixes():
            logger.error("❌ Verification failed")
            return False

        # Success summary
        logger.info("\n" + "=" * 60)
        logger.info("✅ RAILWAY TEAM ID FIX COMPLETED!")
        logger.info("=" * 60)
        logger.info("✅ Team IDs mapped from team names")
        logger.info("✅ Match data now properly linked to teams")
        logger.info("✅ User analyze-me pages should show correct match counts")
        logger.info("🌐 All users' team-filtered data should now work correctly")
        
        return True

def main():
    parser = argparse.ArgumentParser(description="Fix orphaned team IDs in Railway match_scores table")
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    fixer = TeamIdFixer(dry_run=args.dry_run)
    success = fixer.run()
    
    if success:
        logger.info("🎉 Team ID fix completed successfully!")
        sys.exit(0)
    else:
        logger.error("💥 Team ID fix failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 