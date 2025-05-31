#!/usr/bin/env python3
"""
Test script to verify the availability functionality is working correctly
"""

import requests
import json

def test_availability_route():
    """Test that the availability route loads without errors"""
    
    # Test 1: Check that the health endpoint works
    print("=== Test 1: Health Check ===")
    try:
        response = requests.get("http://127.0.0.1:8080/health")
        print(f"Health check status: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print(f"Database status: {health_data.get('database')}")
            print("✅ Health check passed")
        else:
            print("❌ Health check failed")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Test 2: Check that we can access the availability page (this will fail without login but should not 500)
    print("\n=== Test 2: Availability Page Access ===")
    try:
        response = requests.get("http://127.0.0.1:8080/mobile/availability")
        print(f"Availability page status: {response.status_code}")
        
        # We expect 302 (redirect to login) or similar, not 500 (server error)
        if response.status_code in [200, 302, 401, 403]:
            print("✅ Availability route is accessible (no server errors)")
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            print(f"Response content: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"❌ Availability route error: {e}")
        return False
    
    # Test 3: Check API availability endpoint (should also require auth)
    print("\n=== Test 3: API Availability Endpoint ===")
    try:
        response = requests.get("http://127.0.0.1:8080/api/availability")
        print(f"API availability status: {response.status_code}")
        
        # We expect 302 (redirect to login) or similar, not 500 (server error)
        if response.status_code in [200, 302, 401, 403]:
            print("✅ API availability route is accessible (no server errors)")
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            print(f"Response content: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"❌ API availability route error: {e}")
        return False
    
    print("\n🎉 All basic availability tests passed!")
    print("\nNext steps:")
    print("1. Navigate to http://127.0.0.1:8080/mobile/availability in your browser")
    print("2. Log in with your user credentials")
    print("3. Try clicking the availability buttons")
    print("4. Check the browser console for detailed debug logs")
    
    return True

if __name__ == "__main__":
    print("Testing Rally Availability Functionality")
    print("=" * 50)
    
    success = test_availability_route()
    
    if success:
        print("\n✅ All tests passed! The availability routes are working.")
    else:
        print("\n❌ Some tests failed. Check the server logs for more details.") 