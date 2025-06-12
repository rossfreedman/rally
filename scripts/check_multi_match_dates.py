#!/usr/bin/env python3

from database_utils import execute_query
from collections import defaultdict

print('Finding dates with multiple matches to understand court assignment logic...')

# Get all matches for NSTF league (league_id = 3)
all_matches_query = '''
    SELECT 
        TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
        home_team as "Home Team",
        away_team as "Away Team",
        winner as "Winner",
        home_player_1_id as "Home Player 1",
        home_player_2_id as "Home Player 2",
        away_player_1_id as "Away Player 1",
        away_player_2_id as "Away Player 2"
    FROM match_scores
    WHERE league_id = 3
    ORDER BY match_date ASC, home_team, away_team
'''

all_matches = execute_query(all_matches_query, [])
print(f'Found {len(all_matches)} total NSTF matches')

# Group by date
matches_by_date = defaultdict(list)
for match in all_matches:
    matches_by_date[match['Date']].append(match)

# Find dates with multiple matches
print('\nDates with multiple matches:')
multi_match_dates = []
for date, matches in matches_by_date.items():
    if len(matches) > 1:
        multi_match_dates.append((date, matches))
        print(f'  {date}: {len(matches)} matches')
        for i, match in enumerate(matches):
            print(f'    Match {i+1}: {match["Home Team"]} vs {match["Away Team"]}')

if not multi_match_dates:
    print('  No dates found with multiple matches')
    print('\nThis suggests that in NSTF league:')
    print('  - Each match date only has 1 match')
    print('  - All matches should be assigned to Court 1')
    print('  - Court distribution logic should not apply')
else:
    print(f'\nFound {len(multi_match_dates)} dates with multiple matches')
    print('Court assignment should distribute across courts for these dates')

print('\nSample of single-match dates:')
single_match_count = 0
for date, matches in matches_by_date.items():
    if len(matches) == 1:
        single_match_count += 1
        if single_match_count <= 5:  # Show first 5
            print(f'  {date}: {matches[0]["Home Team"]} vs {matches[0]["Away Team"]}')

print(f'\nTotal single-match dates: {single_match_count}')
print(f'Total multi-match dates: {len(multi_match_dates)}') 