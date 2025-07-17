#!/usr/bin/env python3
"""
Test the actual schedule notification function with better error handling
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes.api_routes import get_upcoming_schedule_notifications

def test_schedule_function():
    """Test the actual schedule notification function"""
    
    print("🔍 Testing Schedule Notification Function")
    print("=" * 50)
    
    # Test data
    user_id = 43
    player_id = "nndz-WkMrK3didjlnUT09"
    league_id = 4763
    team_id = 57314
    
    print(f"Test data:")
    print(f"  User ID: {user_id}")
    print(f"  Player ID: {player_id}")
    print(f"  League ID: {league_id}")
    print(f"  Team ID: {team_id}")
    
    try:
        # Call the actual function
        notifications = get_upcoming_schedule_notifications(user_id, player_id, league_id, team_id)
        
        print(f"\n✅ Function completed successfully")
        print(f"   Returned {len(notifications)} notifications")
        
        for i, notification in enumerate(notifications):
            print(f"\n   Notification {i+1}:")
            print(f"     ID: {notification.get('id')}")
            print(f"     Title: {notification.get('title')}")
            print(f"     Message: {notification.get('message')}")
            print(f"     Type: {notification.get('type')}")
            print(f"     Priority: {notification.get('priority')}")
            
    except Exception as e:
        print(f"\n❌ Function failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_schedule_function() 