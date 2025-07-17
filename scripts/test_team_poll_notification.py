#!/usr/bin/env python3
"""
Test script to verify team poll notification format
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes.api_routes import get_team_poll_notifications
from database_utils import execute_query_one

def test_team_poll_notification():
    """Test team poll notification format"""
    
    # Test with Ross Freedman's data
    user_id = 1  # Ross Freedman's user ID
    player_id = "nndz-WkMrK3didjlnUT09"  # Ross's player ID
    league_id = 4489  # APTA Chicago
    team_id = 47092  # Tennaqua S2B
    
    print("Testing team poll notification format...")
    print(f"User ID: {user_id}")
    print(f"Player ID: {player_id}")
    print(f"League ID: {league_id}")
    print(f"Team ID: {team_id}")
    print()
    
    # Get team poll notifications
    notifications = get_team_poll_notifications(user_id, player_id, league_id, team_id)
    
    if notifications:
        print("✅ Team poll notification found:")
        for notification in notifications:
            print(f"  ID: {notification['id']}")
            print(f"  Type: {notification['type']}")
            print(f"  Title: {notification['title']}")
            print(f"  Message: {notification['message']}")
            print(f"  CTA: {notification['cta']}")
            print(f"  Priority: {notification['priority']}")
            print()
            
            # Verify the message only contains the poll question
            if " - " in notification['message'] or " by " in notification['message']:
                print("❌ ERROR: Message still contains date or creator information!")
                return False
            else:
                print("✅ SUCCESS: Message only shows poll question (no date/creator)")
                return True
    else:
        print("ℹ️  No team poll notifications found for this user/team")
        return True

if __name__ == "__main__":
    success = test_team_poll_notification()
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n❌ Test failed!")
        sys.exit(1) 