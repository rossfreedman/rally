#!/usr/bin/env python3
"""
Apply Practice Times Fix Final
===============================

Handle orphaned practice times by consolidating duplicates.
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db

def apply_practice_times_fix_final():
    """Apply practice times fix by consolidating duplicates"""
    
    print("🔧 APPLYING PRACTICE TIMES FIX - FINAL")
    print("=" * 45)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            # Step 1: Check current orphaned practice times
            cursor.execute("""
                SELECT COUNT(*) FROM practice_times pt
                LEFT JOIN teams t ON pt.team_id = t.id
                WHERE pt.team_id IS NOT NULL AND t.id IS NULL
            """)
            orphaned_count = cursor.fetchone()[0]
            print(f"Found {orphaned_count} orphaned practice times")
            
            if orphaned_count == 0:
                print("✅ No orphaned practice times to fix")
                return True
            
            # Step 2: Get target teams
            cursor.execute("""
                SELECT t.id, t.team_name 
                FROM teams t
                JOIN leagues l ON t.league_id = l.id
                WHERE l.league_id = 'APTA_CHICAGO'
                AND t.team_name LIKE '%Tennaqua%'
                AND (t.team_name LIKE '%- 22%' OR t.team_alias LIKE '%Series 22%')
                LIMIT 1
            """)
            series_22_team = cursor.fetchone()
            
            cursor.execute("""
                SELECT t.id, t.team_name 
                FROM teams t
                JOIN leagues l ON t.league_id = l.id
                WHERE l.league_id = 'NSTF'
                AND t.team_name LIKE '%Tennaqua%'
                AND (t.team_name LIKE '%S2B%' OR t.team_alias LIKE '%Series 2B%')
                LIMIT 1
            """)
            series_2b_team = cursor.fetchone()
            
            print(f"Target teams:")
            print(f"  • Series 22: {series_22_team[1]} (ID: {series_22_team[0]})")
            print(f"  • Series 2B: {series_2b_team[1]} (ID: {series_2b_team[0]})")
            
            # Step 3: Collect unique practice time patterns from orphaned records
            cursor.execute("""
                SELECT DISTINCT day_of_week, start_time, end_time, location, pt.league_id
                FROM practice_times pt
                LEFT JOIN teams t ON pt.team_id = t.id
                WHERE pt.team_id IS NOT NULL AND t.id IS NULL
                ORDER BY day_of_week, start_time
            """)
            unique_patterns = cursor.fetchall()
            
            print(f"\nFound {len(unique_patterns)} unique practice time patterns:")
            for pattern in unique_patterns:
                day, start, end, location, league_id = pattern
                print(f"  • {day} {start}-{end} at {location} (league {league_id})")
            
            # Step 4: Delete all orphaned practice times
            print(f"\nDeleting {orphaned_count} orphaned practice times...")
            cursor.execute("""
                DELETE FROM practice_times pt
                WHERE pt.team_id IN (
                    SELECT pt2.team_id FROM practice_times pt2
                    LEFT JOIN teams t ON pt2.team_id = t.id
                    WHERE pt2.team_id IS NOT NULL AND t.id IS NULL
                )
            """)
            deleted_count = cursor.rowcount
            print(f"✅ Deleted {deleted_count} orphaned practice times")
            
            # Step 5: Create clean practice times based on patterns
            created_count = 0
            
            for pattern in unique_patterns:
                day, start, end, location, old_league_id = pattern
                
                # Determine target team based on pattern
                if day == 'Friday' and start.hour == 21:
                    # Friday 21:00 -> Series 22
                    target_team_id = series_22_team[0]
                    target_league_id = 4911  # Current APTA_CHICAGO league ID
                    team_name = series_22_team[1]
                elif day == 'Saturday' and start.hour == 19:
                    # Saturday 19:00 -> Series 2B
                    target_team_id = series_2b_team[0]
                    target_league_id = 4914  # Current NSTF league ID
                    team_name = series_2b_team[1]
                else:
                    # Default to Series 22 for other patterns
                    target_team_id = series_22_team[0]
                    target_league_id = 4911  # Current APTA_CHICAGO league ID
                    team_name = series_22_team[1]
                
                # Insert the clean practice time
                try:
                    cursor.execute("""
                        INSERT INTO practice_times (team_id, day_of_week, start_time, end_time, location, league_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (target_team_id, day, start, end, location, target_league_id))
                    
                    created_count += 1
                    print(f"   ✅ Created: {day} {start}-{end} for {team_name}")
                    
                except Exception as e:
                    # Handle constraint violations gracefully
                    if "duplicate key" in str(e):
                        print(f"   ⚠️  Skipped duplicate: {day} {start}-{end} for {team_name}")
                    else:
                        print(f"   ❌ Error creating practice time: {str(e)}")
            
            print(f"\n✅ Created {created_count} clean practice times")
            
            # Step 6: Final verification
            cursor.execute("""
                SELECT COUNT(*) FROM practice_times pt
                LEFT JOIN teams t ON pt.team_id = t.id
                WHERE pt.team_id IS NOT NULL AND t.id IS NULL
            """)
            final_orphaned = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM practice_times")
            total_practice_times = cursor.fetchone()[0]
            
            print(f"\nFinal status:")
            print(f"  • Total practice times: {total_practice_times}")
            print(f"  • Orphaned practice times: {final_orphaned}")
            
            if final_orphaned == 0:
                conn.commit()
                print("✅ All practice times fixed successfully!")
                return True
            else:
                conn.rollback()
                print("❌ Some practice times still orphaned")
                return False
                
        except Exception as e:
            conn.rollback()
            print(f"❌ Error: {str(e)}")
            return False

if __name__ == "__main__":
    success = apply_practice_times_fix_final()
    
    if success:
        print("\n🎉 Practice times fix completed successfully!")
    else:
        print("\n❌ Practice times fix failed")
    
    sys.exit(0 if success else 1) 