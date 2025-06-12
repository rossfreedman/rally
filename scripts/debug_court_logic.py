#!/usr/bin/env python3

from database_utils import execute_query
import json

# Check actual match data for Ross Freedman
tenniscores_player_id = 'nndz-WlNhd3hMYi9nQT09'
print(f'Checking match data for player: {tenniscores_player_id}')

# Get all matches for this player
matches_query = '''
    SELECT 
        TO_CHAR(match_date, 'DD-Mon-YY') as "Date",
        home_team as "Home Team",
        away_team as "Away Team",
        winner as "Winner",
        scores as "Scores",
        home_player_1_id as "Home Player 1",
        home_player_2_id as "Home Player 2",
        away_player_1_id as "Away Player 1",
        away_player_2_id as "Away Player 2",
        league_id
    FROM match_scores
    WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
    ORDER BY match_date ASC
'''

matches = execute_query(matches_query, [tenniscores_player_id, tenniscores_player_id, tenniscores_player_id, tenniscores_player_id])
print(f'Found {len(matches)} total matches for this player')

if matches:
    print('\nMatch details:')
    for i, match in enumerate(matches):
        print(f'  Match {i+1}: {match["Date"]} - {match["Home Team"]} vs {match["Away Team"]} - Winner: {match["Winner"]}')
        
        # Show where the player was positioned
        if tenniscores_player_id in [match["Home Player 1"], match["Home Player 2"]]:
            position = "Home Player 1" if match["Home Player 1"] == tenniscores_player_id else "Home Player 2"
            partner = match["Home Player 2"] if match["Home Player 1"] == tenniscores_player_id else match["Home Player 1"]
            print(f'    Position: {position}, Partner: {partner}')
        else:
            position = "Away Player 1" if match["Away Player 1"] == tenniscores_player_id else "Away Player 2"
            partner = match["Away Player 2"] if match["Away Player 1"] == tenniscores_player_id else match["Away Player 1"]
            print(f'    Position: {position}, Partner: {partner}')
        
        # Current court assignment logic (match index % 4 + 1)
        current_court = (i % 4) + 1
        print(f'    Current logic assigns: Court {current_court}')
        print()

# Also check if there are dates with multiple matches to understand real court assignment
print('\nChecking for dates with multiple matches...')

# Group matches by date to see the pattern
matches_by_date = {}
for match in matches:
    date = match['Date']
    if date not in matches_by_date:
        matches_by_date[date] = []
    matches_by_date[date].append(match)

print(f'Matches grouped by {len(matches_by_date)} unique dates:')
for date, date_matches in matches_by_date.items():
    print(f'  {date}: {len(date_matches)} match(es)')
    if len(date_matches) > 1:
        print(f'    Multiple matches on same date - this could indicate court assignment')
    else:
        print(f'    Single match - court assignment unclear') 