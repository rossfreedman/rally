#!/usr/bin/env python3

import json
import requests
import traceback

def test_lineup_generation():
    """Test the lineup generation API endpoint"""
    
    # Test data similar to what the frontend would send
    test_data = {
        "players": ["John Doe", "Jane Smith", "Bob Johnson", "Alice Brown"],
        "instructions": ["Jon and Mike should play together"]
    }
    
    try:
        print("🔍 Testing lineup generation API...")
        print(f"Test data: {json.dumps(test_data, indent=2)}")
        
        # Make the API call
        response = requests.post(
            'http://127.0.0.1:8080/api/generate-lineup',
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=60  # 60 second timeout
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print('✅ Lineup generation successful!')
            print(f"Generated lineup: {result.get('suggestion', 'No suggestion returned')[:200]}...")
        else:
            print(f'❌ API returned error status: {response.status_code}')
            try:
                error_data = response.json()
                print(f"Error response: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Raw error response: {response.text}")
                
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - is the server running on http://127.0.0.1:8080?")
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 60 seconds")
    except Exception as e:
        print(f'❌ Lineup generation test failed: {str(e)}')
        print("\n🔍 Full error traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_lineup_generation() 