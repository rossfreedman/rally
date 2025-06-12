#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
from database_utils import execute_query, execute_query_one

# Check PTI data for the CORRECT player ID
player_id = 'nndz-WkMrK3didjlnUT09'  # This is the correct one from your request

print(f"Checking PTI data for Player ID: {player_id}")
print("=" * 60)

# First get the integer player_id from the players table
player_lookup_query = '''
    SELECT id, first_name, last_name, email FROM players 
    WHERE tenniscores_player_id = %s
'''
player_lookup = execute_query_one(player_lookup_query, [player_id])

if player_lookup:
    integer_player_id = player_lookup['id']
    player_name = f"{player_lookup['first_name']} {player_lookup['last_name']}"
    print(f'✅ Player found: {player_name}')
    print(f'   Email: {player_lookup["email"]}')
    print(f'   Integer ID: {integer_player_id}')
    
    # Get PTI data for this player
    pti_query = '''
        SELECT 
            date,
            end_pti,
            TO_CHAR(date, 'YYYY-MM-DD') as formatted_date
        FROM player_history
        WHERE player_id = %s
        ORDER BY date DESC
        LIMIT 10
    '''
    
    pti_records = execute_query(pti_query, [integer_player_id])
    
    if pti_records:
        print(f'\n🎯 Found {len(pti_records)} PTI records:')
        for i, record in enumerate(pti_records):
            print(f'  {i+1:2d}. {record["formatted_date"]}: PTI = {record["end_pti"]:.1f}')
        
        # Calculate current PTI and change
        current_pti = pti_records[0]['end_pti']
        pti_change = 0.0
        if len(pti_records) >= 2:
            previous_pti = pti_records[1]['end_pti']
            pti_change = current_pti - previous_pti
        
        print(f'\n📊 PTI Summary:')
        print(f'   Current PTI: {current_pti:.1f}')
        print(f'   PTI Change: {pti_change:+.1f}')
        print(f'   PTI data available: ✅ TRUE')
        
        # Test the mobile service function
        print(f'\n🧪 Testing mobile service...')
        from services.mobile_service import get_player_analysis
        
        user = {
            'tenniscores_player_id': player_id,
            'email': player_lookup['email'],
            'league_id': 'APTA'
        }
        
        result = get_player_analysis(user)
        
        if result.get('pti_data_available'):
            print(f'   ✅ Mobile service correctly detects PTI data')
            print(f'   📈 Current PTI: {result.get("current_pti")}')
            print(f'   📊 Weekly change: {result.get("weekly_pti_change"):+.1f}')
        else:
            print(f'   ❌ Mobile service NOT detecting PTI data')
            print(f'   🐛 Error: {result.get("error")}')
        
    else:
        print(f'\n❌ No PTI data found for player_id {integer_player_id}')
        print(f'   PTI data available: FALSE')
        
        # Check if there are ANY player_history records
        all_history_query = 'SELECT COUNT(*) as total FROM player_history'
        total_records = execute_query_one(all_history_query)
        print(f'   Total player_history records in DB: {total_records["total"]}')
        
        # Check if there are records for other players
        other_players_query = 'SELECT DISTINCT player_id FROM player_history LIMIT 5'
        other_players = execute_query(other_players_query)
        if other_players:
            print(f'   Other players with PTI data: {[p["player_id"] for p in other_players]}')
        
else:
    print(f'❌ No player found with tenniscores_player_id: {player_id}')
    
    # Check if similar player IDs exist
    similar_query = '''
        SELECT tenniscores_player_id, first_name, last_name 
        FROM players 
        WHERE tenniscores_player_id LIKE %s
        LIMIT 5
    '''
    similar_players = execute_query(similar_query, [f'%{player_id[-10:]}%'])
    if similar_players:
        print(f'\n🔍 Similar player IDs found:')
        for p in similar_players:
            print(f'   {p["tenniscores_player_id"]}: {p["first_name"]} {p["last_name"]}') 