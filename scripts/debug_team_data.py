#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.services.mobile_service import get_mobile_team_data
from app.services.session_service import get_session_data_for_user
from database_utils import execute_query, execute_query_one

def test_team_data_for_user(email):
    """Test team data lookup for a specific user"""
    print(f"Testing team data for user: {email}")
    print("=" * 50)
    
    # Get session data first
    print("1. Getting session data...")
    session_data = get_session_data_for_user(email)
    if not session_data:
        print(f"❌ No session data found for {email}")
        return
    
    print(f"✅ Session data found:")
    for key, value in session_data.items():
        print(f"   {key}: {value} ({type(value)})")
    
    print("\n2. Testing get_mobile_team_data...")
    result = get_mobile_team_data(session_data)
    
    print(f"✅ Result:")
    for key, value in result.items():
        print(f"   {key}: {value}")
    
    print("\n3. Checking teams table...")
    teams_query = """
        SELECT t.id, t.team_name, t.display_name, c.name as club, s.name as series, l.league_name
        FROM teams t
        JOIN clubs c ON t.club_id = c.id
        JOIN series s ON t.series_id = s.id  
        JOIN leagues l ON t.league_id = l.id
        ORDER BY c.name, s.name
        LIMIT 10
    """
    teams = execute_query(teams_query)
    print(f"Sample teams in database:")
    for team in teams:
        print(f"   {team}")

if __name__ == "__main__":
    # Test with a known user email
    test_email = input("Enter user email to test: ").strip()
    if test_email:
        test_team_data_for_user(test_email)
    else:
        print("No email provided") 