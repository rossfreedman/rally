#!/usr/bin/env python3
"""
Test script to call the live availability API and get detailed error information
"""

import requests
import json

def test_live_availability_api():
    """Test the live availability API to get detailed error information"""
    
    # You can adjust these test parameters
    base_url = "https://rally-production.up.railway.app"  # Adjust to your Railway URL
    
    test_data = {
        'player_name': 'Ross Freedman',  # Adjust to match your exact name in the database
        'match_date': '2024-10-01',
        'availability_status': 1,
        'series': 'Beginner'  # Adjust to your exact series name
    }
    
    print(f"=== Testing Live Availability API ===")
    print(f"Base URL: {base_url}")
    print(f"Test data: {json.dumps(test_data, indent=2)}")
    
    try:
        # Make the API call
        response = requests.post(
            f"{base_url}/api/availability",
            json=test_data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Python Test Script'
            },
            timeout=30
        )
        
        print(f"\n=== Response Details ===")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        # Try to get the response body
        try:
            response_text = response.text
            print(f"Response Body: {response_text}")
            
            # Try to parse as JSON
            try:
                response_json = response.json()
                print(f"Parsed JSON: {json.dumps(response_json, indent=2)}")
            except json.JSONDecodeError:
                print("Response is not valid JSON")
                
        except Exception as e:
            print(f"Error reading response body: {e}")
            
        return response.status_code == 200
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - check if the server is accessible")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_series_lookup():
    """Test what series are available"""
    base_url = "https://rally-production.up.railway.app"
    
    print(f"\n=== Testing Series Lookup ===")
    try:
        # Try to get clubs/series info (this might require auth)
        response = requests.get(f"{base_url}/api/get-clubs", timeout=10)
        print(f"Clubs API Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                clubs_data = response.json()
                print("Available clubs/series:")
                print(json.dumps(clubs_data, indent=2))
            except:
                print("Could not parse clubs response as JSON")
        else:
            print(f"Clubs API response: {response.text[:200]}")
            
    except Exception as e:
        print(f"Error testing clubs API: {e}")

if __name__ == "__main__":
    print("Testing Live Rally Availability API")
    print("=" * 50)
    
    # Test the availability API
    success = test_live_availability_api()
    
    # Test series lookup
    test_series_lookup()
    
    print(f"\n{'✅ Test completed successfully' if success else '❌ Test failed'}")
    print("\nIf the test failed, check:")
    print("1. Your Railway URL is correct")
    print("2. Your player name matches exactly what's in the database")
    print("3. Your series name matches exactly what's in the database")
    print("4. The server is running and accessible") 