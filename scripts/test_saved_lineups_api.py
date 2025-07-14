#!/usr/bin/env python3
"""
Test script to test the saved lineups API endpoint
"""

import requests
import json

def test_saved_lineups_api():
    """Test the saved lineups API endpoint"""
    print("🔍 Testing Saved Lineups API")
    print("=" * 50)
    
    # Test with the known team_id from the database
    team_id = 57314
    
    print(f"Testing with team_id: {team_id}")
    
    # Make the API call
    url = f"http://localhost:8080/api/saved-lineups?team_id={team_id}"
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response Data: {json.dumps(data, indent=2)}")
        else:
            print(f"Error Response: {response.text}")
            
    except Exception as e:
        print(f"Error making request: {e}")

if __name__ == "__main__":
    test_saved_lineups_api() 