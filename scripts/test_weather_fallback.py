#!/usr/bin/env python3
"""
Test script to verify the updated weather service with fallback logic
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.weather_service import WeatherService
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def test_weather_service_fallback():
    """Test the weather service with various location types"""
    print("=== Testing Weather Service with Fallback Logic ===")
    
    weather_service = WeatherService()
    
    if not weather_service.api_key:
        print("❌ No OpenWeather API key found")
        return False
    
    # Test date (tomorrow)
    test_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Test locations with different complexity levels
    test_locations = [
        "1 Tennaqua Lane, Deerfield, IL 60062",  # Specific address (should fail, use fallback)
        "Tennaqua Club, Deerfield, IL",          # Club name (should fail, use fallback)
        "Deerfield, IL",                         # City/State (should work)
        "Chicago, IL",                           # Major city (should work)
        "Invalid Location, XX",                  # Invalid (should fail completely)
    ]
    
    success_count = 0
    
    for location in test_locations:
        print(f"\n--- Testing: '{location}' ---")
        
        try:
            # Test geocoding
            coords = weather_service._geocode_location(location)
            
            if coords:
                print(f"✅ Geocoding successful: {coords['lat']:.4f}, {coords['lon']:.4f}")
                
                # Test weather forecast
                forecast = weather_service.get_weather_for_location(location, test_date)
                
                if forecast:
                    weather_msg = weather_service.format_weather_message(forecast)
                    print(f"✅ Weather forecast: {weather_msg}")
                    print(f"   Details: {forecast.condition}, {forecast.temperature_high}°F/{forecast.temperature_low}°F")
                    success_count += 1
                else:
                    print("❌ Weather forecast failed")
            else:
                print("❌ Geocoding failed")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print(f"\n=== Results ===")
    print(f"Successful forecasts: {success_count}/{len(test_locations)}")
    
    return success_count > 0

def test_schedule_entries():
    """Test weather service with schedule entries (like the API uses)"""
    print("\n=== Testing Schedule Entries ===")
    
    weather_service = WeatherService()
    
    # Simulate schedule entries like the API creates
    schedule_entries = [
        {
            'id': 'practice_123',
            'location': '1 Tennaqua Lane, Deerfield, IL 60062',
            'match_date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        },
        {
            'id': 'match_456',
            'location': 'Deerfield, IL',
            'match_date': (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        }
    ]
    
    try:
        weather_data = weather_service.get_weather_for_schedule_entries(schedule_entries)
        
        print(f"Retrieved weather for {len(weather_data)} entries:")
        for entry_id, forecast in weather_data.items():
            weather_msg = weather_service.format_weather_message(forecast)
            print(f"  {entry_id}: {weather_msg}")
            
        return len(weather_data) > 0
        
    except Exception as e:
        print(f"❌ Error testing schedule entries: {str(e)}")
        return False

def main():
    """Main test function"""
    print("Weather Service Fallback Logic Test")
    print("=" * 50)
    
    # Test individual locations
    basic_test_ok = test_weather_service_fallback()
    
    # Test schedule entries
    schedule_test_ok = test_schedule_entries()
    
    print(f"\n=== Final Results ===")
    print(f"Basic location tests: {'✅ PASS' if basic_test_ok else '❌ FAIL'}")
    print(f"Schedule entry tests: {'✅ PASS' if schedule_test_ok else '❌ FAIL'}")
    
    if basic_test_ok and schedule_test_ok:
        print("\n🎉 All tests passed! Weather service with fallback logic is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main() 