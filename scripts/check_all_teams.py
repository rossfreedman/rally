#!/usr/bin/env python3

import sys

sys.path.append(".")

from database_utils import execute_query

print("🔍 CHECKING ALL TEAMS IN DATABASE...")
print("=" * 60)

try:
    # Get all unique team names
    query = """
    SELECT DISTINCT home_team as team 
    FROM match_scores 
    UNION
    SELECT DISTINCT away_team as team 
    FROM match_scores 
    ORDER BY team
    LIMIT 50
    """

    teams = execute_query(query)
    if teams:
        print(f"Found {len(teams)} teams (showing first 50):")
        for i, team in enumerate(teams, 1):
            print(f'  {i:2d}. "{team["team"]}"')
    else:
        print("❌ No teams found")

    # Look for teams containing "Bridge" (in case of slight name variation)
    print('\n🌉 LOOKING FOR TEAMS CONTAINING "Bridge"...')
    bridge_query = """
    SELECT DISTINCT home_team as team 
    FROM match_scores 
    WHERE home_team LIKE '%Bridge%'
    UNION
    SELECT DISTINCT away_team as team 
    FROM match_scores 
    WHERE away_team LIKE '%Bridge%'
    ORDER BY team
    """

    bridge_teams = execute_query(bridge_query)
    if bridge_teams:
        print(f'Found {len(bridge_teams)} teams with "Bridge":')
        for i, team in enumerate(bridge_teams, 1):
            print(f'  {i}. "{team["team"]}"')
    else:
        print('❌ No teams with "Bridge" found')

    # Check league associations for APTA_CHICAGO
    print("\n🏆 CHECKING APTA_CHICAGO TEAMS...")
    apta_query = """
    SELECT DISTINCT team 
    FROM series_stats 
    WHERE league_id = (SELECT id FROM leagues WHERE league_id = 'APTA_CHICAGO')
    ORDER BY team
    LIMIT 20
    """

    apta_teams = execute_query(apta_query)
    if apta_teams:
        print(f"Found {len(apta_teams)} APTA_CHICAGO teams (showing first 20):")
        for i, team in enumerate(apta_teams, 1):
            print(f'  {i:2d}. "{team["team"]}"')
    else:
        print("❌ No APTA_CHICAGO teams found")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
