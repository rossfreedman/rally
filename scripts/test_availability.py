#!/usr/bin/env python3
"""
Test script to verify all-team-availability functionality
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.mobile_service import get_all_team_availability_data

# Mock user object matching the expected structure
test_user = {
    "email": "test@example.com",
    "club": "Tennaqua",
    "series": "Chicago 22",  # This should match what's in the database
}

# Test with the specific date from the URL
test_date = "09/24/2024"

print(f"Testing all-team-availability with:")
print(f"  User: {test_user}")
print(f"  Date: {test_date}")
print()

try:
    result = get_all_team_availability_data(test_user, test_date)

    print("Result:")
    print(f"  Players found: {len(result.get('players_schedule', {}))}")
    print(f"  Selected date: {result.get('selected_date')}")
    print(f"  Team: {result.get('team', 'N/A')}")

    if result.get("error"):
        print(f"  Error: {result['error']}")

    print()
    print("Player data:")
    for player_name, availability_list in result.get("players_schedule", {}).items():
        print(f"  {player_name}: {availability_list}")

except Exception as e:
    print(f"Error running test: {e}")
    import traceback

    print(traceback.format_exc())
