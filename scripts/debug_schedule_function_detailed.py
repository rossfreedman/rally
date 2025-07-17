#!/usr/bin/env python3
"""
Detailed debug of schedule notification function to find exact exception location
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one

def debug_schedule_function_detailed():
    """Debug the schedule notification function with detailed tracing"""
    
    print("🔍 Detailed Debug of Schedule Notification Function")
    print("=" * 60)
    
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
    
    notifications = []
    
    try:
        print(f"\n1. Checking team_id...")
        if not team_id:
            print("❌ team_id is None or empty")
            return notifications
        print("✅ team_id is valid")
        
        print(f"\n2. Getting user's team information...")
        user_info_query = """
            SELECT 
                c.name as club_name,
                s.name as series_name
            FROM players p
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.tenniscores_player_id = %s
            ORDER BY p.id DESC
            LIMIT 1
        """
        
        user_info = execute_query_one(user_info_query, [player_id])
        if not user_info:
            print("❌ No user info found for player_id")
            return notifications
            
        user_club = user_info.get("club_name")
        user_series = user_info.get("series_name")
        
        print(f"✅ User info found:")
        print(f"   Club: {user_club}")
        print(f"   Series: {user_series}")
        
        if not user_club or not user_series:
            print("❌ Missing club or series information")
            return notifications
        
        print(f"\n3. Building team patterns...")
        # Build team pattern for matches
        if "Series" in user_series:
            series_code = user_series.replace("Series ", "S")
            team_pattern = f"{user_club} {series_code} - {user_series}"
        elif "Division" in user_series:
            division_num = user_series.replace("Division ", "")
            team_pattern = f"{user_club} {division_num} - Series {division_num}"
        else:
            series_num = user_series.split()[-1] if user_series else ""
            team_pattern = f"{user_club} - {series_num}"
        
        # Build practice pattern
        if "Division" in user_series:
            division_num = user_series.replace("Division ", "")
            practice_pattern = f"{user_club} Practice - Series {division_num}"
        else:
            practice_pattern = f"{user_club} Practice - {user_series}"
        
        print(f"✅ Team patterns built:")
        print(f"   Team pattern: {team_pattern}")
        print(f"   Practice pattern: {practice_pattern}")
        
        print(f"\n4. Getting current date...")
        now = datetime.now()
        current_date = now.date()
        print(f"✅ Current date: {current_date}")
        
        print(f"\n5. Querying upcoming schedule entries...")
        schedule_query = """
            SELECT 
                s.id,
                s.match_date,
                s.match_time,
                s.home_team_id,
                s.away_team_id,
                s.home_team,
                s.away_team,
                s.location,
                c.club_address,
                CASE 
                    WHEN s.home_team_id = %s THEN 'practice'
                    ELSE 'match'
                END as type
            FROM schedule s
            LEFT JOIN teams t ON (s.home_team_id = t.id OR s.away_team_id = t.id)
            LEFT JOIN clubs c ON t.club_id = c.id
            WHERE (s.home_team_id = %s OR s.away_team_id = %s)
            AND s.match_date >= %s
            ORDER BY s.match_date ASC, s.match_time ASC
            LIMIT 10
        """
        
        schedule_entries = execute_query(schedule_query, [team_id, team_id, team_id, current_date])
        print(f"✅ Found {len(schedule_entries)} schedule entries")
        
        if not schedule_entries:
            print("❌ No schedule entries found")
            return notifications
        
        print(f"\n6. Converting to dictionaries...")
        # The execute_query function already returns RealDictRow objects (dictionaries)
        # So we don't need to convert them, just use them directly
        print(f"✅ Schedule entries are already dictionaries: {len(schedule_entries)} entries")
        
        # Show sample of the data structure
        if schedule_entries:
            sample = schedule_entries[0]
            print(f"   Sample entry keys: {list(sample.keys())}")
            print(f"   Sample entry: {dict(sample)}")
        
        print(f"\n7. Finding next practice and next match...")
        next_practice = None
        next_match = None
        
        for entry in schedule_entries:
            if entry["type"] == "practice" and not next_practice:
                next_practice = entry
                print(f"✅ Found next practice: {entry['match_date']} {entry['match_time']}")
            elif entry["type"] == "match" and not next_match:
                next_match = entry
                print(f"✅ Found next match: {entry['match_date']} {entry['match_time']}")
            
            if next_practice and next_match:
                break
        
        print(f"\n8. Getting weather data...")
        weather_data = {}
        try:
            from app.services.weather_service import WeatherService
            weather_service = WeatherService()
            
            # Prepare schedule entries for weather lookup
            weather_entries = []
            if next_practice:
                weather_entries.append({
                    'id': f"practice_{next_practice['id']}",
                    'location': next_practice.get('club_address') or next_practice.get('location') or f"{user_club}, IL",
                    'match_date': next_practice['match_date'].strftime('%Y-%m-%d')
                })
            
            if next_match:
                weather_entries.append({
                    'id': f"match_{next_match['id']}",
                    'location': next_match.get('club_address') or next_match.get('location') or f"{user_club}, IL",
                    'match_date': next_match['match_date'].strftime('%Y-%m-%d')
                })
            
            # Get weather forecasts
            weather_data = weather_service.get_weather_for_schedule_entries(weather_entries)
            print(f"✅ Weather data retrieved: {len(weather_data)} forecasts")
            
        except Exception as e:
            print(f"❌ Weather service error: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n9. Building notification message...")
        practice_text = "No upcoming practices"
        match_text = "No upcoming matches"
        
        if next_practice:
            practice_date = next_practice["match_date"].strftime("%b %d")
            practice_time = next_practice["match_time"].strftime("%I:%M %p").lstrip("0") if next_practice["match_time"] else ""
            practice_text = f"Practice: {practice_date}"
            if practice_time:
                practice_text += f" at {practice_time}"
            print(f"✅ Practice text: {practice_text}")
        
        if next_match:
            match_date = next_match["match_date"].strftime("%b %d")
            match_time = next_match["match_time"].strftime("%I:%M %p").lstrip("0") if next_match["match_time"] else ""
            # Determine opponent using team_id
            if next_match["home_team_id"] == team_id:
                opponent = next_match["away_team"]
            else:
                opponent = next_match["home_team"]
            match_text = f"Match: {match_date}"
            if match_time:
                match_text += f" at {match_time}"
            if opponent:
                match_text += f" vs {opponent}"
            print(f"✅ Match text: {match_text}")
        
        print(f"\n10. Creating notification...")
        notification_data = {
            "id": "upcoming_schedule",
            "type": "schedule",
            "title": "Upcoming Schedule",
            "message": f"{practice_text}\n{match_text}",
            "cta": {"label": "View Schedule", "href": "/mobile/availability"},
            "priority": 2
        }
        
        print(f"✅ Notification created:")
        print(f"   ID: {notification_data['id']}")
        print(f"   Title: {notification_data['title']}")
        print(f"   Message: {notification_data['message']}")
        print(f"   Type: {notification_data['type']}")
        print(f"   Priority: {notification_data['priority']}")
        
        # Add weather data to notification if available
        if weather_data:
            print(f"\n11. Adding weather data...")
            # Convert WeatherForecast objects to dictionaries for JSON serialization
            weather_dict = {}
            for key, forecast in weather_data.items():
                if hasattr(forecast, '__dict__'):
                    weather_dict[key] = {
                        'date': forecast.date,
                        'temperature_high': forecast.temperature_high,
                        'temperature_low': forecast.temperature_low,
                        'condition': forecast.condition,
                        'condition_code': forecast.condition_code,
                        'precipitation_chance': forecast.precipitation_chance,
                        'wind_speed': forecast.wind_speed,
                        'humidity': forecast.humidity,
                        'icon': forecast.icon
                    }
                else:
                    weather_dict[key] = forecast
            notification_data["weather"] = weather_dict
            print(f"✅ Weather data added to notification")
        
        print(f"\n12. Adding notification to list...")
        notifications.append(notification_data)
        print(f"✅ Notification added to list. Total notifications: {len(notifications)}")
        
        print(f"\n🎉 Function completed successfully!")
        print(f"   The notification should be generated and returned")
        
    except Exception as e:
        print(f"\n❌ Exception occurred: {e}")
        print(f"   Exception type: {type(e)}")
        import traceback
        traceback.print_exc()
    
    return notifications

if __name__ == "__main__":
    result = debug_schedule_function_detailed()
    print(f"\nFinal result: {len(result)} notifications")
    for i, notification in enumerate(result):
        print(f"  Notification {i+1}: {notification.get('title')}") 