#!/usr/bin/env python3
"""
Debug script for HomePageNotifications API
"""

import requests
import json
from datetime import datetime

def test_notifications_with_session():
    """Test the notifications API with a session"""
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    # First, try to get the login page to see if we can establish a session
    try:
        print("Testing server connectivity...")
        response = session.get("http://localhost:8080/")
        print(f"Home page status: {response.status_code}")
        
        # Try the notifications API
        print("\nTesting notifications API...")
        response = session.get("http://localhost:8080/api/home/notifications")
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 401:
            print("✅ API requires authentication (expected)")
            return True
        elif response.status_code == 200:
            data = response.json()
            print(f"✅ API works! Response: {json.dumps(data, indent=2)}")
            return True
        elif response.status_code == 500:
            print(f"❌ 500 Error - Response: {response.text}")
            return False
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running on port 8080?")
        return False
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        return False

def test_database_connection():
    """Test if we can connect to the database"""
    try:
        from database_utils import execute_query_one
        print("\nTesting database connection...")
        
        # Simple test query
        result = execute_query_one("SELECT 1 as test")
        if result:
            print("✅ Database connection successful")
            return True
        else:
            print("❌ Database query returned no results")
            return False
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_notification_functions():
    """Test the notification functions directly"""
    try:
        from app.routes.api_routes import get_fallback_notifications
        print("\nTesting notification functions...")
        
        # Test fallback notifications
        fallbacks = get_fallback_notifications(1, None, None, None)
        print(f"✅ Fallback notifications generated: {len(fallbacks)}")
        for fb in fallbacks:
            print(f"  - {fb['title']}: {fb['message'][:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Notification functions failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== HomePageNotifications Debug Test ===")
    print(f"Time: {datetime.now()}")
    
    # Test database connection
    db_ok = test_database_connection()
    
    # Test notification functions
    func_ok = test_notification_functions()
    
    # Test API endpoint
    api_ok = test_notifications_with_session()
    
    print(f"\n=== Results ===")
    print(f"Database: {'✅' if db_ok else '❌'}")
    print(f"Functions: {'✅' if func_ok else '❌'}")
    print(f"API: {'✅' if api_ok else '❌'}")
    
    if not all([db_ok, func_ok, api_ok]):
        print("\n❌ Some tests failed - check the errors above")
    else:
        print("\n✅ All tests passed!") 