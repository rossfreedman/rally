#!/usr/bin/env python3
"""
Check Schedule League Breakdown
==============================

Check which leagues have schedule entries with NULL team_ids.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import get_db

def main():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get breakdown by league
        cursor.execute("""
            SELECT l.league_name, l.league_id, COUNT(*) as null_count
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE (s.home_team_id IS NULL OR s.away_team_id IS NULL)
            GROUP BY l.league_name, l.league_id
            ORDER BY null_count DESC
        """)
        
        print("📊 Schedule NULL team_ids by League:")
        print("=" * 50)
        
        total_null = 0
        for league_name, league_id, null_count in cursor.fetchall():
            print(f"{league_name} (ID: {league_id}): {null_count:,} entries")
            total_null += null_count
        
        print(f"\n📊 Total NULL entries: {total_null:,}")
        
        # Check total schedule entries by league
        cursor.execute("""
            SELECT l.league_name, COUNT(*) as total_count
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            GROUP BY l.league_name
            ORDER BY total_count DESC
        """)
        
        print(f"\n📊 Total Schedule Entries by League:")
        print("=" * 50)
        
        for league_name, total_count in cursor.fetchall():
            print(f"{league_name}: {total_count:,} entries")

if __name__ == "__main__":
    main() 