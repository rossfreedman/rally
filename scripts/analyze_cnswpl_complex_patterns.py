#!/usr/bin/env python3
"""
Analyze CNSWPL Complex Team Patterns
===================================

Analyze the complex team naming patterns in CNSWPL to understand how to map
schedule team names to teams table names.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import get_db
import re

def main():
    with get_db() as conn:
        cursor = conn.cursor()
        
        print("🔍 CNSWPL Complex Team Pattern Analysis")
        print("=" * 60)
        
        # Get some examples of failed matches
        print("\n📅 Examples of Failed Schedule Team Names:")
        print("-" * 50)
        cursor.execute("""
            SELECT DISTINCT s.home_team
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
              AND s.home_team_id IS NULL
            LIMIT 20
        """)
        
        failed_teams = [row[0] for row in cursor.fetchall()]
        for team in failed_teams:
            print(f"  {team}")
        
        # Get corresponding teams from teams table
        print(f"\n🏆 CNSWPL Teams Table (sample):")
        print("-" * 50)
        cursor.execute("""
            SELECT DISTINCT t.team_name
            FROM teams t
            JOIN leagues l ON t.league_id = l.id
            WHERE l.league_id = 'CNSWPL'
            ORDER BY t.team_name
            LIMIT 30
        """)
        
        teams_table_teams = [row[0] for row in cursor.fetchall()]
        for team in teams_table_teams:
            print(f"  {team}")
        
        # Analyze patterns
        print(f"\n🔍 Pattern Analysis:")
        print("-" * 50)
        
        # Look for common patterns in failed teams
        patterns = {}
        for team in failed_teams:
            if " - Series " in team:
                base_part = team.split(" - Series ")[0]
                series_part = team.split(" - Series ")[1]
                
                # Extract club name and number
                # Pattern: "Club Name X(suffix) - Series Y"
                match = re.match(r'^(.+?)\s+(\d+[a-z]?)(?:\([^)]+\))?$', base_part)
                if match:
                    club_name = match.group(1).strip()
                    team_number = match.group(2)
                    key = f"{club_name} {team_number}"
                    if key not in patterns:
                        patterns[key] = []
                    patterns[key].append(team)
        
        print("Extracted patterns:")
        for key, examples in list(patterns.items())[:10]:
            print(f"  {key} → {examples[0]}")
        
        # Try to find matches
        print(f"\n🔗 Potential Matches:")
        print("-" * 50)
        
        matches_found = 0
        for team in failed_teams[:20]:  # Test first 20
            if " - Series " in team:
                base_part = team.split(" - Series ")[0]
                
                # Try different extraction methods
                potential_matches = []
                
                # Method 1: Remove everything after first parenthesis
                clean_name = re.sub(r'\([^)]*\)', '', base_part).strip()
                if clean_name in teams_table_teams:
                    potential_matches.append(clean_name)
                
                # Method 2: Extract club + number pattern
                match = re.match(r'^(.+?)\s+(\d+[a-z]?)(?:\([^)]+\))?$', base_part)
                if match:
                    club_name = match.group(1).strip()
                    team_number = match.group(2)
                    simple_name = f"{club_name} {team_number}"
                    if simple_name in teams_table_teams:
                        potential_matches.append(simple_name)
                
                # Method 3: Remove all suffixes
                clean_name2 = re.sub(r'\([^)]*\)', '', base_part)
                clean_name2 = re.sub(r'\s+[a-z]$', '', clean_name2).strip()
                if clean_name2 in teams_table_teams:
                    potential_matches.append(clean_name2)
                
                if potential_matches:
                    print(f"✅ {team} → {potential_matches[0]}")
                    matches_found += 1
                else:
                    print(f"❌ {team} → no match")
        
        print(f"\n📊 Summary:")
        print(f"Patterns analyzed: {len(patterns)}")
        print(f"Test matches found: {matches_found}/20")

if __name__ == "__main__":
    main() 