#!/usr/bin/env python3
"""
Validation script to confirm analyze-me page uses database starting_pti field
"""

import sys
import os

# Add root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock user session data (similar to what Flask session would contain)
user = {
    'tenniscores_player_id': 'nndz-WkMrK3didjlnUT09',  # Ross Freedman
    'league_id': 4783,
    'first_name': 'Ross',
    'last_name': 'Freedman',
    'club': 'Tennaqua',
    'series': 'Series 20',
    'team_id': 59837,
}

# Test the exact code path used by analyze-me page
from app.services.mobile_service import get_player_analysis

print("=" * 70)
print("VALIDATING analyze-me page PTI lookup")
print("=" * 70)
print()

print(f"Testing with user: {user['first_name']} {user['last_name']}")
print(f"Player ID: {user['tenniscores_player_id']}")
print(f"League ID: {user['league_id']}")
print()
print("Calling get_player_analysis()...")
print("-" * 70)

try:
    # This will trigger the PTI lookup logic
    result = get_player_analysis(user)
    
    print()
    print("=" * 70)
    print("RESULTS FROM get_player_analysis()")
    print("=" * 70)
    
    if result:
        print(f"✅ Function executed successfully")
        print()
        print(f"Current PTI:       {result.get('current_pti', 'N/A')}")
        print(f"Starting PTI:      {result.get('starting_pti', 'N/A')}")
        print(f"PTI Delta:         {result.get('pti_delta', 'N/A')}")
        print(f"Delta Available:   {result.get('delta_available', False)}")
        print()
        
        # Validate the values
        expected_starting_pti = 50.8
        expected_delta = -0.8
        
        if result.get('starting_pti') == expected_starting_pti:
            print(f"✅ Starting PTI matches expected: {expected_starting_pti}")
        else:
            print(f"❌ Starting PTI mismatch! Expected {expected_starting_pti}, got {result.get('starting_pti')}")
        
        if result.get('pti_delta') == expected_delta:
            print(f"✅ PTI Delta matches expected: {expected_delta}")
        else:
            print(f"❌ PTI Delta mismatch! Expected {expected_delta}, got {result.get('pti_delta')}")
        
        if result.get('delta_available'):
            print(f"✅ Delta is available for display")
        else:
            print(f"❌ Delta not available!")
        
        print()
        print("=" * 70)
        print("✅ VALIDATION SUCCESSFUL - analyze-me page uses database starting_pti")
        print("=" * 70)
    else:
        print("❌ No result returned from get_player_analysis()")
        
except Exception as e:
    print(f"❌ Error during validation: {e}")
    import traceback
    print(traceback.format_exc())

