#!/usr/bin/env python3
"""
Test script to verify notification filters are working correctly.
This script tests that loss-related notifications are hidden while keeping
Team Polls, Pickup Games, and Captain Notifications.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one
import json

def test_notification_filters():
    """Test that notification filters are working correctly"""
    
    print("=== Testing Notification Filters ===")
    print("Verifying that loss-related notifications are hidden...")
    
    # Test 1: Check recent match results function
    print("\n1. Testing recent match results...")
    
    # Get a sample user with recent matches
    user_query = """
        SELECT u.id, u.email, u.tenniscores_player_id, u.league_id, u.league_context
        FROM users u
        WHERE u.tenniscores_player_id IS NOT NULL 
        AND u.league_id IS NOT NULL
        LIMIT 1
    """
    
    user = execute_query_one(user_query)
    if not user:
        print("❌ No test user found with required data")
        return False
    
    print(f"✅ Using test user: {user['email']}")
    
    # Import the notification functions
    from app.routes.api_routes import get_recent_match_results, get_personal_performance_highlights, get_team_performance_highlights
    
    # Test recent match results
    recent_results = get_recent_match_results(
        user['id'], 
        user['tenniscores_player_id'], 
        user['league_id'], 
        user['league_context']
    )
    
    print(f"   Recent match notifications: {len(recent_results)}")
    for notification in recent_results:
        print(f"   - {notification['title']}: {notification['message']}")
        # Verify no loss notifications
        if 'lost' in notification['message'].lower() or 'loss' in notification['title'].lower():
            print(f"   ❌ ERROR: Found loss notification: {notification['title']}")
            return False
    
    # Test personal performance highlights
    print("\n2. Testing personal performance highlights...")
    personal_highlights = get_personal_performance_highlights(
        user['id'], 
        user['tenniscores_player_id'], 
        user['league_id'], 
        user['league_context']
    )
    
    print(f"   Personal highlight notifications: {len(personal_highlights)}")
    for notification in personal_highlights:
        print(f"   - {notification['title']}: {notification['message']}")
        # Verify no loss streak notifications
        if 'loss' in notification['title'].lower() or 'decreased' in notification['message'].lower():
            print(f"   ❌ ERROR: Found loss notification: {notification['title']}")
            return False
    
    # Test team performance highlights
    print("\n3. Testing team performance highlights...")
    team_highlights = get_team_performance_highlights(
        user['id'], 
        user['tenniscores_player_id'], 
        user['league_id'], 
        user['league_context']
    )
    
    print(f"   Team highlight notifications: {len(team_highlights)}")
    for notification in team_highlights:
        print(f"   - {notification['title']}: {notification['message']}")
        # Verify no team loss notifications
        if 'loss' in notification['title'].lower() or 'lost' in notification['message'].lower():
            print(f"   ❌ ERROR: Found team loss notification: {notification['title']}")
            return False
    
    # Test that other notification types still work
    print("\n4. Testing that other notification types still work...")
    
    from app.routes.api_routes import get_team_poll_notifications, get_pickup_games_notifications, get_captain_messages
    
    # Test team polls
    poll_notifications = get_team_poll_notifications(
        user['id'], 
        user['tenniscores_player_id'], 
        user['league_id'], 
        user['league_context']
    )
    print(f"   Team poll notifications: {len(poll_notifications)}")
    
    # Test pickup games
    pickup_notifications = get_pickup_games_notifications(
        user['id'], 
        user['tenniscores_player_id'], 
        user['league_id'], 
        user['league_context']
    )
    print(f"   Pickup game notifications: {len(pickup_notifications)}")
    
    # Test captain messages
    captain_notifications = get_captain_messages(
        user['id'], 
        user['tenniscores_player_id'], 
        user['league_id'], 
        user['league_context']
    )
    print(f"   Captain message notifications: {len(captain_notifications)}")
    
    print("\n✅ All notification filters working correctly!")
    print("✅ Loss-related notifications are hidden")
    print("✅ Team Polls, Pickup Games, and Captain Notifications still work")
    
    return True

if __name__ == "__main__":
    try:
        success = test_notification_filters()
        if success:
            print("\n🎉 All tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 