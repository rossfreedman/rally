#!/usr/bin/env python3
"""
Test if the weather service is causing the schedule notification issue
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_weather_service():
    """Test if weather service is causing the issue"""
    
    print("🔍 Testing Weather Service")
    print("=" * 40)
    
    # Check if API key is configured
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if api_key:
        print(f"✅ OpenWeather API key is configured")
    else:
        print(f"❌ OpenWeather API key is NOT configured")
        print(f"   This could cause the weather service to fail")
    
    # Test importing the weather service
    try:
        from app.services.weather_service import WeatherService
        print(f"✅ WeatherService import successful")
        
        # Test creating an instance
        weather_service = WeatherService()
        print(f"✅ WeatherService instance created successfully")
        
        # Test a simple weather lookup
        try:
            weather_data = weather_service.get_weather_for_schedule_entries([
                {
                    'id': 'test_1',
                    'location': 'Tennaqua, IL',
                    'match_date': '2025-07-19'
                }
            ])
            print(f"✅ Weather service call completed: {len(weather_data)} results")
            
        except Exception as e:
            print(f"❌ Weather service call failed: {e}")
            
    except Exception as e:
        print(f"❌ WeatherService import failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_weather_service() 