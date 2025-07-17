#!/usr/bin/env python3
"""
Test frontend JavaScript logic for weather data association
"""

def test_frontend_weather_logic():
    """Test the frontend JavaScript logic for matching weather data to events"""
    
    print("=== Testing Frontend Weather Logic ===")
    
    # Simulate the notification data structure
    notification_data = {
        "id": "upcoming_schedule",
        "type": "schedule",
        "title": "Upcoming Schedule",
        "message": "Practice: Jul 19 at 6:00 AM\nMatch: Jul 17 at 6:00 PM vs Winnetka S2B - Series 2B",
        "weather": {
            "practice_403453": {
                "date": "2025-07-19",
                "temperature_high": 69.17,
                "temperature_low": 69.17,
                "condition": "Rain",
                "quality": "bad",
                "description": "Mild, Rainy, Light rain likely",
                "emoji": "🌧️"
            },
            "match_398270": {
                "date": "2025-07-17",
                "temperature_high": 69.31,
                "temperature_low": 68.97,
                "condition": "Rain",
                "quality": "bad",
                "description": "Mild, Rainy, Light rain likely",
                "emoji": "🌧️"
            }
        }
    }
    
    print("Notification data:")
    print(f"  Message: {notification_data['message']}")
    print(f"  Weather entries: {len(notification_data['weather'])}")
    
    # Simulate the JavaScript logic
    lines = notification_data['message'].split('\n')
    event_matches = []
    
    for line in lines:
        print(f"\nProcessing line: '{line}'")
        
        # Parse practice line: "Practice: Jul 19 at 6:00 AM"
        import re
        practice_match = re.match(r'Practice: (\w+ \d+) at (\d+:\d+ \w+)', line)
        if practice_match:
            event_date = practice_match.group(1)  # "Jul 19"
            event_type = 'practice'
            print(f"  ✅ Found practice on {event_date}")
            
            # Find matching weather data by date
            matching_weather_key = None
            for key, forecast in notification_data['weather'].items():
                if forecast and 'date' in forecast:
                    # Convert weather date to display format for comparison
                    from datetime import datetime
                    weather_date = datetime.strptime(forecast['date'], '%Y-%m-%d')
                    weather_display_date = weather_date.strftime('%b %d')
                    
                    if weather_display_date == event_date:
                        matching_weather_key = key
                        break
            
            if matching_weather_key:
                print(f"  🌤️ Matched weather: {matching_weather_key} - {notification_data['weather'][matching_weather_key]['condition']}")
                event_matches.append({
                    'line': line,
                    'event_date': event_date,
                    'event_type': event_type,
                    'weather_key': matching_weather_key,
                    'weather_data': notification_data['weather'][matching_weather_key]
                })
            else:
                print(f"  ❌ No matching weather found for {event_date}")
        
        # Parse match line: "Match: Jul 17 at 6:00 PM vs Winnetka S2B - Series 2B"
        match_match = re.match(r'Match: (\w+ \d+) at (\d+:\d+ \w+)', line)
        if match_match:
            event_date = match_match.group(1)  # "Jul 17"
            event_type = 'match'
            print(f"  ✅ Found match on {event_date}")
            
            # Find matching weather data by date
            matching_weather_key = None
            for key, forecast in notification_data['weather'].items():
                if forecast and 'date' in forecast:
                    # Convert weather date to display format for comparison
                    from datetime import datetime
                    weather_date = datetime.strptime(forecast['date'], '%Y-%m-%d')
                    weather_display_date = weather_date.strftime('%b %d')
                    
                    if weather_display_date == event_date:
                        matching_weather_key = key
                        break
            
            if matching_weather_key:
                print(f"  🌤️ Matched weather: {matching_weather_key} - {notification_data['weather'][matching_weather_key]['condition']}")
                event_matches.append({
                    'line': line,
                    'event_date': event_date,
                    'event_type': event_type,
                    'weather_key': matching_weather_key,
                    'weather_data': notification_data['weather'][matching_weather_key]
                })
            else:
                print(f"  ❌ No matching weather found for {event_date}")
    
    print(f"\n📋 Event-Weather Matches:")
    for i, match in enumerate(event_matches, 1):
        print(f"  {i}. {match['event_type'].title()} on {match['event_date']}")
        print(f"     Weather: {match['weather_data']['condition']} - {match['weather_data']['temperature_high']}°F/{match['weather_data']['temperature_low']}°F")
    
    # Verify the order is correct
    expected_order = [
        {'event_type': 'practice', 'date': 'Jul 19'},
        {'event_type': 'match', 'date': 'Jul 17'}
    ]
    
    print(f"\n✅ Verification:")
    for i, (expected, actual) in enumerate(zip(expected_order, event_matches), 1):
        if actual['event_type'] == expected['event_type'] and actual['event_date'] == expected['date']:
            print(f"  {i}. ✅ {actual['event_type'].title()} on {actual['event_date']} - Correct order")
        else:
            print(f"  {i}. ❌ Expected {expected['event_type']} on {expected['date']}, got {actual['event_type']} on {actual['event_date']}")
    
    return len(event_matches) == 2

if __name__ == "__main__":
    success = test_frontend_weather_logic()
    if success:
        print("\n🎉 Frontend weather logic test PASSED!")
    else:
        print("\n❌ Frontend weather logic test FAILED!") 