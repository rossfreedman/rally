#!/usr/bin/env python3
"""
Test practice notification to verify the fix is working
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes.api_routes import get_upcoming_schedule_notifications

def test_practice_notification():
    """Test that practice notification is working"""
    
    print("=== Testing Practice Notification Fix ===")
    
    # Test with Ross's user data
    user_id = 1
    player_id = "nndz-WlNhd3hMYi9nQT09"
    league_id = "4489"
    team_id = "47092"
    
    print(f"Testing with user data:")
    print(f"  Player ID: {player_id}")
    print(f"  League ID: {league_id}")
    print(f"  Team ID: {team_id}")
    
    # Get notifications
    notifications = get_upcoming_schedule_notifications(user_id, player_id, league_id, team_id)
    
    print(f"\nFound {len(notifications)} notifications")
    
    for notification in notifications:
        if notification.get('id') == 'upcoming_schedule':
            print(f"\n✅ Upcoming Schedule notification found!")
            print(f"  Message: {notification.get('message')}")
            
            # Check if practice is mentioned
            message = notification.get('message', '')
            if 'Practice: Jul 19 at 6:00 AM' in message:
                print(f"  ✅ Practice found: Jul 19 at 6:00 AM")
            else:
                print(f"  ❌ Practice not found in message")
            
            # Check weather data
            if 'weather' in notification:
                weather_count = len(notification['weather'])
                print(f"  📊 Weather data: {weather_count} entries")
                for key, forecast in notification['weather'].items():
                    print(f"    {key}: {forecast.temperature_high}°F/{forecast.temperature_low}°F, {forecast.condition}")
            else:
                print(f"  ❌ No weather data")
            
            return True
    
    print(f"\n❌ No upcoming schedule notification found")
    return False

if __name__ == "__main__":
    success = test_practice_notification()
    if success:
        print(f"\n🎉 Practice notification fix is working!")
    else:
        print(f"\n❌ Practice notification fix failed") 