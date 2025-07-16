#!/usr/bin/env python3
"""
Test OpenWeatherMap API Key
Simple script to verify API key functionality
"""

import os
import requests
import json

def test_api_key():
    """Test the OpenWeatherMap API key"""
    
    api_key = os.getenv('OPENWEATHER_API_KEY')
    
    if not api_key:
        print("❌ No OPENWEATHER_API_KEY found in environment")
        return False
    
    print(f"🔑 Testing API Key: {api_key[:8]}...{api_key[-4:]}")
    print("=" * 50)
    
    # Test 1: Geocoding API
    print("📍 Test 1: Geocoding API")
    geocoding_url = f"http://api.openweathermap.org/geo/1.0/direct?q=Chicago,IL&limit=1&appid={api_key}"
    
    try:
        response = requests.get(geocoding_url, timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data:
                print(f"   ✅ Geocoding successful: {data[0]['name']}, {data[0]['country']}")
                print(f"   Coordinates: {data[0]['lat']}, {data[0]['lon']}")
            else:
                print(f"   ⚠️  No results found")
        elif response.status_code == 401:
            print(f"   ❌ Invalid API key")
            print(f"   Response: {response.text}")
        else:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Request failed: {str(e)}")
    
    print()
    
    # Test 2: Current Weather API
    print("🌤️ Test 2: Current Weather API")
    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q=Chicago,IL&appid={api_key}&units=imperial"
    
    try:
        response = requests.get(weather_url, timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Weather API successful")
            print(f"   Temperature: {data['main']['temp']}°F")
            print(f"   Condition: {data['weather'][0]['main']}")
        elif response.status_code == 401:
            print(f"   ❌ Invalid API key")
            print(f"   Response: {response.text}")
        else:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Request failed: {str(e)}")
    
    print()
    
    # Test 3: Forecast API
    print("📅 Test 3: Forecast API")
    forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q=Chicago,IL&appid={api_key}&units=imperial"
    
    try:
        response = requests.get(forecast_url, timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Forecast API successful")
            print(f"   Forecasts available: {len(data['list'])}")
        elif response.status_code == 401:
            print(f"   ❌ Invalid API key")
            print(f"   Response: {response.text}")
        else:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Request failed: {str(e)}")
    
    print()
    print("=" * 50)
    
    # Provide troubleshooting information
    print("🔧 Troubleshooting Information:")
    print("   1. New API keys can take up to 2 hours to activate")
    print("   2. Make sure you're using the correct API key from your dashboard")
    print("   3. Check if you've exceeded the free tier limits (1,000 calls/day)")
    print("   4. Verify the key is copied correctly without extra spaces")
    print()
    print("📚 OpenWeatherMap Documentation:")
    print("   https://openweathermap.org/api")
    print("   https://openweathermap.org/faq#error401")

if __name__ == "__main__":
    test_api_key() 