#!/usr/bin/env python3
"""
Analyze CNSWPL Team Mapping Patterns
===================================

Analyze the team naming patterns in CNSWPL to understand how to map
schedule team names to teams table names.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import get_db

def main():
    with get_db() as conn:
        cursor = conn.cursor()
        
        print("🔍 CNSWPL Team Mapping Analysis")
        print("=" * 60)
        
        # Get all CNSWPL schedule team names
        print("\n📅 CNSWPL Schedule Team Names:")
        print("-" * 40)
        cursor.execute("""
            SELECT DISTINCT s.home_team, s.away_team
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
            ORDER BY s.home_team, s.away_team
            LIMIT 20
        """)
        
        schedule_teams = set()
        for home, away in cursor.fetchall():
            schedule_teams.add(home)
            schedule_teams.add(away)
            print(f"  {home}")
            print(f"  {away}")
        
        # Get all CNSWPL teams from teams table
        print(f"\n🏆 CNSWPL Teams Table Names:")
        print("-" * 40)
        cursor.execute("""
            SELECT DISTINCT t.team_name
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
            ORDER BY t.team_name
        """)
        
        teams_table_teams = set()
        for (team_name,) in cursor.fetchall():
            teams_table_teams.add(team_name)
            print(f"  {team_name}")
        
        # Analyze patterns
        print(f"\n🔍 Pattern Analysis:")
        print("-" * 40)
        
        # Look for common prefixes
        schedule_prefixes = set()
        for team in schedule_teams:
            if ' - Series ' in team:
                prefix = team.split(' - Series ')[0]
                schedule_prefixes.add(prefix)
        
        teams_prefixes = set()
        for team in teams_table_teams:
            # Teams table seems to have simpler names
            teams_prefixes.add(team)
        
        print(f"Schedule prefixes: {sorted(schedule_prefixes)}")
        print(f"Teams table names: {sorted(teams_prefixes)}")
        
        # Try to find matches
        print(f"\n🔗 Potential Matches:")
        print("-" * 40)
        
        matches_found = 0
        for schedule_team in sorted(schedule_teams):
            if ' - Series ' in schedule_team:
                prefix = schedule_team.split(' - Series ')[0]
                series_part = schedule_team.split(' - Series ')[1]
                
                # Look for exact prefix match
                if prefix in teams_table_teams:
                    print(f"✅ {schedule_team} → {prefix}")
                    matches_found += 1
                else:
                    # Look for partial matches
                    potential_matches = [t for t in teams_table_teams if prefix.lower() in t.lower() or t.lower() in prefix.lower()]
                    if potential_matches:
                        print(f"🔍 {schedule_team} → potential: {potential_matches}")
                    else:
                        print(f"❌ {schedule_team} → no match found")
        
        print(f"\n📊 Summary:")
        print(f"Schedule teams: {len(schedule_teams)}")
        print(f"Teams table teams: {len(teams_table_teams)}")
        print(f"Direct matches found: {matches_found}")
        
        # Check for specific examples
        print(f"\n📋 Specific Examples:")
        print("-" * 40)
        
        # Get some specific examples with their counts
        cursor.execute("""
            SELECT s.home_team, COUNT(*) as count
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
            GROUP BY s.home_team
            ORDER BY count DESC
            LIMIT 10
        """)
        
        for team_name, count in cursor.fetchall():
            print(f"  {team_name} ({count} matches)")

if __name__ == "__main__":
    main() 