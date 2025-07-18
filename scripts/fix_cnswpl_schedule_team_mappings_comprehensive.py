#!/usr/bin/env python3
"""
Fix CNSWPL Schedule Team Mappings (Comprehensive)
================================================

Fix CNSWPL schedule entries with NULL team_ids by applying normalization logic.
Handles both numeric series (can be fixed) and letter series (cannot be fixed).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import get_db
import re

def normalize_team_name_for_matching(team_name: str) -> str:
    """Normalize team name by removing ' - Series X' suffix for matching"""
    if " - Series " in team_name:
        return team_name.split(" - Series ")[0]
    return team_name

def is_numeric_series(series_name: str) -> bool:
    """Check if series name is numeric (can be mapped)"""
    return series_name.isdigit()

def main():
    print("🔧 Fixing CNSWPL Schedule Team Mappings (Comprehensive)")
    print("=" * 60)
    
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
        
        # Analyze series types
        print("\n🔍 Analyzing Series Types:")
        print("-" * 40)
        
        cursor.execute("""
            SELECT DISTINCT 
                SUBSTRING(s.home_team FROM ' - Series (.+)$') as series_name
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
              AND s.home_team LIKE '% - Series %'
              AND s.home_team_id IS NULL
        """)
        
        series_types = {}
        for (series_name,) in cursor.fetchall():
            if series_name:
                series_type = "numeric" if is_numeric_series(series_name) else "letter"
                if series_type not in series_types:
                    series_types[series_type] = []
                series_types[series_type].append(series_name)
        
        print(f"Numeric series (fixable): {sorted(set(series_types.get('numeric', [])))}")
        print(f"Letter series (not fixable): {sorted(set(series_types.get('letter', [])))}")
        
        # Count entries by series type
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN SUBSTRING(s.home_team FROM ' - Series (.+)$') ~ '^[0-9]+$' THEN 'numeric'
                    ELSE 'letter'
                END as series_type,
                COUNT(*) as count
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
              AND s.home_team_id IS NULL
              AND s.home_team LIKE '% - Series %'
            GROUP BY series_type
        """)
        
        series_counts = dict(cursor.fetchall())
        print(f"\n📊 Entries by series type:")
        print(f"  Numeric series: {series_counts.get('numeric', 0)} entries")
        print(f"  Letter series: {series_counts.get('letter', 0)} entries")
        
        # Fix numeric series entries
        print(f"\n🔧 Fixing numeric series entries...")
        
        # Fix home team mappings for numeric series
        cursor.execute("""
            SELECT DISTINCT s.id, s.home_team, s.league_id
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
              AND s.home_team_id IS NULL 
              AND s.home_team != 'BYE'
              AND SUBSTRING(s.home_team FROM ' - Series (.+)$') ~ '^[0-9]+$'
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
        
        # Fix away team mappings for numeric series
        cursor.execute("""
            SELECT DISTINCT s.id, s.away_team, s.league_id
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
              AND s.away_team_id IS NULL 
              AND s.away_team != 'BYE'
              AND SUBSTRING(s.away_team FROM ' - Series (.+)$') ~ '^[0-9]+$'
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
        
        # Get breakdown of remaining issues
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN SUBSTRING(s.home_team FROM ' - Series (.+)$') ~ '^[0-9]+$' THEN 'numeric'
                    ELSE 'letter'
                END as series_type,
                COUNT(*) as count
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
              AND (s.home_team_id IS NULL OR s.away_team_id IS NULL)
              AND s.home_team LIKE '% - Series %'
            GROUP BY series_type
        """)
        
        remaining_series_counts = dict(cursor.fetchall())
        
        conn.commit()
        
        print(f"\n📊 Summary:")
        print(f"  Home team fixes: {home_fixes}")
        print(f"  Away team fixes: {away_fixes}")
        print(f"  Total fixes: {home_fixes + away_fixes}")
        print(f"  Remaining NULL entries: {final_null_count}")
        print(f"  Success rate: {((initial_null_count - final_null_count) / initial_null_count * 100):.1f}%")
        
        print(f"\n📋 Remaining Issues:")
        print(f"  Numeric series: {remaining_series_counts.get('numeric', 0)} entries")
        print(f"  Letter series: {remaining_series_counts.get('letter', 0)} entries")
        
        if remaining_series_counts.get('letter', 0) > 0:
            print(f"\n⚠️  Note: {remaining_series_counts.get('letter', 0)} entries have letter series (A, B, C, etc.)")
            print(f"   These cannot be mapped because the teams table only has numeric series.")
            print(f"   This indicates a data source mismatch between schedule and teams data.")
        
        if final_null_count == 0:
            print("🎉 All CNSWPL schedule team mappings fixed successfully!")
        elif remaining_series_counts.get('numeric', 0) == 0:
            print("✅ All fixable CNSWPL entries have been fixed!")
            print("   Remaining entries are letter series that require data source alignment.")

if __name__ == "__main__":
    main() 