#!/usr/bin/env python3

import sys
sys.path.append('.')

from database_utils import execute_query

print('🔍 CHECKING SEVEN BRIDGES TEAM NAMES IN DATABASE...')
print('=' * 60)

# Check what team names contain 'Seven Bridges'
query = """
SELECT DISTINCT home_team as team 
FROM match_scores 
WHERE home_team LIKE '%Seven Bridges%'
UNION
SELECT DISTINCT away_team as team 
FROM match_scores 
WHERE away_team LIKE '%Seven Bridges%'
ORDER BY team
"""

try:
    teams = execute_query(query)
    if teams:
        print(f'Found {len(teams)} Seven Bridges teams in match_scores:')
        for i, team in enumerate(teams, 1):
            print(f'  {i}. "{team["team"]}"')
    else:
        print('❌ No Seven Bridges teams found in match_scores')
        
    # Also check series stats
    print('\n📊 CHECKING SERIES_STATS TABLE...')
    series_query = """
    SELECT DISTINCT team 
    FROM series_stats 
    WHERE team LIKE '%Seven Bridges%'
    ORDER BY team
    """
    series_teams = execute_query(series_query)
    if series_teams:
        print(f'Found {len(series_teams)} Seven Bridges teams in series_stats:')
        for i, team in enumerate(series_teams, 1):
            print(f'  {i}. "{team["team"]}"')
    else:
        print('❌ No Seven Bridges teams found in series_stats')
        
    # Check the specific constructed name
    print('\n🎯 CHECKING CONSTRUCTED NAME: "Seven Bridges - 3"')
    check_query = """
    SELECT COUNT(*) as count FROM match_scores 
    WHERE home_team = %s OR away_team = %s
    """
    result = execute_query(check_query, ['Seven Bridges - 3', 'Seven Bridges - 3'])
    print(f'Matches found for "Seven Bridges - 3": {result[0]["count"]}')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc() 