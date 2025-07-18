#!/usr/bin/env python3
"""
Fix CNSWPL Schedule Team Mappings
=================================

Fix CNSWPL schedule entries with NULL team_ids by applying the same
normalization logic used for NSTF (removing " - Series X" suffix).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import get_db

def normalize_team_name_for_matching(team_name: str) -> str:
    """Normalize team name by removing ' - Series X' suffix for matching"""
    if " - Series " in team_name:
        return team_name.split(" - Series ")[0]
    return team_name

def main():
    print("🔧 Fixing CNSWPL Schedule Team Mappings")
    print("=" * 50)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check current status
        cursor.execute("""
            SELECT COUNT(*) as null_count
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'CNSWPL' 
              AND (s.home_team_id IS NULL OR s.away_team_id IS NULL)
        """)
        initial_null_count = cursor.fetchone()[0]
        
        print(f"📊 Initial CNSWPL NULL team_ids: {initial_null_count}")
        
        if initial_null_count == 0:
            print("✅ No CNSWPL entries need fixing!")
            return
        
        # Fix home team mappings
        print("\n🔧 Fixing home team mappings...")
        cursor.execute("""
            SELECT DISTINCT s.id, s.home_team, s.league_id
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
              AND s.home_team_id IS NULL 
              AND s.home_team != 'BYE'
        """)
        home_team_fixes = cursor.fetchall()
        
        home_fixes = 0
        for schedule_id, team_name, league_db_id in home_team_fixes:
            # Try exact match first
            cursor.execute("""
                SELECT t.id FROM teams t
                WHERE t.league_id = %s AND t.team_name = %s
            """, (league_db_id, team_name))
            team_row = cursor.fetchone()
            
            if not team_row:
                # Try normalized match (remove " - Series X" suffix)
                normalized_team_name = normalize_team_name_for_matching(team_name)
                cursor.execute("""
                    SELECT t.id FROM teams t
                    WHERE t.league_id = %s AND t.team_name = %s
                """, (league_db_id, normalized_team_name))
                team_row = cursor.fetchone()
            
            if team_row:
                cursor.execute("""
                    UPDATE schedule SET home_team_id = %s WHERE id = %s
                """, (team_row[0], schedule_id))
                home_fixes += 1
                print(f"  ✅ Fixed: {team_name} → team_id {team_row[0]}")
            else:
                print(f"  ❌ No match found: {team_name}")
        
        # Fix away team mappings
        print("\n🔧 Fixing away team mappings...")
        cursor.execute("""
            SELECT DISTINCT s.id, s.away_team, s.league_id
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
              AND s.away_team_id IS NULL 
              AND s.away_team != 'BYE'
        """)
        away_team_fixes = cursor.fetchall()
        
        away_fixes = 0
        for schedule_id, team_name, league_db_id in away_team_fixes:
            # Try exact match first
            cursor.execute("""
                SELECT t.id FROM teams t
                WHERE t.league_id = %s AND t.team_name = %s
            """, (league_db_id, team_name))
            team_row = cursor.fetchone()
            
            if not team_row:
                # Try normalized match (remove " - Series X" suffix)
                normalized_team_name = normalize_team_name_for_matching(team_name)
                cursor.execute("""
                    SELECT t.id FROM teams t
                    WHERE t.league_id = %s AND t.team_name = %s
                """, (league_db_id, normalized_team_name))
                team_row = cursor.fetchone()
            
            if team_row:
                cursor.execute("""
                    UPDATE schedule SET away_team_id = %s WHERE id = %s
                """, (team_row[0], schedule_id))
                away_fixes += 1
                print(f"  ✅ Fixed: {team_name} → team_id {team_row[0]}")
            else:
                print(f"  ❌ No match found: {team_name}")
        
        # Check final status
        cursor.execute("""
            SELECT COUNT(*) as remaining_null_count
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'CNSWPL' 
              AND (s.home_team_id IS NULL OR s.away_team_id IS NULL)
        """)
        final_null_count = cursor.fetchone()[0]
        
        conn.commit()
        
        print(f"\n📊 Summary:")
        print(f"  Home team fixes: {home_fixes}")
        print(f"  Away team fixes: {away_fixes}")
        print(f"  Total fixes: {home_fixes + away_fixes}")
        print(f"  Remaining NULL entries: {final_null_count}")
        print(f"  Success rate: {((initial_null_count - final_null_count) / initial_null_count * 100):.1f}%")
        
        if final_null_count == 0:
            print("🎉 All CNSWPL schedule team mappings fixed successfully!")
        else:
            print(f"⚠️  {final_null_count} CNSWPL entries still have NULL team_ids")

if __name__ == "__main__":
    main() 