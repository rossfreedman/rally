#!/usr/bin/env python3
"""
Check CNSWPL Non-Pattern Teams
==============================

Check for CNSWPL teams that don't follow the " - Series X" pattern.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import get_db

def main():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check for CNSWPL teams that don't follow the pattern
        cursor.execute("""
            SELECT DISTINCT s.home_team
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'CNSWPL' 
              AND s.home_team_id IS NULL
              AND s.home_team NOT LIKE '% - Series %'
        """)
        
        non_pattern_teams = cursor.fetchall()
        print(f"Teams not following pattern: {len(non_pattern_teams)}")
        for (team,) in non_pattern_teams:
            print(f"  {team}")
        
        # Check total CNSWPL NULL entries
        cursor.execute("""
            SELECT COUNT(*) as null_count
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'CNSWPL' 
              AND (s.home_team_id IS NULL OR s.away_team_id IS NULL)
        """)
        
        total_null = cursor.fetchone()[0]
        print(f"\nTotal CNSWPL NULL entries: {total_null}")

if __name__ == "__main__":
    main() 