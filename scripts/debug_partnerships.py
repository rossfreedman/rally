#!/usr/bin/env python3

"""
Debug script to analyze partnership data for the Best Partner issue
"""

import sys
sys.path.append('.')

from app.services.mobile_service import get_mobile_team_data

# Test with your user data (adjust as needed)
test_user = {
    'club': 'Seven Bridges',
    'email': 'bwagner@gmail.com',  # From the console logs
    'first_name': 'Brian',
    'last_name': 'Wagner',
    'league_id': 'APTA_CHICAGO',  # Adjust based on your league
    'series': 'Series 3'  # Adjust based on your series
}

print("🔍 DEBUGGING PARTNERSHIP DATA")
print("=" * 50)
print(f"User: {test_user['first_name']} {test_user['last_name']}")
print(f"Email: {test_user['email']}")
print(f"Club: {test_user['club']}")
print(f"Series: {test_user['series']}")
print("=" * 50)

try:
    result = get_mobile_team_data(test_user)
    
    # Check the result structure
    print(f"\n📊 RESULT STRUCTURE:")
    print(f"- team_data: {result.get('team_data') is not None}")
    print(f"- top_players: {len(result.get('top_players', []))} players")
    print(f"- error: {result.get('error')}")
    
    # Look at the top players data
    top_players = result.get('top_players', [])
    if top_players:
        print(f"\n👥 TOP PLAYERS DATA:")
        for i, player in enumerate(top_players[:3]):  # Show first 3 players
            print(f"\n{i+1}. {player.get('name', 'Unknown')}")
            print(f"   Matches: {player.get('matches', 0)}")
            print(f"   Win Rate: {player.get('win_rate', 0)}%")
            print(f"   Best Court: {player.get('best_court', 'N/A')}")
            print(f"   Best Partner: {player.get('best_partner', 'N/A')}")
    else:
        print("\n❌ No top players data found")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("🔍 Check the console above for [DEBUG PARTNER] messages")
print("   These show the raw partnership data being processed") 