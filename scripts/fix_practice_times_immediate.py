#!/usr/bin/env python3
"""
Fix Practice Times Immediately
==============================

This script directly fixes orphaned practice times using the team_mapping_backup table.

Usage:
    python scripts/fix_practice_times_immediate.py [--dry-run]
"""

import sys
import os
import argparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db

def fix_practice_times_immediate(dry_run=False):
    """Fix orphaned practice times using direct database queries"""
    
    print("🔧 FIXING PRACTICE TIMES IMMEDIATELY")
    print("=" * 50)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            # Step 1: Check current status
            print("🔍 Step 1: Checking current practice times status...")
            
            # Check practice_times table for orphaned records
            cursor.execute("""
                SELECT COUNT(*) FROM practice_times pt
                LEFT JOIN teams t ON pt.team_id = t.id
                WHERE pt.team_id IS NOT NULL AND t.id IS NULL
            """)
            orphaned_practice_times = cursor.fetchone()[0]
            
            # Check schedule table for orphaned practice times
            cursor.execute("""
                SELECT COUNT(*) FROM schedule s
                LEFT JOIN teams t ON s.home_team_id = t.id
                WHERE s.home_team_id IS NOT NULL AND t.id IS NULL
                AND (s.home_team LIKE '%Practice%' OR s.home_team LIKE '%practice%')
            """)
            orphaned_schedule_practice = cursor.fetchone()[0]
            
            print(f"   • Orphaned practice times in practice_times table: {orphaned_practice_times}")
            print(f"   • Orphaned practice times in schedule table: {orphaned_schedule_practice}")
            
            if orphaned_practice_times == 0 and orphaned_schedule_practice == 0:
                print("✅ No orphaned practice times found!")
                return True
            
            # Step 2: Check if team_mapping_backup exists
            print("\n🗺️  Step 2: Checking for team mapping backup...")
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'team_mapping_backup'
                )
            """)
            team_mapping_exists = cursor.fetchone()[0]
            
            if not team_mapping_exists:
                print("❌ No team_mapping_backup table found - cannot map teams")
                return False
            
            cursor.execute("SELECT COUNT(*) FROM team_mapping_backup")
            mapping_count = cursor.fetchone()[0]
            print(f"   ✅ Found team_mapping_backup with {mapping_count} mappings")
            
            # Step 3: Fix practice_times table
            if orphaned_practice_times > 0:
                print(f"\n🔧 Step 3: Fixing {orphaned_practice_times} orphaned practice times...")
                
                if dry_run:
                    # Show what would be fixed
                    cursor.execute("""
                        SELECT pt.id, pt.team_id, pt.day_of_week, pt.start_time, pt.location,
                               tmb.old_team_name, tmb.old_team_alias, tmb.old_league_string_id,
                               new_teams.id as new_team_id, new_teams.team_name as new_team_name
                        FROM practice_times pt
                        LEFT JOIN teams t ON pt.team_id = t.id
                        LEFT JOIN team_mapping_backup tmb ON pt.team_id = tmb.old_team_id
                        LEFT JOIN teams new_teams ON (
                            new_teams.team_name = tmb.old_team_name
                            OR new_teams.team_alias = tmb.old_team_alias
                        )
                        LEFT JOIN leagues l ON new_teams.league_id = l.id AND l.league_id = tmb.old_league_string_id
                        WHERE pt.team_id IS NOT NULL AND t.id IS NULL
                        ORDER BY pt.id
                    """)
                    would_fix = cursor.fetchall()
                    
                    print("   🧪 DRY RUN - Would fix:")
                    for fix in would_fix:
                        if fix[8]:  # new_team_id exists
                            print(f"      Practice {fix[0]}: {fix[1]} → {fix[8]} ({fix[9]} - {fix[7]})")
                        else:
                            print(f"      Practice {fix[0]}: {fix[1]} → NO MAPPING FOUND (was {fix[5]})")
                
                else:
                    # Apply the fix using team_mapping_backup + current teams
                    cursor.execute("""
                        UPDATE practice_times 
                        SET team_id = new_teams.id
                        FROM team_mapping_backup tmb
                        JOIN teams new_teams ON (
                            new_teams.team_name = tmb.old_team_name
                            OR new_teams.team_alias = tmb.old_team_alias
                        )
                        JOIN leagues l ON new_teams.league_id = l.id AND l.league_id = tmb.old_league_string_id
                        WHERE practice_times.team_id = tmb.old_team_id
                        AND practice_times.team_id IN (
                            SELECT pt.team_id FROM practice_times pt
                            LEFT JOIN teams t ON pt.team_id = t.id
                            WHERE pt.team_id IS NOT NULL AND t.id IS NULL
                        )
                    """)
                    fixed_count = cursor.rowcount
                    print(f"   ✅ Fixed {fixed_count} practice times using team mapping")
            
            # Step 4: Fix schedule table practice times
            if orphaned_schedule_practice > 0:
                print(f"\n🔧 Step 4: Fixing {orphaned_schedule_practice} orphaned schedule practice times...")
                
                if dry_run:
                    print("   🧪 DRY RUN - Would fix schedule practice times")
                else:
                    cursor.execute("""
                        UPDATE schedule 
                        SET home_team_id = new_teams.id
                        FROM team_mapping_backup tmb
                        JOIN teams new_teams ON (
                            new_teams.team_name = tmb.old_team_name
                            OR new_teams.team_alias = tmb.old_team_alias
                        )
                        JOIN leagues l ON new_teams.league_id = l.id AND l.league_id = tmb.old_league_string_id
                        WHERE schedule.home_team_id = tmb.old_team_id
                        AND schedule.home_team_id IN (
                            SELECT s.home_team_id FROM schedule s
                            LEFT JOIN teams t ON s.home_team_id = t.id
                            WHERE s.home_team_id IS NOT NULL AND t.id IS NULL
                            AND (s.home_team LIKE '%Practice%' OR s.home_team LIKE '%practice%')
                        )
                    """)
                    fixed_schedule_count = cursor.rowcount
                    print(f"   ✅ Fixed {fixed_schedule_count} schedule practice times using team mapping")
            
            # Step 5: Handle unmapped practice times
            print("\n🔍 Step 5: Checking for remaining orphaned practice times...")
            
            # Check for practice times that couldn't be mapped
            cursor.execute("""
                SELECT pt.id, pt.team_id, pt.day_of_week, pt.start_time, pt.location, pt.league_id
                FROM practice_times pt
                LEFT JOIN teams t ON pt.team_id = t.id
                WHERE pt.team_id IS NOT NULL AND t.id IS NULL
            """)
            remaining_orphans = cursor.fetchall()
            
            if remaining_orphans:
                print(f"   🔧 Found {len(remaining_orphans)} practice times that need pattern matching...")
                
                for practice in remaining_orphans:
                    practice_id, old_team_id, day_of_week, start_time, location, league_id = practice
                    
                    # Try to find matching team by location and league
                    cursor.execute("""
                        SELECT t.id, t.team_name 
                        FROM teams t
                        WHERE t.league_id = %s
                        AND (t.team_name LIKE %s OR t.team_alias LIKE %s)
                        LIMIT 1
                    """, (league_id, f'%{location}%', f'%{location}%'))
                    
                    match = cursor.fetchone()
                    if match and not dry_run:
                        new_team_id, team_name = match
                        cursor.execute("""
                            UPDATE practice_times 
                            SET team_id = %s 
                            WHERE id = %s
                        """, (new_team_id, practice_id))
                        print(f"   ✅ Fixed practice {practice_id}: {old_team_id} → {new_team_id} ({team_name})")
                    elif match and dry_run:
                        print(f"   🧪 Would fix practice {practice_id}: {old_team_id} → {match[0]} ({match[1]})")
                    else:
                        print(f"   ⚠️  Could not find team for practice {practice_id} (location: {location}, league: {league_id})")
            
            # Step 6: Final validation
            print("\n✅ Step 6: Final validation...")
            
            cursor.execute("""
                SELECT COUNT(*) FROM practice_times pt
                LEFT JOIN teams t ON pt.team_id = t.id
                WHERE pt.team_id IS NOT NULL AND t.id IS NULL
            """)
            final_orphaned_practice = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM schedule s
                LEFT JOIN teams t ON s.home_team_id = t.id
                WHERE s.home_team_id IS NOT NULL AND t.id IS NULL
                AND (s.home_team LIKE '%Practice%' OR s.home_team LIKE '%practice%')
            """)
            final_orphaned_schedule = cursor.fetchone()[0]
            
            print(f"   • Final orphaned practice times: {final_orphaned_practice}")
            print(f"   • Final orphaned schedule practice times: {final_orphaned_schedule}")
            
            if not dry_run:
                conn.commit()
                print("   ✅ Changes committed to database")
            else:
                print("   🧪 DRY RUN - No changes made")
            
            success = final_orphaned_practice == 0 and final_orphaned_schedule == 0
            return success
            
        except Exception as e:
            if not dry_run:
                conn.rollback()
            print(f"❌ Error: {str(e)}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Fix orphaned practice times immediately')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Test run without making changes')
    
    args = parser.parse_args()
    
    success = fix_practice_times_immediate(dry_run=args.dry_run)
    
    if success:
        print("\n🎉 Practice times fix completed successfully!")
    else:
        print("\n❌ Practice times fix failed or incomplete")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 