#!/usr/bin/env python3
"""
Debug weather display to see why both weather cards are showing the same data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes.api_routes import get_upcoming_schedule_notifications
from datetime import datetime

def debug_weather_display():
    """Debug the weather display logic"""
    
    print("=== Debug Weather Display ===")
    
    # Test with Ross's user data
    user_id = 1
    player_id = "nndz-WlNhd3hMYi9nQT09"
    league_id = "4489"
    team_id = "47092"
    
    # Get notifications
    notifications = get_upcoming_schedule_notifications(user_id, player_id, league_id, team_id)
    
    for notification in notifications:
        if notification.get('id') == 'upcoming_schedule':
            print(f"\nNotification: {notification.get('title')}")
            print(f"Message: {notification.get('message')}")
            
            if 'weather' in notification:
                weather_data = notification['weather']
                print(f"\nWeather data keys: {list(weather_data.keys())}")
                
                for key, forecast in weather_data.items():
                    print(f"\n{key}:")
                    print(f"  Temperature: {forecast.temperature_high}°F/{forecast.temperature_low}°F")
                    print(f"  Condition: {forecast.condition}")
                    print(f"  Icon: {forecast.icon}")
                    print(f"  Quality: {getattr(forecast, 'quality', 'N/A')}")
                    print(f"  Description: {getattr(forecast, 'description', 'N/A')}")
                    print(f"  Emoji: {getattr(forecast, 'emoji', 'N/A')}")
                    
                    # Test the frontend rendering logic
                    print(f"\nFrontend rendering test for {key}:")
                    test_weather = {key: forecast}
                    print(f"  Weather object: {test_weather}")
                    
                    # Simulate the frontend logic
                    if key.startswith('practice_'):
                        print(f"  Would render under practice line")
                    elif key.startswith('match_'):
                        print(f"  Would render under match line")
            else:
                print("No weather data")

if __name__ == "__main__":
    debug_weather_display() 