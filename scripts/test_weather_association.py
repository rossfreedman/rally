#!/usr/bin/env python3
"""
Test weather data association with specific events
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes.api_routes import get_upcoming_schedule_notifications
from datetime import datetime

def test_weather_association():
    """Test that weather data is properly associated with specific events"""
    
    print("=== Testing Weather Data Association ===")
    
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
            print(f"  Title: {notification.get('title')}")
            print(f"  Message: {notification.get('message')}")
            
            # Check weather data
            if 'weather' in notification:
                weather_count = len(notification['weather'])
                print(f"  📊 Weather data: {weather_count} entries")
                
                # Parse the message to extract event dates
                message_lines = notification['message'].split('\n')
                event_dates = {}
                
                for line in message_lines:
                    if 'Practice:' in line:
                        # Extract date from "Practice: Jul 19 at 6:00 AM"
                        import re
                        match = re.search(r'Practice: (\w+ \d+) at', line)
                        if match:
                            event_dates['practice'] = match.group(1)
                            print(f"    📅 Practice date: {match.group(1)}")
                    
                    elif 'Match:' in line:
                        # Extract date from "Match: Jul 17 at 6:00 PM vs Winnetka S2B - Series 2B"
                        import re
                        match = re.search(r'Match: (\w+ \d+) at', line)
                        if match:
                            event_dates['match'] = match.group(1)
                            print(f"    📅 Match date: {match.group(1)}")
                
                # Check weather data dates
                print(f"    🌤️ Weather data details:")
                for key, forecast in notification['weather'].items():
                    if forecast and 'date' in forecast:
                        # Convert weather date to display format
                        weather_date = datetime.strptime(forecast['date'], '%Y-%m-%d')
                        weather_display_date = weather_date.strftime('%b %d')
                        
                        print(f"      {key}: {weather_display_date} - {forecast.get('temperature_high')}°F/{forecast.get('temperature_low')}°F, {forecast.get('condition')}")
                        
                        # Check if this weather data matches any event
                        if weather_display_date in event_dates.values():
                            print(f"        ✅ Matches event on {weather_display_date}")
                        else:
                            print(f"        ❌ No matching event for {weather_display_date}")
            else:
                print(f"  ❌ No weather data")
            
            return True
    
    print(f"\n❌ No upcoming schedule notification found")
    return False

if __name__ == "__main__":
    test_weather_association() 