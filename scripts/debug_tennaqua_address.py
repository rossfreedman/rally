#!/usr/bin/env python3
"""
Debug script to check Tennaqua club address and test geocoding
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db
import requests
from dotenv import load_dotenv

load_dotenv()

def check_tennaqua_address():
    """Check Tennaqua club address in database"""
    print("=== Checking Tennaqua Club Address ===")
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT name, club_address FROM clubs WHERE name ILIKE %s', ('%tennaqua%',))
        result = cursor.fetchone()
        
        if result:
            club_name, club_address = result
            print(f"Club Name: {club_name}")
            print(f"Club Address: '{club_address}'")
            print(f"Address Length: {len(club_address) if club_address else 0}")
            print(f"Is Empty: {not club_address or club_address.strip() == ''}")
        else:
            print("Tennaqua club not found in database")
            return None
    
    return club_address

def test_geocoding(address):
    """Test geocoding with OpenWeatherMap API, using fallback if needed"""
    print("\n=== Testing Geocoding ===")
    
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        print("ERROR: OPENWEATHER_API_KEY not found in environment")
        return
    
    # Address variants to try (all with US)
    test_addresses = [
        address + ", US" if address and not address.strip().endswith(", US") else address,
        "Tennaqua Club, Deerfield, IL, US",
        "Tennaqua, Deerfield, IL, US",
        "Deerfield, IL, US"
    ]
    
    found_location = None
    used_address = None
    for test_addr in test_addresses:
        if not test_addr or test_addr.strip() == '':
            continue
        print(f"\nTesting address: '{test_addr}'")
        
        # Geocoding API call
        geocode_url = "http://api.openweathermap.org/geo/1.0/direct"
        params = {
            'q': test_addr,
            'limit': 1,
            'appid': api_key
        }
        try:
            response = requests.get(geocode_url, params=params, timeout=10)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if data:
                    location = data[0]
                    print(f"Found: {location.get('name', 'N/A')}, {location.get('state', 'N/A')}, {location.get('country', 'N/A')}")
                    print(f"Coordinates: {location.get('lat', 'N/A')}, {location.get('lon', 'N/A')}")
                    found_location = location
                    used_address = test_addr
                    break
                else:
                    print("❌ No location found")
            else:
                print(f"❌ Geocoding API Error: {response.status_code}")
                if response.status_code == 401:
                    print("   This usually means the API key is invalid or not activated yet")
                print(f"   Response: {response.text[:200]}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    if found_location:
        print(f"\n✅ Using address for weather: '{used_address}'")
        lat, lon = found_location['lat'], found_location['lon']
        weather_url = "https://api.openweathermap.org/data/2.5/forecast"
        weather_params = {
            'lat': lat,
            'lon': lon,
            'appid': api_key,
            'units': 'imperial'
        }
        weather_response = requests.get(weather_url, params=weather_params, timeout=10)
        if weather_response.status_code == 200:
            weather_data = weather_response.json()
            if weather_data.get('list'):
                first_forecast = weather_data['list'][0]
                temp = first_forecast['main']['temp']
                description = first_forecast['weather'][0]['description']
                print(f"Weather Test: {temp}°F, {description}")
                print("✅ Geocoding and weather API working!")
                return True
        else:
            print(f"Weather API Error: {weather_response.status_code}")
    else:
        print("\n❌ All address variants failed. Using fallback: 'Deerfield, IL, US'")
        # Fallback to Deerfield, IL, US
        fallback_addr = "Deerfield, IL, US"
        geocode_url = "http://api.openweathermap.org/geo/1.0/direct"
        params = {
            'q': fallback_addr,
            'limit': 1,
            'appid': api_key
        }
        response = requests.get(geocode_url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                location = data[0]
                print(f"Fallback Found: {location.get('name', 'N/A')}, {location.get('state', 'N/A')}, {location.get('country', 'N/A')}")
                print(f"Coordinates: {location.get('lat', 'N/A')}, {location.get('lon', 'N/A')}")
                lat, lon = location['lat'], location['lon']
                weather_url = "https://api.openweathermap.org/data/2.5/forecast"
                weather_params = {
                    'lat': lat,
                    'lon': lon,
                    'appid': api_key,
                    'units': 'imperial'
                }
                weather_response = requests.get(weather_url, params=weather_params, timeout=10)
                if weather_response.status_code == 200:
                    weather_data = weather_response.json()
                    if weather_data.get('list'):
                        first_forecast = weather_data['list'][0]
                        temp = first_forecast['main']['temp']
                        description = first_forecast['weather'][0]['description']
                        print(f"Weather Test: {temp}°F, {description}")
                        print("✅ Fallback geocoding and weather API working!")
                        return True
                else:
                    print(f"Weather API Error: {weather_response.status_code}")
            else:
                print("❌ Fallback location not found")
        else:
            print(f"❌ Fallback geocoding API Error: {response.status_code}")

def main():
    """Main function"""
    print("Tennaqua Club Address Debug Script")
    print("=" * 50)
    
    # Check database address
    address = check_tennaqua_address()
    
    # Test geocoding
    if address:
        test_geocoding(address)
    else:
        print("\nNo address found in database, testing with known good addresses...")
        test_geocoding("")

if __name__ == "__main__":
    main() 