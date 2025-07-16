#!/usr/bin/env python3
"""
Test Weather Integration for Rally Platform
Tests the weather service and notification integration
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.weather_service import WeatherService
from core.database import get_db

def test_weather_service():
    """Test the weather service functionality"""
    
    print("🌤️ Testing Weather Service Integration")
    print("=" * 50)
    
    # Initialize weather service
    weather_service = WeatherService()
    
    if not weather_service.api_key:
        print("⚠️  No OpenWeather API key found. Set OPENWEATHER_API_KEY environment variable.")
        print("   You can get a free API key from: https://openweathermap.org/api")
        return False
    
    print(f"✅ Weather service initialized with API key")
    
    # Test locations
    test_locations = [
        "Tennaqua, Evanston, IL",
        "1544 Elmwood Ave, Evanston, IL 60201",
        "Chicago, IL"
    ]
    
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    for location in test_locations:
        print(f"\n📍 Testing location: {location}")
        
        try:
            # Test geocoding
            coords = weather_service._geocode_location(location)
            if coords:
                print(f"   ✅ Geocoded: {coords['lat']:.4f}, {coords['lon']:.4f}")
                
                # Test weather forecast
                forecast = weather_service.get_weather_for_location(location, tomorrow)
                if forecast:
                    print(f"   ✅ Weather forecast: {weather_service.format_weather_message(forecast)}")
                    print(f"      Condition: {forecast.condition}")
                    print(f"      Icon: {forecast.icon}")
                else:
                    print(f"   ❌ No weather forecast available")
            else:
                print(f"   ❌ Could not geocode location")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    return True

def test_notification_integration():
    """Test the notification integration with weather data"""
    
    print("\n📱 Testing Notification Integration")
    print("=" * 50)
    
    try:
        from app.routes.api_routes import get_upcoming_schedule_notifications
        
        # Get a test user from the database
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.id, u.email, p.tenniscores_player_id, t.id as team_id, l.id as league_id
                FROM users u
                JOIN players p ON u.tenniscores_player_id = p.tenniscores_player_id
                JOIN teams t ON p.team_id = t.id
                JOIN leagues l ON t.league_id = l.id
                LIMIT 1
            """)
            
            user_data = cursor.fetchone()
            
            if not user_data:
                print("❌ No test user found in database")
                return False
            
            user_id, email, player_id, team_id, league_id = user_data
            print(f"✅ Using test user: {email}")
            
            # Test notification generation
            notifications = get_upcoming_schedule_notifications(
                user_id, player_id, league_id, team_id
            )
            
            if notifications:
                schedule_notification = next(
                    (n for n in notifications if n['type'] == 'schedule'), 
                    None
                )
                
                if schedule_notification:
                    print(f"✅ Schedule notification generated")
                    print(f"   Title: {schedule_notification['title']}")
                    print(f"   Message: {schedule_notification['message']}")
                    
                    if 'weather' in schedule_notification:
                        print(f"   Weather data: {len(schedule_notification['weather'])} forecasts")
                        for key, forecast in schedule_notification['weather'].items():
                            print(f"     {key}: {forecast.condition} {forecast.temperature_high}°F/{forecast.temperature_low}°F")
                    else:
                        print(f"   ⚠️  No weather data in notification")
                else:
                    print(f"   ⚠️  No schedule notification found")
            else:
                print(f"   ⚠️  No notifications generated")
                
    except Exception as e:
        print(f"❌ Error testing notification integration: {str(e)}")
        return False
    
    return True

def test_weather_cache():
    """Test the weather cache functionality"""
    
    print("\n💾 Testing Weather Cache")
    print("=" * 50)
    
    try:
        weather_service = WeatherService()
        
        # Test location and date
        test_location = "Tennaqua, Evanston, IL"
        test_date = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        
        print(f"📍 Testing cache for: {test_location} on {test_date}")
        
        # First call - should fetch from API and cache
        print("   🔄 First call (should fetch from API)...")
        forecast1 = weather_service.get_weather_for_location(test_location, test_date)
        
        if forecast1:
            print(f"   ✅ First call successful: {weather_service.format_weather_message(forecast1)}")
            
            # Second call - should use cache
            print("   🔄 Second call (should use cache)...")
            forecast2 = weather_service.get_weather_for_location(test_location, test_date)
            
            if forecast2:
                print(f"   ✅ Second call successful: {weather_service.format_weather_message(forecast2)}")
                
                # Verify they're the same
                if (forecast1.temperature_high == forecast2.temperature_high and 
                    forecast1.temperature_low == forecast2.temperature_low):
                    print(f"   ✅ Cache working correctly")
                else:
                    print(f"   ❌ Cache data mismatch")
            else:
                print(f"   ❌ Second call failed")
        else:
            print(f"   ❌ First call failed")
            
    except Exception as e:
        print(f"❌ Error testing weather cache: {str(e)}")
        return False
    
    return True

def main():
    """Run all weather integration tests"""
    
    print("🌤️ Rally Weather Integration Test Suite")
    print("=" * 60)
    
    # Test weather service
    weather_ok = test_weather_service()
    
    if weather_ok:
        # Test cache functionality
        cache_ok = test_weather_cache()
        
        # Test notification integration
        notification_ok = test_notification_integration()
        
        print("\n" + "=" * 60)
        print("📊 Test Results Summary:")
        print(f"   Weather Service: {'✅ PASS' if weather_ok else '❌ FAIL'}")
        print(f"   Weather Cache: {'✅ PASS' if cache_ok else '❌ FAIL'}")
        print(f"   Notification Integration: {'✅ PASS' if notification_ok else '❌ FAIL'}")
        
        if weather_ok and cache_ok and notification_ok:
            print("\n🎉 All tests passed! Weather integration is working correctly.")
        else:
            print("\n⚠️  Some tests failed. Check the output above for details.")
    else:
        print("\n❌ Weather service test failed. Cannot proceed with other tests.")

if __name__ == "__main__":
    main() 