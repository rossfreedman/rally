#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.services.mobile_service import get_mobile_team_data
from database_utils import execute_query

def test_team_lookup():
    print("Testing team data lookup...")
    print("=" * 50)
    
    # Get a sample user with tenniscores_player_id
    sample_user_query = """
        SELECT email, first_name, last_name, tenniscores_player_id, league_context
        FROM users 
        WHERE tenniscores_player_id IS NOT NULL 
        LIMIT 1
    """
    
    sample_user = execute_query(sample_user_query)
    if not sample_user:
        print("❌ No users found with tenniscores_player_id")
        return
    
    user_data = sample_user[0]
    print(f"Testing with user: {user_data['first_name']} {user_data['last_name']} ({user_data['email']})")
    print(f"Player ID: {user_data['tenniscores_player_id']}")
    print(f"League context: {user_data['league_context']}")
    print()
    
    # Create user dict like session would have
    user_session = {
        "email": user_data["email"],
        "first_name": user_data["first_name"], 
        "last_name": user_data["last_name"],
        "tenniscores_player_id": user_data["tenniscores_player_id"],
        "league_id": user_data["league_context"]
    }
    
    # Test the function
    print("Calling get_mobile_team_data...")
    print("-" * 30)
    
    try:
        result = get_mobile_team_data(user_session)
        print("✅ Function completed successfully")
        print(f"Result keys: {list(result.keys())}")
        
        if result.get("error"):
            print(f"❌ Error returned: {result['error']}")
        else:
            team_data = result.get("team_data", {})
            if team_data:
                print(f"✅ Team data found:")
                print(f"  Team: {team_data.get('team', 'Unknown')}")
                print(f"  Matches: {team_data.get('matches', {})}")
                print(f"  Lines: {team_data.get('lines', {})}")
            else:
                print("❌ No team_data in result")
                
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_team_lookup() 