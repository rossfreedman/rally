#!/usr/bin/env python3
"""
Check CNSWPL Series Mapping
===========================

Check if there's a mapping between CNSWPL letter series (A, B, C, etc.)
and numeric series (1, 2, 3, etc.) in the teams table.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import get_db

def main():
    with get_db() as conn:
        cursor = conn.cursor()
        
        print("🔍 CNSWPL Series Mapping Analysis")
        print("=" * 50)
        
        # Get all unique series from schedule
        print("\n📅 Schedule Series (letter-based):")
        print("-" * 40)
        cursor.execute("""
            SELECT DISTINCT 
                SUBSTRING(s.home_team FROM ' - Series (.+)$') as series_letter
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
              AND s.home_team LIKE '% - Series %'
            ORDER BY series_letter
        """)
        
        schedule_series = [row[0] for row in cursor.fetchall() if row[0]]
        for series in schedule_series:
            print(f"  {series}")
        
        # Get all unique series from teams table
        print(f"\n🏆 Teams Table Series (numeric):")
        print("-" * 40)
        cursor.execute("""
            SELECT DISTINCT 
                SUBSTRING(t.team_name FROM ' (\d+[a-z]?)$') as series_number
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
            ORDER BY series_number
        """)
        
        teams_series = [row[0] for row in cursor.fetchall() if row[0]]
        for series in teams_series:
            print(f"  {series}")
        
        # Check if there are any teams that exist in both formats
        print(f"\n🔗 Cross-Reference Check:")
        print("-" * 40)
        
        # Get some examples of teams that might exist in both formats
        cursor.execute("""
            SELECT DISTINCT 
                SUBSTRING(s.home_team FROM '^(.+?) - Series') as club_base,
                SUBSTRING(s.home_team FROM ' - Series (.+)$') as series_letter
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
              AND s.home_team LIKE '% - Series %'
            LIMIT 10
        """)
        
        for club_base, series_letter in cursor.fetchall():
            if club_base and series_letter:
                # Look for corresponding numeric team
                cursor.execute("""
                    SELECT t.team_name
                    FROM teams t
                    JOIN leagues l ON t.league_id = l.id
                    WHERE l.league_id = 'CNSWPL'
                      AND t.team_name LIKE %s
                    LIMIT 5
                """, (f"{club_base}%",))
                
                matching_teams = [row[0] for row in cursor.fetchall()]
                if matching_teams:
                    print(f"  {club_base} - Series {series_letter} → {matching_teams}")
                else:
                    print(f"  {club_base} - Series {series_letter} → no matches")
        
        # Check if there's a series_mappings table
        print(f"\n🗂️  Series Mappings Table Check:")
        print("-" * 40)
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name LIKE '%series%' 
              AND table_schema = 'public'
        """)
        
        series_tables = [row[0] for row in cursor.fetchall()]
        for table in series_tables:
            print(f"  Found table: {table}")
            
            # Check if it has CNSWPL mappings
            try:
                cursor.execute(f"""
                    SELECT * FROM {table} 
                    WHERE league_id = 'CNSWPL' 
                    LIMIT 5
                """)
                mappings = cursor.fetchall()
                if mappings:
                    print(f"    Has CNSWPL mappings: {len(mappings)} rows")
                    for mapping in mappings:
                        print(f"      {mapping}")
            except Exception as e:
                print(f"    Error querying {table}: {e}")

if __name__ == "__main__":
    main() 