#!/usr/bin/env python3

import json

from database_utils import execute_query

print("Checking all PTI data in player_history table...")

# Check if there's any PTI data at all
all_pti_query = """
    SELECT 
        ph.player_id,
        ph.date,
        ph.end_pti,
        ph.series,
        p.first_name,
        p.last_name,
        p.tenniscores_player_id
    FROM player_history ph
    LEFT JOIN players p ON ph.player_id = p.id
    ORDER BY ph.date DESC
    LIMIT 20
"""

all_pti_data = execute_query(all_pti_query, [])
print(f"Found {len(all_pti_data)} total PTI records in database")

if all_pti_data:
    print("Sample PTI data:")
    for i, record in enumerate(all_pti_data[:10]):
        name = f"{record.get('first_name', 'Unknown')} {record.get('last_name', '')}"
        print(
            f'  {i+1}. Player: {name} (ID: {record["player_id"]}) | Date: {record["date"]} | PTI: {record["end_pti"]} | Series: {record["series"]}'
        )

# Also check how many unique players have PTI data
unique_players_query = """
    SELECT COUNT(DISTINCT player_id) as unique_players
    FROM player_history
"""

unique_count = execute_query(unique_players_query, [])
if unique_count:
    print(f'\nTotal unique players with PTI data: {unique_count[0]["unique_players"]}')

# Check players who have tenniscores_player_id similar to what we're looking for
similar_players_query = """
    SELECT id, first_name, last_name, tenniscores_player_id
    FROM players 
    WHERE first_name = 'Ross' AND last_name = 'Freedman'
"""

similar_players = execute_query(similar_players_query, [])
print(f"\nAll Ross Freedman records in players table:")
for player in similar_players:
    print(
        f'  ID: {player["id"]} | Name: {player["first_name"]} {player["last_name"]} | Tennis ID: {player["tenniscores_player_id"]}'
    )
