#!/usr/bin/env python3
"""
Apply Practice Times Fix
========================

Direct application of practice times fix based on known patterns.
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db

def apply_practice_times_fix():
    """Apply practice times fix directly"""
    
    print("🔧 APPLYING PRACTICE TIMES FIX")
    print("=" * 40)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            # Get the Tennaqua Series 22 team (APTA_CHICAGO)
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
            
            # Get the Tennaqua S2B team (NSTF)
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
            
            print(f"Found teams:")
            if series_22_team:
                print(f"  • Series 22: {series_22_team[1]} (ID: {series_22_team[0]})")
            if series_2b_team:
                print(f"  • Series 2B: {series_2b_team[1]} (ID: {series_2b_team[0]})")
            
            if not series_22_team or not series_2b_team:
                print("❌ Could not find required teams")
                return False
            
            # Fix Friday 21:00 practices (Series 22)
            cursor.execute("""
                UPDATE practice_times 
                SET team_id = %s
                WHERE team_id IN (
                    SELECT pt.team_id FROM practice_times pt
                    LEFT JOIN teams t ON pt.team_id = t.id
                    WHERE pt.team_id IS NOT NULL AND t.id IS NULL
                    AND pt.day_of_week = 'Friday' AND pt.start_time = '21:00:00'
                )
            """, (series_22_team[0],))
            friday_fixed = cursor.rowcount
            
            # Fix Saturday 19:00 practices (Series 2B)
            cursor.execute("""
                UPDATE practice_times 
                SET team_id = %s
                WHERE team_id IN (
                    SELECT pt.team_id FROM practice_times pt
                    LEFT JOIN teams t ON pt.team_id = t.id
                    WHERE pt.team_id IS NOT NULL AND t.id IS NULL
                    AND pt.day_of_week = 'Saturday' AND pt.start_time = '19:00:00'
                )
            """, (series_2b_team[0],))
            saturday_fixed = cursor.rowcount
            
            # Fix any remaining orphaned practice times (use Series 22 as default)
            cursor.execute("""
                UPDATE practice_times 
                SET team_id = %s
                WHERE team_id IN (
                    SELECT pt.team_id FROM practice_times pt
                    LEFT JOIN teams t ON pt.team_id = t.id
                    WHERE pt.team_id IS NOT NULL AND t.id IS NULL
                )
            """, (series_22_team[0],))
            remaining_fixed = cursor.rowcount
            
            total_fixed = friday_fixed + saturday_fixed + remaining_fixed
            
            print(f"\nFixed practice times:")
            print(f"  • Friday 21:00 (Series 22): {friday_fixed}")
            print(f"  • Saturday 19:00 (Series 2B): {saturday_fixed}")
            print(f"  • Remaining (Series 22): {remaining_fixed}")
            print(f"  • Total fixed: {total_fixed}")
            
            # Verify fix
            cursor.execute("""
                SELECT COUNT(*) FROM practice_times pt
                LEFT JOIN teams t ON pt.team_id = t.id
                WHERE pt.team_id IS NOT NULL AND t.id IS NULL
            """)
            remaining_orphaned = cursor.fetchone()[0]
            
            print(f"\nRemaining orphaned practice times: {remaining_orphaned}")
            
            if remaining_orphaned == 0:
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
    success = apply_practice_times_fix()
    
    if success:
        print("\n🎉 Practice times fix completed successfully!")
    else:
        print("\n❌ Practice times fix failed")
    
    sys.exit(0 if success else 1) 