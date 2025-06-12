#!/usr/bin/env python3

import sys
sys.path.append('.')

from app.services.mobile_service import get_mobile_team_data
import json
import os

# Test with Ross's data
test_user = {
    'club': 'Tennaqua',
    'email': 'rossfreedman@gmail.com', 
    'first_name': 'Ross',
    'last_name': 'Freedman',
    'league_id': 'NSTF',
    'league_name': 'North Shore Tennis Foundation',
    'series': 'Series 2B',
    'tenniscores_player_id': 'nndz-WlNhd3hMYi9nQT09'
}

print("🏓 DEBUG: Testing team name construction for NSTF player")
print(f"Player: {test_user['first_name']} {test_user['last_name']}")
print(f"Club: {test_user['club']}")
print(f"Series: {test_user['series']}")
print("=" * 60)

# Manual team name construction (current logic)
import re
club = test_user.get('club')
series = test_user.get('series')
m = re.search(r'(\d+)', series)
series_num = m.group(1) if m else ''
constructed_team = f"{club} - {series_num}"

print(f"🔧 CURRENT LOGIC:")
print(f"   Input series: '{series}'")
print(f"   Extracted number: '{series_num}'")
print(f"   Constructed team name: '{constructed_team}'")

# Check what teams actually exist in match data
matches_path = 'data/leagues/all/match_history.json'
with open(matches_path, 'r') as f:
    all_matches = json.load(f)

# Find all unique team names containing "Tennaqua"
tennaqua_teams = set()
for match in all_matches:
    home_team = match.get('Home Team', '')
    away_team = match.get('Away Team', '')
    if 'Tennaqua' in home_team:
        tennaqua_teams.add(home_team)
    if 'Tennaqua' in away_team:
        tennaqua_teams.add(away_team)

print(f"\n📋 ACTUAL TENNAQUA TEAMS IN DATA:")
for team in sorted(tennaqua_teams):
    print(f"   '{team}'")

# Test the actual function
print(f"\n🧪 TESTING get_mobile_team_data():")
result = get_mobile_team_data(test_user)
team_data = result.get('team_data')
error = result.get('error')

print(f"   Error: {error}")
print(f"   Team data found: {team_data is not None}")
if team_data:
    print(f"   Team name in result: {team_data.get('team', 'N/A')}")

# Check specifically for NSTF format
nstf_format = f"{club} S2B"
print(f"\n💡 LIKELY CORRECT TEAM NAME: '{nstf_format}'")
print(f"   Is this in the data? {'Yes' if nstf_format in tennaqua_teams else 'No'}") 