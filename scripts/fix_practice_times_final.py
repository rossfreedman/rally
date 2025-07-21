#!/usr/bin/env python3
"""
Fix Practice Times Final
========================

This script fixes orphaned practice times using pattern-based matching
when team_mapping_backup doesn't contain the practice time team IDs.

Usage:
    python scripts/fix_practice_times_final.py [--dry-run]
"""

import sys
import os
import argparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db

def fix_practice_times_final(dry_run=False):
    """Fix orphaned practice times using pattern-based matching"""
    
    print("🔧 FIXING PRACTICE TIMES - FINAL APPROACH")
    print("=" * 50)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            # Step 1: Analyze current situation
            print("🔍 Step 1: Analyzing current practice times...")
            
            cursor.execute("""
                SELECT pt.id, pt.team_id, pt.day_of_week, pt.start_time, pt.location, pt.league_id
                FROM practice_times pt
                LEFT JOIN teams t ON pt.team_id = t.id
                WHERE pt.team_id IS NOT NULL AND t.id IS NULL
                ORDER BY pt.league_id, pt.start_time
            """)
            orphaned_practices = cursor.fetchall()
            
            print(f"   Found {len(orphaned_practices)} orphaned practice times")
            
            if len(orphaned_practices) == 0:
                print("✅ No orphaned practice times found!")
                return True
            
            # Step 2: Analyze practice time patterns
            print("\n📊 Step 2: Analyzing practice time patterns...")
            
            # Group by league and time patterns
            league_4903_practices = [p for p in orphaned_practices if p[5] == 4903]  # Old APTA_CHICAGO league
            league_4906_practices = [p for p in orphaned_practices if p[5] == 4906]  # Old NSTF league
            
            print(f"   • League 4903 (old APTA_CHICAGO): {len(league_4903_practices)} practices")
            print(f"   • League 4906 (old NSTF): {len(league_4906_practices)} practices")
            
            # Step 3: Get current teams that match Tennaqua pattern
            print("\n🎯 Step 3: Finding matching current teams...")
            
            cursor.execute("""
                SELECT t.id, t.team_name, t.team_alias, l.league_id, l.id as league_db_id
                FROM teams t
                JOIN leagues l ON t.league_id = l.id
                WHERE t.team_name LIKE '%Tennaqua%'
                ORDER BY l.league_id, t.team_name
            """)
            current_tennaqua_teams = cursor.fetchall()
            
            print(f"   Found {len(current_tennaqua_teams)} current Tennaqua teams:")
            for team in current_tennaqua_teams:
                print(f"      Team {team[0]}: {team[1]} ({team[2]}) - {team[3]}")
            
            # Step 4: Create mapping strategy
            print("\n🗺️  Step 4: Creating mapping strategy...")
            
            fixed_count = 0
            mapping_log = []
            
            for practice in orphaned_practices:
                practice_id, old_team_id, day_of_week, start_time, location, old_league_id = practice
                
                # Strategy 1: Map based on league and common patterns
                if old_league_id == 4903:  # Old APTA_CHICAGO
                    # Look for APTA_CHICAGO teams - prioritize Series 22 for Friday 21:00 practices
                    if day_of_week == 'Friday' and start_time.hour == 21:
                        # This is likely Series 22 practice time
                        cursor.execute("""
                            SELECT t.id, t.team_name 
                            FROM teams t
                            JOIN leagues l ON t.league_id = l.id
                            WHERE l.league_id = 'APTA_CHICAGO'
                            AND t.team_name LIKE '%Tennaqua%'
                            AND (t.team_name LIKE '%- 22%' OR t.team_alias LIKE '%Series 22%')
                            LIMIT 1
                        """)
                        match = cursor.fetchone()
                        
                        if match:
                            new_team_id, team_name = match
                            mapping_log.append((practice_id, old_team_id, new_team_id, team_name, "Series 22 Friday pattern"))
                            if not dry_run:
                                cursor.execute("UPDATE practice_times SET team_id = %s WHERE id = %s", (new_team_id, practice_id))
                                fixed_count += 1
                    
                    else:
                        # General APTA_CHICAGO mapping - use first available Tennaqua team
                        cursor.execute("""
                            SELECT t.id, t.team_name 
                            FROM teams t
                            JOIN leagues l ON t.league_id = l.id
                            WHERE l.league_id = 'APTA_CHICAGO'
                            AND t.team_name LIKE '%Tennaqua%'
                            ORDER BY t.id
                            LIMIT 1
                        """)
                        match = cursor.fetchone()
                        
                        if match:
                            new_team_id, team_name = match
                            mapping_log.append((practice_id, old_team_id, new_team_id, team_name, "APTA_CHICAGO general"))
                            if not dry_run:
                                cursor.execute("UPDATE practice_times SET team_id = %s WHERE id = %s", (new_team_id, practice_id))
                                fixed_count += 1
                
                elif old_league_id == 4906:  # Old NSTF
                    # Look for NSTF teams - prioritize Series 2B for Saturday 19:00 practices
                    if day_of_week == 'Saturday' and start_time.hour == 19:
                        # This is likely Series 2B practice time
                                                 cursor.execute("""
                             SELECT t.id, t.team_name 
                             FROM teams t
                             JOIN leagues l ON t.league_id = l.id
                             WHERE l.league_id = 'NSTF'
                             AND t.team_name LIKE '%Tennaqua%'
                             AND (t.team_name LIKE '%S2B%' OR t.team_alias LIKE '%Series 2B%')
                             LIMIT 1
                         """)
                        match = cursor.fetchone()
                        
                        if match:
                            new_team_id, team_name = match
                            mapping_log.append((practice_id, old_team_id, new_team_id, team_name, "Series 2B Saturday pattern"))
                            if not dry_run:
                                cursor.execute("UPDATE practice_times SET team_id = %s WHERE id = %s", (new_team_id, practice_id))
                                fixed_count += 1
                    
                    else:
                        # General NSTF mapping - use first available Tennaqua team
                        cursor.execute("""
                            SELECT t.id, t.team_name 
                            FROM teams t
                            JOIN leagues l ON t.league_id = l.id
                            WHERE l.league_id = 'NSTF'
                            AND t.team_name LIKE '%Tennaqua%'
                            ORDER BY t.id
                            LIMIT 1
                        """)
                        match = cursor.fetchone()
                        
                        if match:
                            new_team_id, team_name = match
                            mapping_log.append((practice_id, old_team_id, new_team_id, team_name, "NSTF general"))
                            if not dry_run:
                                cursor.execute("UPDATE practice_times SET team_id = %s WHERE id = %s", (new_team_id, practice_id))
                                fixed_count += 1
                
                # If no match found, log it
                if not any(log[0] == practice_id for log in mapping_log):
                    mapping_log.append((practice_id, old_team_id, None, None, "NO MATCH FOUND"))
            
            # Step 5: Show mapping results
            print("\n🔧 Step 5: Mapping results...")
            if dry_run:
                print("   🧪 DRY RUN - Would apply these mappings:")
            else:
                print("   ✅ Applied these mappings:")
            
            for log_entry in mapping_log:
                practice_id, old_team_id, new_team_id, team_name, reason = log_entry
                if new_team_id:
                    print(f"      Practice {practice_id}: {old_team_id} → {new_team_id} ({team_name}) [{reason}]")
                else:
                    print(f"      Practice {practice_id}: {old_team_id} → {reason}")
            
            # Step 6: Final validation
            print("\n✅ Step 6: Final validation...")
            
            cursor.execute("""
                SELECT COUNT(*) FROM practice_times pt
                LEFT JOIN teams t ON pt.team_id = t.id
                WHERE pt.team_id IS NOT NULL AND t.id IS NULL
            """)
            final_orphaned = cursor.fetchone()[0]
            
            print(f"   • Final orphaned practice times: {final_orphaned}")
            
            if not dry_run:
                conn.commit()
                print("   ✅ Changes committed to database")
                print(f"   ✅ Fixed {fixed_count} practice times")
            else:
                print("   🧪 DRY RUN - No changes made")
                successful_mappings = len([log for log in mapping_log if log[2] is not None])
                print(f"   🧪 Would fix {successful_mappings} practice times")
            
            success = final_orphaned == 0 or (dry_run and len(mapping_log) > 0)
            return success
            
        except Exception as e:
            if not dry_run:
                conn.rollback()
            print(f"❌ Error: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Fix orphaned practice times with final approach')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Test run without making changes')
    
    args = parser.parse_args()
    
    success = fix_practice_times_final(dry_run=args.dry_run)
    
    if success:
        print("\n🎉 Practice times fix completed successfully!")
    else:
        print("\n❌ Practice times fix failed or incomplete")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 