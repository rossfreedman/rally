#!/usr/bin/env python3
"""
Script to manually add the missing Ross Freedman match to test our court assignment fix
This will insert the missing match in the correct position to test our theory
"""

import json
import os
from datetime import datetime

def add_missing_ross_match():
    """Add the missing Ross Freedman/Stephen Statkus match to the JSON"""
    
    json_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'leagues', 'APTA_CHICAGO', 'match_history.json')
    
    if not os.path.exists(json_path):
        print(f"❌ JSON file not found: {json_path}")
        return False
    
    print("🔧 Adding missing Ross Freedman match to JSON...")
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Find the October 8, 2024 matches
    oct8_matches = []
    oct8_indices = []
    
    for i, match in enumerate(data):
        if (match.get('Date') == '08-Oct-24' and 
            'Tennaqua' in match.get('Home Team', '') and 
            'Michigan Shores' in match.get('Away Team', '')):
            oct8_matches.append(match)
            oct8_indices.append(i)
    
    print(f"📊 Found {len(oct8_matches)} existing matches for Oct 8, 2024")
    
    if len(oct8_matches) != 3:
        print(f"⚠️ Expected 3 matches, found {len(oct8_matches)}. Aborting.")
        return False
    
    # The missing match should be inserted after the first match (Mike Lieberman)
    # and before the current second match (Victor Forman)
    
    # Create the missing Ross Freedman match
    missing_match = {
        "league_id": "APTA_CHICAGO",
        "Date": "08-Oct-24",
        "Home Team": "Tennaqua - 22",
        "Away Team": "Michigan Shores - 22", 
        "Home Player 1": "Ross Freedman",
        "Home Player 1 ID": "nndz-WkMrK3didjlnUT09",  # Ross's actual ID
        "Home Player 2": "Stephen Statkus",
        "Home Player 2 ID": "nndz-WkM2L3c3djZnQT09",  # Stephen's actual ID
        "Away Player 1": "John Kelly MSC",
        "Away Player 1 ID": "nndz-WkNPd3hyajhqUT09",  # John's actual ID from existing data
        "Away Player 2": "Tom Moran", 
        "Away Player 2 ID": "nndz-WkNPd3hyajhqUT09",  # Tom's actual ID from existing data
        "Scores": "6-4, 6-4",
        "Winner": "home",
        "source_league": "APTA_CHICAGO"
    }
    
    # Insert the missing match in the correct position
    # It should be the 2nd match (index 1) in the sequence
    insert_position = oct8_indices[1]  # Insert before the current 2nd match (Victor Forman)
    
    print(f"📍 Inserting missing match at position {insert_position}")
    print(f"   Before: {data[insert_position]['Home Player 1']} / {data[insert_position]['Home Player 2']}")
    
    data.insert(insert_position, missing_match)
    
    # Save the updated JSON
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print("✅ Successfully added missing Ross Freedman match!")
    
    # Verify the fix
    print("\n🔍 Verifying the updated sequence:")
    updated_oct8_matches = []
    for match in data:
        if (match.get('Date') == '08-Oct-24' and 
            'Tennaqua' in match.get('Home Team', '') and 
            'Michigan Shores' in match.get('Away Team', '')):
            updated_oct8_matches.append(match)
    
    for i, match in enumerate(updated_oct8_matches, 1):
        print(f"  Court {i}: {match['Home Player 1']} / {match['Home Player 2']} vs {match['Away Player 1']} / {match['Away Player 2']}")
        print(f"    Score: {match['Scores']}, Winner: {match['Winner']}")
    
    print(f"\n🎯 Expected order:")
    print(f"  Court 1: Mike Lieberman / Brian Stutland vs Greg Byrnes / Ben Rodman")
    print(f"  Court 2: Ross Freedman / Stephen Statkus vs John Kelly MSC / Tom Moran") 
    print(f"  Court 3: Victor Forman / Paul Patt vs Chris Pauly / Tim Davis")
    print(f"  Court 4: Jonathan Blume / Adam Seyb vs JP Marchetti / Bob Armour")
    
    return True

if __name__ == "__main__":
    success = add_missing_ross_match()
    if success:
        print("\n✅ Ready to re-import to database!")
        print("💡 Run: python3 data/etl/database_import/import_all_jsons_to_database.py")
    else:
        print("\n❌ Failed to add missing match") 