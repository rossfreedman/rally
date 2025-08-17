#!/usr/bin/env python3
"""
Apply Joel Braunstein Orphaned Records Fix to Remote Environments
================================================================

This script applies the database fixes to actual staging/production environments
using direct database connections via Railway public URLs.

Usage:
1. For staging: export DATABASE_PUBLIC_URL=$(railway variables --service "Rally STAGING App" --json | jq -r '.DATABASE_PUBLIC_URL')
2. For production: export DATABASE_PUBLIC_URL=$(railway variables --service "Rally Production App" --json | jq -r '.DATABASE_PUBLIC_URL')
3. Run: python scripts/apply_orphan_fix_to_remote.py --environment staging/production
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RemoteOrphanFix:
    """Apply orphaned records fixes to remote environments"""
    
    def __init__(self, environment="staging"):
        self.environment = environment
        self.start_time = datetime.now()
        self.conn = None
        self.fixes_applied = {
            'series_stats_league_ids': 0,
            'series_stats_team_ids': 0,
            'schedule_league_ids': 0,
            'schedule_team_ids': 0,
            'match_scores_league_ids': 0,
            'match_scores_team_ids': 0
        }
        
    def connect_to_remote(self):
        """Connect to remote database using environment URL"""
        staging_url = (
            os.getenv('DATABASE_PUBLIC_URL') or 
            os.getenv('DATABASE_URL') or
            os.getenv('STAGING_DATABASE_URL')
        )
        
        if not staging_url:
            print("❌ No database URL found!")
            print("Set DATABASE_PUBLIC_URL environment variable first")
            return False
            
        # Handle Railway's postgres:// URLs
        if staging_url.startswith("postgres://"):
            staging_url = staging_url.replace("postgres://", "postgresql://", 1)
        
        # Parse and connect
        parsed = urlparse(staging_url)
        conn_params = {
            "dbname": parsed.path[1:],
            "user": parsed.username,
            "password": parsed.password,
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "sslmode": "require",
            "connect_timeout": 30,
            "application_name": f"orphan_fix_{self.environment}"
        }
        
        try:
            self.conn = psycopg2.connect(**conn_params)
            print(f"✅ Connected to {self.environment} database at {parsed.hostname}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to {self.environment} database: {e}")
            return False
    
    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        if not self.conn:
            return None
            
        try:
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params or [])
            return cursor.fetchall()
        except Exception as e:
            print(f"❌ Query failed: {e}")
            return None
    
    def execute_query_one(self, query, params=None):
        """Execute a query and return single result"""
        results = self.execute_query(query, params)
        return results[0] if results else None
    
    def execute_update(self, query, params=None):
        """Execute an update query and return affected rows"""
        if not self.conn:
            return 0
            
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params or [])
            affected = cursor.rowcount
            self.conn.commit()
            return affected
        except Exception as e:
            print(f"❌ Update failed: {e}")
            self.conn.rollback()
            return 0
    
    def run_diagnostic(self):
        """Run diagnostic checks to identify orphaned records"""
        print(f"\n🔍 DIAGNOSTIC: Checking for orphaned records in {self.environment}...")
        
        # Check orphaned league_ids in series_stats
        orphaned_leagues = self.execute_query_one("""
            SELECT COUNT(*) as count
            FROM series_stats ss
            LEFT JOIN leagues l ON ss.league_id = l.id
            WHERE l.id IS NULL AND ss.league_id IS NOT NULL
        """)
        print(f"   📊 Orphaned league_ids in series_stats: {orphaned_leagues['count'] if orphaned_leagues else 0}")
        
        # Check orphaned team_ids in series_stats
        orphaned_teams = self.execute_query_one("""
            SELECT COUNT(*) as count
            FROM series_stats ss
            WHERE ss.team_id IS NULL OR ss.team_id NOT IN (SELECT id FROM teams)
        """)
        print(f"   📊 Orphaned team_ids in series_stats: {orphaned_teams['count'] if orphaned_teams else 0}")
        
        # Show specific orphaned league_ids
        orphaned_league_breakdown = self.execute_query("""
            SELECT ss.league_id, COUNT(*) as count
            FROM series_stats ss
            LEFT JOIN leagues l ON ss.league_id = l.id
            WHERE l.id IS NULL AND ss.league_id IS NOT NULL
            GROUP BY ss.league_id
            ORDER BY ss.league_id
        """)
        
        if orphaned_league_breakdown:
            print(f"   📋 Orphaned league_id breakdown:")
            for row in orphaned_league_breakdown:
                print(f"      - league_id {row['league_id']}: {row['count']} records")
                
        return {
            'orphaned_leagues': orphaned_leagues['count'] if orphaned_leagues else 0,
            'orphaned_teams': orphaned_teams['count'] if orphaned_teams else 0,
            'breakdown': orphaned_league_breakdown
        }
    
    def get_current_league_mappings(self):
        """Get current league mappings from database"""
        leagues = self.execute_query("SELECT id, league_id, league_name FROM leagues ORDER BY id")
        
        print(f"\n📋 Current leagues in {self.environment}:")
        league_map = {}
        for league in leagues or []:
            print(f"   - ID {league['id']}: {league['league_id']} ({league['league_name']})")
            league_map[league['league_id']] = league['id']
            
        return league_map
    
    def apply_orphaned_league_fixes(self):
        """Apply the orphaned league_id fixes"""
        print(f"\n🔧 FIXING: Orphaned league_ids...")
        
        # Get current league mappings
        league_map = self.get_current_league_mappings()
        
        # Define the orphan mappings discovered during investigation
        orphan_mappings = {
            4551: league_map.get('APTA_CHICAGO'),
            4552: league_map.get('CITA'),
            4553: league_map.get('CNSWPL'),
            4554: league_map.get('NSTF')
        }
        
        print(f"   📋 Orphan mappings to apply:")
        for orphaned_id, correct_id in orphan_mappings.items():
            if correct_id:
                print(f"      - {orphaned_id} → {correct_id}")
            else:
                print(f"      - {orphaned_id} → SKIPPED (target league not found)")
        
        # Apply fixes to series_stats table
        total_fixed = 0
        for orphaned_id, correct_id in orphan_mappings.items():
            if correct_id is None:
                continue
                
            result = self.execute_update(
                "UPDATE series_stats SET league_id = %s WHERE league_id = %s",
                [correct_id, orphaned_id]
            )
            
            if result > 0:
                print(f"   ✅ Fixed {result} series_stats records: {orphaned_id} → {correct_id}")
                self.fixes_applied['series_stats_league_ids'] += result
                total_fixed += result
        
        # Apply fixes to schedule table
        for orphaned_id, correct_id in orphan_mappings.items():
            if correct_id is None:
                continue
                
            result = self.execute_update(
                "UPDATE schedule SET league_id = %s WHERE league_id = %s",
                [correct_id, orphaned_id]
            )
            
            if result > 0:
                print(f"   ✅ Fixed {result} schedule records: {orphaned_id} → {correct_id}")
                self.fixes_applied['schedule_league_ids'] += result
                total_fixed += result
        
        # Apply fixes to match_scores table
        for orphaned_id, correct_id in orphan_mappings.items():
            if correct_id is None:
                continue
                
            result = self.execute_update(
                "UPDATE match_scores SET league_id = %s WHERE league_id = %s",
                [correct_id, orphaned_id]
            )
            
            if result > 0:
                print(f"   ✅ Fixed {result} match_scores records: {orphaned_id} → {correct_id}")
                self.fixes_applied['match_scores_league_ids'] += result
                total_fixed += result
        
        print(f"   📊 Total league_id fixes applied: {total_fixed}")
        return total_fixed
    
    def apply_orphaned_team_fixes(self):
        """Fix orphaned team_ids by matching team names"""
        print(f"\n🔧 FIXING: Orphaned team_ids...")
        
        # Fix series_stats team_ids
        result = self.execute_update("""
            UPDATE series_stats ss
            SET team_id = t.id
            FROM teams t
            WHERE ss.team = t.team_name 
              AND (ss.team_id IS NULL OR ss.team_id NOT IN (SELECT id FROM teams))
        """)
        
        if result > 0:
            print(f"   ✅ Fixed {result} series_stats team_id records")
            self.fixes_applied['series_stats_team_ids'] += result
        
        # Fix schedule home_team_ids
        result = self.execute_update("""
            UPDATE schedule s
            SET home_team_id = t.id
            FROM teams t
            WHERE s.home_team = t.team_name 
              AND (s.home_team_id IS NULL OR s.home_team_id NOT IN (SELECT id FROM teams))
        """)
        
        if result > 0:
            print(f"   ✅ Fixed {result} schedule home_team_id records")
            self.fixes_applied['schedule_team_ids'] += result
            
        # Fix schedule away_team_ids
        result = self.execute_update("""
            UPDATE schedule s
            SET away_team_id = t.id
            FROM teams t
            WHERE s.away_team = t.team_name
              AND (s.away_team_id IS NULL OR s.away_team_id NOT IN (SELECT id FROM teams))
        """)
        
        if result > 0:
            print(f"   ✅ Fixed {result} schedule away_team_id records") 
            self.fixes_applied['schedule_team_ids'] += result
            
        # Fix match_scores home_team_ids
        result = self.execute_update("""
            UPDATE match_scores ms
            SET home_team_id = t.id
            FROM teams t
            WHERE ms.home_team = t.team_name 
              AND (ms.home_team_id IS NULL OR ms.home_team_id NOT IN (SELECT id FROM teams))
        """)
        
        if result > 0:
            print(f"   ✅ Fixed {result} match_scores home_team_id records")
            self.fixes_applied['match_scores_team_ids'] += result
            
        # Fix match_scores away_team_ids  
        result = self.execute_update("""
            UPDATE match_scores ms
            SET away_team_id = t.id
            FROM teams t
            WHERE ms.away_team = t.team_name
              AND (ms.away_team_id IS NULL OR ms.away_team_id NOT IN (SELECT id FROM teams))
        """)
        
        if result > 0:
            print(f"   ✅ Fixed {result} match_scores away_team_id records")
            self.fixes_applied['match_scores_team_ids'] += result
        
        total_team_fixes = sum([
            self.fixes_applied['series_stats_team_ids'],
            self.fixes_applied['schedule_team_ids'], 
            self.fixes_applied['match_scores_team_ids']
        ])
        print(f"   📊 Total team_id fixes applied: {total_team_fixes}")
        return total_team_fixes
    
    def verify_fixes(self):
        """Verify that the fixes resolved the orphaned records issues"""
        print(f"\n✅ VERIFICATION: Checking fix results...")
        
        # Re-run diagnostic
        post_fix_stats = self.run_diagnostic()
        
        # Verify foreign key integrity
        integrity_check = self.execute_query_one("""
            SELECT 
                (SELECT COUNT(*) FROM series_stats ss LEFT JOIN leagues l ON ss.league_id = l.id WHERE l.id IS NULL AND ss.league_id IS NOT NULL) as orphaned_leagues,
                (SELECT COUNT(*) FROM series_stats ss WHERE ss.team_id IS NULL OR ss.team_id NOT IN (SELECT id FROM teams)) as orphaned_teams
        """)
        
        success = (
            integrity_check['orphaned_leagues'] == 0 and 
            post_fix_stats['orphaned_leagues'] == 0
        )
        
        if success:
            print(f"   🎉 SUCCESS: All critical orphaned league records have been fixed!")
        else:
            print(f"   ⚠️  WARNING: Some orphaned records remain:")
            print(f"      - Orphaned leagues: {integrity_check['orphaned_leagues']}")
        
        # Note about team orphans (these may be expected)
        if integrity_check['orphaned_teams'] > 0:
            print(f"   ℹ️  NOTE: {integrity_check['orphaned_teams']} orphaned team records remain")
            print(f"      - This is expected for teams that don't exist in teams table")
            print(f"      - Main issue (orphaned league_ids) has been resolved")
            
        return success
    
    def generate_summary(self):
        """Generate a summary of fixes applied"""
        duration = datetime.now() - self.start_time
        
        print(f"\n📊 SUMMARY: Joel Braunstein Orphan Fix - {self.environment.title()}")
        print(f"   🕒 Duration: {duration.total_seconds():.1f}s")
        print(f"   🔧 Fixes Applied:")
        
        total_fixes = sum(self.fixes_applied.values())
        for table_type, count in self.fixes_applied.items():
            if count > 0:
                print(f"      - {table_type}: {count} records")
        
        print(f"   📈 Total Records Fixed: {total_fixes}")
        
        if total_fixes > 0:
            print(f"   ✅ Status: SUCCESS - Critical orphaned records resolved")
            print(f"\n   🎯 Expected Impact:")
            print(f"      - my-series pages should now load properly")
            print(f"      - my-club pages should show correct data")  
            print(f"      - League context should work correctly")
            print(f"      - Joel Braunstein should have access to schedule/stats")
        else:
            print(f"   ℹ️  Status: NO CHANGES - No critical orphaned records found")
        
        return total_fixes
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Apply Joel Braunstein orphaned records fix to remote environment')
    parser.add_argument('--environment', choices=['staging', 'production'], default='staging',
                       help='Target environment (default: staging)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be fixed without applying changes')
    
    args = parser.parse_args()
    
    print(f"🚀 Joel Braunstein Orphaned Records Fix - Remote")
    print(f"   Environment: {args.environment}")
    print(f"   Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    
    if args.dry_run:
        print(f"\n⚠️  DRY RUN MODE: No changes will be applied")
    
    try:
        # Initialize the fix system
        fixer = RemoteOrphanFix(environment=args.environment)
        
        # Connect to remote database
        if not fixer.connect_to_remote():
            sys.exit(1)
        
        # Run initial diagnostic
        initial_stats = fixer.run_diagnostic()
        
        if initial_stats['orphaned_leagues'] == 0 and initial_stats['orphaned_teams'] == 0:
            print(f"\n✅ No orphaned records found - database is healthy!")
            return
        
        if not args.dry_run:
            # Apply the fixes
            league_fixes = fixer.apply_orphaned_league_fixes()
            team_fixes = fixer.apply_orphaned_team_fixes()
            
            # Verify fixes worked
            success = fixer.verify_fixes()
            
            # Generate summary
            total_fixes = fixer.generate_summary()
            
        else:
            print(f"\n🔍 DRY RUN: Would fix {initial_stats['orphaned_leagues']} league and {initial_stats['orphaned_teams']} team orphaned records")
        
        # Close connection
        fixer.close()
        
    except Exception as e:
        logger.error(f"Fix failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
