#!/usr/bin/env python3
"""
Debug frontend weather rendering logic
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes.api_routes import get_upcoming_schedule_notifications
from datetime import datetime
import json

def debug_frontend_weather():
    """Debug the frontend weather rendering logic"""
    
    print("=== Debug Frontend Weather Rendering ===")
    
    # Test with Ross's user data
    user_id = 43
    player_id = "nndz-WkMrK3didjlnUT09"
    league_id = "4763"
    team_id = "57314"
    
    # Get notifications
    notifications = get_upcoming_schedule_notifications(user_id, player_id, league_id, team_id)
    
    for notification in notifications:
        if notification.get('id') == 'upcoming_schedule':
            print(f"\n✅ Upcoming Schedule notification found!")
            print(f"  Title: {notification.get('title')}")
            print(f"  Message: {notification.get('message')}")
            
            # Simulate the frontend JavaScript logic
            if 'weather' in notification and notification['weather']:
                print(f"  📊 Weather data present: {len(notification['weather'])} entries")
                
                # Parse the message to extract event dates
                message_lines = notification['message'].split('\n')
                event_dates = {}
                
                for line in message_lines:
                    print(f"    Processing line: '{line}'")
                    
                    # Parse practice line: "Practice: Jul 19 at 6:00 AM"
                    import re
                    practice_match = re.search(r'Practice: (\w+ \d+) at', line)
                    if practice_match:
                        event_dates['practice'] = practice_match.group(1)
                        print(f"      ✅ Found practice on {practice_match.group(1)}")
                    
                    # Parse match line: "Match: Jul 17 at 6:00 PM vs Winnetka S2B - Series 2B"
                    match_match = re.search(r'Match: (\w+ \d+) at', line)
                    if match_match:
                        event_dates['match'] = match_match.group(1)
                        print(f"      ✅ Found match on {match_match.group(1)}")
                
                # Check weather data dates
                print(f"    🌤️ Weather data details:")
                for key, forecast in notification['weather'].items():
                    if hasattr(forecast, 'date') and forecast.date:
                        # Convert weather date to display format for comparison
                        weather_date = datetime.strptime(forecast.date, '%Y-%m-%d')
                        weather_display_date = weather_date.strftime('%b %d')
                        
                        print(f"      {key}: {weather_display_date} - {forecast.temperature_high}°F/{forecast.temperature_low}°F, {forecast.condition}")
                        
                        # Check if this weather data matches any event
                        if weather_display_date in event_dates.values():
                            print(f"        ✅ Matches event on {weather_display_date}")
                        else:
                            print(f"        ❌ No matching event for {weather_display_date}")
                    else:
                        print(f"      {key}: Missing date property")
                        
                # Simulate the frontend date matching logic
                print(f"\n    🔍 Frontend Date Matching Simulation:")
                for line in message_lines:
                    if 'Practice:' in line:
                        practice_match = re.search(r'Practice: (\w+ \d+) at', line)
                        if practice_match:
                            event_date = practice_match.group(1)
                            print(f"      Practice date: {event_date}")
                            
                            # Find matching weather data
                            matching_found = False
                            for key, forecast in notification['weather'].items():
                                if hasattr(forecast, 'date') and forecast.date:
                                    weather_date = datetime.strptime(forecast.date, '%Y-%m-%d')
                                    weather_display_date = weather_date.strftime('%b %d')
                                    
                                    if weather_display_date == event_date:
                                        print(f"        ✅ Matched weather: {key}")
                                        matching_found = True
                                        break
                            
                            if not matching_found:
                                print(f"        ❌ No matching weather found")
                    
                    elif 'Match:' in line:
                        match_match = re.search(r'Match: (\w+ \d+) at', line)
                        if match_match:
                            event_date = match_match.group(1)
                            print(f"      Match date: {event_date}")
                            
                            # Find matching weather data
                            matching_found = False
                            for key, forecast in notification['weather'].items():
                                if hasattr(forecast, 'date') and forecast.date:
                                    weather_date = datetime.strptime(forecast.date, '%Y-%m-%d')
                                    weather_display_date = weather_date.strftime('%b %d')
                                    
                                    if weather_display_date == event_date:
                                        print(f"        ✅ Matched weather: {key}")
                                        matching_found = True
                                        break
                            
                            if not matching_found:
                                print(f"        ❌ No matching weather found")
            else:
                print(f"  ❌ No weather data")
            
            return True
    
    print(f"\n❌ No upcoming schedule notification found")
    return False

if __name__ == "__main__":
    debug_frontend_weather() 