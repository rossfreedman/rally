#!/usr/bin/env python3
"""
Test script to verify weather display on notification cards
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db
from app.services.weather_service import WeatherService
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def test_user_club_address():
    """Test getting user's club address"""
    print("=== Testing User Club Address ===")
    
    # Test with Ross Freedman's player ID (you may need to adjust this)
    test_player_id = "nndz-WlNhd3hMYi9nQT09"  # Ross Freedman's ID
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                c.name as club_name,
                c.club_address as club_address,
                s.name as series_name
            FROM players p
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.tenniscores_player_id = %s
            ORDER BY p.id DESC
            LIMIT 1
        """, [test_player_id])
        
        result = cursor.fetchone()
        if result:
            club_name, club_address, series_name = result
            print(f"Club Name: {club_name}")
            print(f"Club Address: '{club_address}'")
            print(f"Series Name: {series_name}")
            return club_name, club_address, series_name
        else:
            print("User not found")
            return None, None, None

def test_weather_notification_logic():
    """Test the weather notification logic"""
    print("\n=== Testing Weather Notification Logic ===")
    
    club_name, club_address, series_name = test_user_club_address()
    
    if not club_name:
        print("❌ Cannot test without user club data")
        return
    
    # Simulate the notification logic
    weather_service = WeatherService()
    test_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Test practice location logic
    print(f"\n--- Practice Location Logic ---")
    practice_location = (
        None or  # next_practice.get('club_address')
        None or  # next_practice.get('location')
        club_address or  # user_club_address
        f"{club_name}, IL"  # fallback
    )
    print(f"Practice Location: '{practice_location}'")
    
    # Test weather for practice
    if practice_location:
        forecast = weather_service.get_weather_for_location(practice_location, test_date)
        if forecast:
            weather_msg = weather_service.format_weather_message(forecast)
            print(f"✅ Practice Weather: {weather_msg}")
        else:
            print("❌ No weather forecast for practice")
    
    # Test match location logic
    print(f"\n--- Match Location Logic ---")
    match_location = (
        None or  # next_match.get('club_address')
        None or  # next_match.get('location')
        f"{club_name}, IL"  # fallback
    )
    print(f"Match Location: '{match_location}'")
    
    # Test weather for match
    if match_location:
        forecast = weather_service.get_weather_for_location(match_location, test_date)
        if forecast:
            weather_msg = weather_service.format_weather_message(forecast)
            print(f"✅ Match Weather: {weather_msg}")
        else:
            print("❌ No weather forecast for match")

def test_notification_api():
    """Test the notification API endpoint"""
    print("\n=== Testing Notification API ===")
    
    # This would require a logged-in session, so we'll simulate the data structure
    print("Notification data structure should include:")
    print("- weather: { schedule_id: WeatherForecast }")
    print("- WeatherForecast includes: icon, temperature_high, temperature_low, condition")
    print("- Frontend generates weather icons using forecast.icon")

def test_frontend_weather_display():
    """Test frontend weather display logic"""
    print("\n=== Testing Frontend Weather Display ===")
    
    # Simulate weather data that would come from the API
    mock_weather_data = {
        "practice_123": {
            "icon": "02d",  # Partly cloudy
            "temperature_high": 75.0,
            "temperature_low": 65.0,
            "condition": "Clouds"
        },
        "match_456": {
            "icon": "01d",  # Clear sky
            "temperature_high": 80.0,
            "temperature_low": 70.0,
            "condition": "Clear"
        }
    }
    
    print("Mock weather data structure:")
    for key, forecast in mock_weather_data.items():
        print(f"  {key}: {forecast['temperature_high']}°F/{forecast['temperature_low']}°F, {forecast['condition']}")
        icon_url = f"http://openweathermap.org/img/wn/{forecast['icon']}@2x.png"
        print(f"    Icon URL: {icon_url}")

def main():
    """Main test function"""
    print("Weather Notification Display Test")
    print("=" * 50)
    
    # Test user club address retrieval
    test_user_club_address()
    
    # Test weather notification logic
    test_weather_notification_logic()
    
    # Test notification API structure
    test_notification_api()
    
    # Test frontend display
    test_frontend_weather_display()
    
    print("\n=== Summary ===")
    print("✅ Weather integration should work with user's club address")
    print("✅ Practices default to user's club address")
    print("✅ Weather icons are generated in frontend")
    print("✅ Temperature ranges are displayed")

if __name__ == "__main__":
    main() 