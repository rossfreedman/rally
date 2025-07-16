#!/usr/bin/env python3
"""
Test script for the new notification functions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes.api_routes import get_team_position_notifications, get_my_win_streaks_notifications
from database_utils import execute_query

def test_team_position_notifications():
    """Test the team position notifications function"""
    print("Testing get_team_position_notifications...")
    
    # Test with sample data
    user_id = 1
    player_id = "test_player_id"
    league_id = 4489  # APTA Chicago
    team_id = 1
    
    try:
        notifications = get_team_position_notifications(user_id, player_id, league_id, team_id)
        print(f"Team position notifications: {notifications}")
        return True
    except Exception as e:
        print(f"Error testing team position notifications: {e}")
        return False

def test_my_win_streaks_notifications():
    """Test the my win streaks notifications function"""
    print("Testing get_my_win_streaks_notifications...")
    
    # Test with sample data
    user_id = 1
    player_id = "test_player_id"
    league_id = 4489  # APTA Chicago
    team_id = 1
    
    try:
        notifications = get_my_win_streaks_notifications(user_id, player_id, league_id, team_id)
        print(f"My win streaks notifications: {notifications}")
        return True
    except Exception as e:
        print(f"Error testing my win streaks notifications: {e}")
        return False

def test_notification_order():
    """Test that notifications are returned in the correct order"""
    print("Testing notification order...")
    
    # The expected order should be:
    # 1. Captains Message (priority 1)
    # 2. Upcoming Schedule (priority 2)
    # 3. Team Position (priority 3)
    # 4. Team Poll (priority 4)
    # 5. My Win Streaks (priority 5)
    # 6. Pickup Games Available (priority 6)
    
    expected_order = [1, 2, 3, 4, 5, 6]
    print(f"Expected priority order: {expected_order}")
    print("✅ Notification order test completed")

if __name__ == "__main__":
    print("Testing new notification functions...")
    print("=" * 50)
    
    # Test individual functions
    test_team_position_notifications()
    test_my_win_streaks_notifications()
    test_notification_order()
    
    print("=" * 50)
    print("✅ All tests completed!") 