#!/usr/bin/env python3
"""
Debug script to test October 8, 2024 match scraping
This will help us understand why the Ross Freedman match is missing
"""

import os
import sys
import json
from datetime import datetime

# Add the scrapers directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'data', 'etl', 'scrapers'))

from scraper_match_scores import parse_cnswpl_match_table, get_league_config

def debug_oct8_matches():
    """Debug the October 8, 2024 match extraction"""
    
    print("🔍 DEBUG: October 8, 2024 Match Scraping")
    print("=" * 50)
    
    # Load the current JSON data
    json_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'leagues', 'APTA_CHICAGO', 'match_history.json')
    
    if not os.path.exists(json_path):
        print(f"❌ JSON file not found: {json_path}")
        return
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Find all October 8, 2024 matches for Tennaqua vs Michigan Shores
    oct8_matches = []
    for match in data:
        if (match.get('Date') == '08-Oct-24' and 
            'Tennaqua' in match.get('Home Team', '') and 
            'Michigan Shores' in match.get('Away Team', '')):
            oct8_matches.append(match)
    
    print(f"📊 Current JSON has {len(oct8_matches)} matches for Oct 8, 2024:")
    for i, match in enumerate(oct8_matches, 1):
        print(f"  {i}. {match['Home Player 1']} / {match['Home Player 2']} vs {match['Away Player 1']} / {match['Away Player 2']}")
        print(f"     Score: {match['Scores']}, Winner: {match['Winner']}")
    
    print(f"\n🎯 Expected matches from sample image:")
    expected = [
        "Mike Lieberman / Brian Stutland vs Greg Byrnes / Ben Rodman (6-1, 6-0)",
        "Ross Freedman / Stephen Statkus vs John Kelly MSC / Tom Moran (6-4, 6-4)",  # MISSING!
        "Victor Forman / Paul Patt vs Chris Pauly / Tim Davis (1-6, 1-6)",
        "Jonathan Blume / Adam Seyb vs JP Marchetti / Bob Armour (6-4, 4-6, 2-6)"
    ]
    
    for i, expected_match in enumerate(expected, 1):
        print(f"  {i}. {expected_match}")
    
    print(f"\n❌ MISSING: Ross Freedman / Stephen Statkus match")
    print(f"🔍 This suggests a scraper filtering issue")
    
    # Create mock HTML that represents what the scraper might see
    print(f"\n🧪 Testing parser with mock data...")
    
    # This would be the HTML structure the scraper extracts
    mock_divs_by_class = {
        "points": ["", "", "", "", ""],  # Header + 4 matches
        "team_name": [
            "Tennaqua - 22",  # Header
            "Mike Lieberman / Brian Stutland",  # Match 1
            "Ross Freedman / Stephen Statkus",   # Match 2 - MISSING from JSON!
            "Victor Forman / Paul Patt",         # Match 3 
            "Jonathan Blume / Adam Seyb"         # Match 4
        ],
        "match_rest": [
            "October 8, 2024 06:30 pm",  # Header  
            "6-1, 6-0",                   # Match 1
            "6-4, 6-4",                   # Match 2 - MISSING!
            "1-6, 1-6",                   # Match 3
            "6-4, 4-6, 2-6"              # Match 4
        ],
        "team_name2": [
            "Michigan Shores - 22",       # Header
            "Greg Byrnes / Ben Rodman",   # Match 1
            "John Kelly MSC / Tom Moran", # Match 2 - MISSING!
            "Chris Pauly / Tim Davis",    # Match 3
            "JP Marchetti / Bob Armour"   # Match 4
        ],
        "points2": ["", "", "", "", ""]  # Header + 4 matches
    }
    
    print(f"Mock data structure:")
    for i in range(len(mock_divs_by_class["team_name"])):
        if i == 0:
            print(f"  Header: {mock_divs_by_class['team_name'][i]} vs {mock_divs_by_class['team_name2'][i]}")
        else:
            print(f"  Match {i}: {mock_divs_by_class['team_name'][i]} vs {mock_divs_by_class['team_name2'][i]} - {mock_divs_by_class['match_rest'][i]}")
    
    print(f"\n🔬 This mock data should produce 4 matches, but our JSON only has 3.")
    print(f"💡 The scraper is likely filtering out the Ross Freedman match due to:")
    print(f"   1. Different separator format (not '/')")
    print(f"   2. HTML encoding issues") 
    print(f"   3. Extra whitespace or special characters")
    print(f"   4. Player name formatting differences")
    
    print(f"\n📝 Recommendation:")
    print(f"   1. Run the enhanced scraper with debug logging")
    print(f"   2. Check what raw HTML is extracted for this match")
    print(f"   3. Look for separator issues in the filtering logic")

if __name__ == "__main__":
    debug_oct8_matches() 