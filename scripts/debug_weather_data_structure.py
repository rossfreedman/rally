#!/usr/bin/env python3
"""
Debug weather data structure to understand what's being returned
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes.api_routes import get_upcoming_schedule_notifications
import json

def debug_weather_data_structure():
    """Debug the weather data structure being returned"""
    
    print("=== Debug Weather Data Structure ===")
    
    # Test with Ross's user data
    user_id = 43  # Ross's user ID from logs
    player_id = "nndz-WkMrK3didjlnUT09"  # Ross's player ID from logs
    league_id = "4763"  # League ID from logs
    team_id = "57314"  # Team ID from logs
    
    print(f"Testing with user data:")
    print(f"  User ID: {user_id}")
    print(f"  Player ID: {player_id}")
    print(f"  League ID: {league_id}")
    print(f"  Team ID: {team_id}")
    
    # Get notifications
    notifications = get_upcoming_schedule_notifications(user_id, player_id, league_id, team_id)
    
    print(f"\nFound {len(notifications)} notifications")
    
    for notification in notifications:
        if notification.get('id') == 'upcoming_schedule':
            print(f"\n✅ Upcoming Schedule notification found!")
            print(f"  Title: {notification.get('title')}")
            print(f"  Message: {notification.get('message')}")
            
            # Check weather data
            if 'weather' in notification:
                weather_data = notification['weather']
                print(f"  📊 Weather data type: {type(weather_data)}")
                print(f"  📊 Weather data keys: {list(weather_data.keys()) if isinstance(weather_data, dict) else 'Not a dict'}")
                
                if isinstance(weather_data, dict):
                    for key, value in weather_data.items():
                        print(f"    Key: {key}")
                        print(f"    Value type: {type(value)}")
                        print(f"    Value: {json.dumps(value, indent=4, default=str)}")
                        print()
                else:
                    print(f"    Weather data is not a dict: {weather_data}")
            else:
                print(f"  ❌ No weather data")
            
            return True
    
    print(f"\n❌ No upcoming schedule notification found")
    return False

if __name__ == "__main__":
    debug_weather_data_structure() 