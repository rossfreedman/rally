#!/usr/bin/env python3

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))
from database_utils import execute_query, execute_query_one

print("🎯 CHECKING PLAYERS.PTI FIELD")
print("=" * 60)

# 1. Check Ross Freedman's PTI in the players table
player_id = "nndz-WkMrK3didjlnUT09"
print(f"Checking PTI for Player ID: {player_id}")

ross_pti_query = """
    SELECT 
        id,
        first_name,
        last_name,
        email,
        pti,
        tenniscores_player_id,
        club_id,
        series_id,
        league_id
    FROM players 
    WHERE tenniscores_player_id = %s
"""
ross_data = execute_query_one(ross_pti_query, [player_id])

if ross_data:
    print(f"\n✅ Player Found:")
    print(f"   Name: {ross_data['first_name']} {ross_data['last_name']}")
    print(f"   Email: {ross_data['email']}")
    print(f"   Integer ID: {ross_data['id']}")
    print(f"   🎯 PTI: {ross_data['pti']}")
    print(f"   Club ID: {ross_data['club_id']}")
    print(f"   Series ID: {ross_data['series_id']}")
    print(f"   League ID: {ross_data['league_id']}")

    if ross_data["pti"] is not None:
        print(f"\n🎉 PTI DATA FOUND: {ross_data['pti']}")

        # Test the mobile service with this direct PTI approach
        print(f"\n🧪 Testing modified mobile service logic...")

        # Let's see if we can find a way to get PTI change data
        # Check if we can link player_history by series or other means
        series_link_query = """
            SELECT 
                date,
                end_pti,
                series,
                TO_CHAR(date, 'YYYY-MM-DD') as formatted_date
            FROM player_history
            WHERE series IS NOT NULL
            ORDER BY date DESC
            LIMIT 10
        """

        series_data = execute_query(series_link_query)
        if series_data:
            print(f"   Found {len(series_data)} recent records with series data:")
            for record in series_data:
                print(
                    f"     {record['formatted_date']}: PTI={record['end_pti']}, Series={record['series']}"
                )

    else:
        print(f"\n❌ PTI field is NULL in players table")

else:
    print(f"❌ Player not found")

# 2. Check some other players with PTI data
print(f"\n📊 Checking other players with PTI data:")
other_players_query = """
    SELECT 
        first_name,
        last_name,
        pti,
        tenniscores_player_id
    FROM players 
    WHERE pti IS NOT NULL
    ORDER BY pti DESC
    LIMIT 10
"""
other_players = execute_query(other_players_query)
if other_players:
    print(f"   Found {len(other_players)} players with PTI data:")
    for player in other_players:
        print(
            f"     {player['first_name']} {player['last_name']}: PTI={player['pti']} (ID: {player['tenniscores_player_id']})"
        )
else:
    print("   No players found with PTI data")

# 3. Check if we can link player_history by series to get PTI progression
print(f"\n🔄 Investigating PTI progression linking:")

# Get Ross's series
if ross_data and ross_data["series_id"]:
    # Get series name from series table
    series_query = """
        SELECT name FROM series WHERE id = %s
    """
    series_info = execute_query_one(series_query, [ross_data["series_id"]])

    if series_info:
        series_name = series_info["name"]
        print(f"   Ross's series: {series_name}")

        # Try to find PTI history by series name
        series_history_query = """
            SELECT 
                date,
                end_pti,
                TO_CHAR(date, 'YYYY-MM-DD') as formatted_date
            FROM player_history
            WHERE series ILIKE %s
            ORDER BY date DESC
            LIMIT 10
        """

        # Try different series name patterns
        patterns = [
            series_name,
            f"%{series_name}%",
            f"{series_name}%",
            f"%{series_name}",
        ]

        for pattern in patterns:
            series_records = execute_query(series_history_query, [pattern])
            if series_records:
                print(
                    f"   Found {len(series_records)} records matching pattern '{pattern}':"
                )
                for record in series_records:
                    print(f"     {record['formatted_date']}: PTI={record['end_pti']}")
                break
        else:
            print(f"   No PTI history found for series: {series_name}")

print(f"\n💡 RECOMMENDATION:")
print(f"   Use players.pti field for current PTI instead of player_history linking")
print(f"   PTI change calculation may not be available until linking is fixed")
