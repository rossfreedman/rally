#!/usr/bin/env python3
"""
Check Problematic Team Names
===========================

Examine team names in leagues with high NULL team_id rates.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import get_db

def main():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check CITA team names
        print("🏆 CITA Team Names (from schedule):")
        print("=" * 50)
        cursor.execute("""
            SELECT DISTINCT s.home_team, s.away_team
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'CITA'
            LIMIT 10
        """)
        
        for home, away in cursor.fetchall():
            print(f"  {home} vs {away}")
        
        # Check CNSWPL team names
        print(f"\n🏆 CNSWPL Team Names (from schedule):")
        print("=" * 50)
        cursor.execute("""
            SELECT DISTINCT s.home_team, s.away_team
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
            LIMIT 10
        """)
        
        for home, away in cursor.fetchall():
            print(f"  {home} vs {away}")
        
        # Check what teams exist in teams table for these leagues
        print(f"\n🏆 Teams in teams table for CITA:")
        print("=" * 50)
        cursor.execute("""
            SELECT t.team_name, COUNT(*) as count
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            WHERE l.league_id = 'CITA'
            GROUP BY t.team_name
            ORDER BY count DESC
            LIMIT 10
        """)
        
        for team_name, count in cursor.fetchall():
            print(f"  {team_name} ({count} players)")
        
        print(f"\n🏆 Teams in teams table for CNSWPL:")
        print("=" * 50)
        cursor.execute("""
            SELECT t.team_name, COUNT(*) as count
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
            GROUP BY t.team_name
            ORDER BY count DESC
            LIMIT 10
        """)
        
        for team_name, count in cursor.fetchall():
            print(f"  {team_name} ({count} players)")

if __name__ == "__main__":
    main() 