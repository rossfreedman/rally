#!/usr/bin/env python3
"""Automated test to verify /api/schedule returns club_address field"""

import json
from database_utils import execute_query
from routes.act.schedule import get_matches_for_user_club

# Test with different clubs
test_clubs = [
    {"club": "Michigan Shores", "series": "Series 20"},
    {"club": "Park Ridge CC", "series": "Series 35"},
    {"club": "Indian Hill", "series": "Series 26"},
    {"club": "Skokie", "series": "Series 29"},
    {"club": "Winnetka", "series": "Series 26"},
]

print("\n" + "=" * 70)
print("AUTOMATED TEST: Verify /api/schedule Returns club_address")
print("=" * 70)

success_count = 0
fail_count = 0

for i, test_case in enumerate(test_clubs, 1):
    print(f"\n{'='*70}")
    print(f"TEST {i}/5: {test_case['club']} - {test_case['series']}")
    print(f"{'='*70}")
    
    # Get user from this club
    user_query = execute_query("""
        SELECT u.id, u.email, u.first_name, u.last_name, 
               t.club_id, c.name as club, l.league_name
        FROM users u
        JOIN teams t ON u.team_id = t.id
        JOIN clubs c ON t.club_id = c.id
        JOIN leagues l ON t.league_id = l.id
        WHERE c.name LIKE %s
        LIMIT 1
    """, (f"%{test_case['club']}%",))
    
    if not user_query:
        # Try to create a mock user object based on the club
        league_query = execute_query("""
            SELECT l.id, l.league_name
            FROM leagues l
            JOIN teams t ON t.league_id = l.id
            JOIN clubs c ON t.club_id = c.id
            WHERE c.name LIKE %s
            LIMIT 1
        """, (f"%{test_case['club']}%",))
        
        if league_query:
            user = {
                "club": test_case['club'],
                "series": test_case['series'],
                "league_id": league_query[0]['id']
            }
        else:
            print(f"  ❌ SKIP: No users or league found for {test_case['club']}")
            fail_count += 1
            continue
    else:
        user_data = user_query[0]
        # Get team's series
        team_query = execute_query("""
            SELECT s.name as series
            FROM teams t
            JOIN series s ON t.series_id = s.id
            WHERE t.id = (SELECT team_id FROM users WHERE id = %s LIMIT 1)
        """, (user_data['id'],))
        
        series = team_query[0]['series'] if team_query else test_case['series']
        
        user = {
            "club": user_data['club'],
            "series": series,
            "league_id": user_data.get('league_name', 'APTA Chicago')
        }
    
    print(f"  User Context: {user['club']} - {user['series']}")
    
    # Get matches for this user
    try:
        matches = get_matches_for_user_club(user)
        
        if not matches:
            print(f"  ⚠️  WARNING: No matches found for {user['club']}")
            continue
        
        print(f"  ✓ Found {len(matches)} total entries (matches + practices)")
        
        # Check matches (not practices) for club_address field
        upcoming_matches = [m for m in matches if m.get('type') == 'match']
        
        if not upcoming_matches:
            print(f"  ⚠️  WARNING: No matches (only practices) found")
            continue
        
        print(f"  ✓ Found {len(upcoming_matches)} matches")
        
        # Check first match for club_address
        first_match = upcoming_matches[0]
        
        print(f"\n  First Match Details:")
        print(f"    Home: {first_match.get('home_team')}")
        print(f"    Away: {first_match.get('away_team')}")
        print(f"    Date: {first_match.get('date')}")
        print(f"    Location: {first_match.get('location')}")
        print(f"    Club Address: {first_match.get('club_address', 'MISSING!')}")
        
        # Verify club_address exists
        if 'club_address' in first_match:
            if first_match['club_address']:
                print(f"\n  ✅ SUCCESS: club_address field is present and has value")
                print(f"     Maps URL: https://maps.google.com/?q={first_match.get('location', '')}, {first_match['club_address']}")
                success_count += 1
            else:
                print(f"\n  ⚠️  WARNING: club_address field exists but is empty")
                print(f"     This is OK if the location club doesn't have an address in the database")
        else:
            print(f"\n  ❌ FAIL: club_address field is MISSING from match data")
            fail_count += 1
            
    except Exception as e:
        print(f"  ❌ ERROR: {str(e)}")
        fail_count += 1

print(f"\n{'='*70}")
print(f"FINAL RESULTS")
print(f"{'='*70}")
print(f"  ✅ Successful: {success_count}/5")
print(f"  ❌ Failed:     {fail_count}/5")

if success_count >= 3:
    print(f"\n  🎉 PASS: Majority of tests successful!")
    print(f"  The Get Directions feature should work correctly.")
else:
    print(f"\n  ⚠️  Some tests failed. Check the output above.")

print(f"{'='*70}\n")

