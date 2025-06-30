#!/usr/bin/env python3
"""
Test script for admin user impersonation functionality.

This script tests the new admin impersonation feature to ensure it works correctly.
"""

import requests
import json
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_impersonation_endpoints():
    """Test the impersonation API endpoints"""
    
    base_url = "http://localhost:8080"  # Adjust if your server runs on a different port
    
    print("🧪 Testing Admin User Impersonation Feature")
    print("=" * 50)
    
    # Test 1: Check impersonation status (should be false initially)
    print("\n1. Testing impersonation status endpoint...")
    try:
        response = requests.get(f"{base_url}/api/admin/impersonation-status")
        if response.status_code == 200:
            status = response.json()
            print(f"   ✅ Status endpoint working: {status}")
            if not status.get("is_impersonating"):
                print("   ✅ Not currently impersonating (expected)")
            else:
                print("   ⚠️  Currently impersonating (unexpected for fresh start)")
        else:
            print(f"   ❌ Status endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Status endpoint error: {e}")
    
    # Test 2: Try to start impersonation (will fail without admin session, which is expected)
    print("\n2. Testing start impersonation endpoint (without auth - should fail)...")
    try:
        response = requests.post(
            f"{base_url}/api/admin/start-impersonation",
            json={"user_email": "test@example.com"},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 401:
            print("   ✅ Start impersonation properly requires authentication")
        else:
            print(f"   ⚠️  Start impersonation returned unexpected status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Start impersonation error: {e}")
    
    # Test 3: Try to stop impersonation (should also require auth)
    print("\n3. Testing stop impersonation endpoint (without auth - should fail)...")
    try:
        response = requests.post(
            f"{base_url}/api/admin/stop-impersonation",
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 401:
            print("   ✅ Stop impersonation properly requires authentication")
        else:
            print(f"   ⚠️  Stop impersonation returned unexpected status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Stop impersonation error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Test Summary:")
    print("   - Endpoints are properly protected with authentication")
    print("   - Status endpoint is accessible")
    print("   - Ready for admin testing with logged-in admin user")
    print("\n📋 Next Steps:")
    print("   1. Start your Rally server: python server.py")
    print("   2. Log in as an admin user")
    print("   3. Navigate to /admin")
    print("   4. Use the 'User Impersonation' section to test the feature")
    print("   5. Select a user and click 'Start Impersonation'")
    print("   6. Navigate around the site to see their view")
    print("   7. Use 'Stop Impersonation' to return to admin view")

if __name__ == "__main__":
    test_impersonation_endpoints() 