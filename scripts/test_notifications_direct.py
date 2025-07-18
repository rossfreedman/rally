#!/usr/bin/env python3
"""
Script to test the individual notification functions directly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes.api_routes import (
    get_captain_messages,
    get_upcoming_schedule_notifications,
    get_team_position_notifications,
    get_team_poll_notifications,
    get_pickup_games_notifications,
    get_my_win_streaks_notifications
)

def test_notifications_direct():
    print("=== Testing Individual Notification Functions ===\n")
    
    # Ross's data
    user_id = 43
    player_id = "nndz-WkMrK3didjlnUT09"  # Chicago 22 player ID
    league_id = 4775  # APTA Chicago
    team_id = 59176   # Tennaqua - 22
    
    print(f"1. Testing with Ross's data:")
    print(f"   - User ID: {user_id}")
    print(f"   - Player ID: {player_id}")
    print(f"   - League ID: {league_id}")
    print(f"   - Team ID: {team_id}\n")
    
    # Test each notification function
    functions_to_test = [
        ("Captain Messages", get_captain_messages),
        ("Upcoming Schedule", get_upcoming_schedule_notifications),
        ("Team Position", get_team_position_notifications),
        ("Team Poll", get_team_poll_notifications),
        ("Pickup Games", get_pickup_games_notifications),
        ("My Win Streaks", get_my_win_streaks_notifications)
    ]
    
    all_notifications = []
    
    for name, func in functions_to_test:
        print(f"2. Testing {name}...")
        try:
            notifications = func(user_id, player_id, league_id, team_id)
            print(f"   ✅ {name}: {len(notifications)} notifications")
            
            for i, notification in enumerate(notifications, 1):
                print(f"      {i}. {notification['title']} (Priority: {notification['priority']})")
                print(f"         Message: {notification['message'][:60]}...")
                all_notifications.append(notification)
                
        except Exception as e:
            print(f"   ❌ {name}: Error - {str(e)}")
    
    print(f"\n3. Summary:")
    print(f"   Total notifications: {len(all_notifications)}")
    
    # Sort by priority
    all_notifications.sort(key=lambda x: x['priority'])
    
    print(f"\n4. Notifications sorted by priority:")
    for i, notification in enumerate(all_notifications, 1):
        print(f"   {i}. {notification['title']} (Priority: {notification['priority']})")
        print(f"      Message: {notification['message'][:60]}...")
    
    # Check for missing notifications
    expected_notifications = [
        "Captain's Message",
        "Upcoming Schedule", 
        "Team Position",
        "Team Poll",
        "Pickup Game Available",
        "My Win Streaks"
    ]
    
    found_titles = [n['title'] for n in all_notifications]
    
    print(f"\n5. Missing notifications:")
    missing = [title for title in expected_notifications if title not in found_titles]
    if missing:
        for title in missing:
            print(f"   ❌ {title}")
    else:
        print(f"   ✅ All expected notifications found")
    
    print("\n✅ Test completed")

if __name__ == "__main__":
    test_notifications_direct() 