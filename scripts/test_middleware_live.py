#!/usr/bin/env python3
"""
Test the temporary password middleware with the live Flask server
"""

import requests
import json

def test_middleware_live():
    """Test the middleware with the live Flask server"""
    
    base_url = "http://localhost:8080"
    
    print("🧪 Testing Temporary Password Middleware with Live Server")
    print("=" * 60)
    
    # Test 1: Check if server is running
    print("\n1. Testing server health...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("   ✅ Server is running")
        else:
            print(f"   ❌ Server returned status {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Cannot connect to server: {e}")
        return
    
    # Test 2: Test change password page (should be accessible)
    print("\n2. Testing change password page access...")
    try:
        response = requests.get(f"{base_url}/change-password")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Change password page is accessible")
        elif response.status_code == 302:
            print(f"   ⚠️ Redirected to: {response.headers.get('Location')}")
        else:
            print(f"   ❌ Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Test mobile page (should redirect if user has temp password)
    print("\n3. Testing mobile page access...")
    try:
        response = requests.get(f"{base_url}/mobile")
        print(f"   Status: {response.status_code}")
        if response.status_code == 302:
            location = response.headers.get('Location')
            print(f"   ⚠️ Redirected to: {location}")
            if location == "/change-password":
                print("   ✅ Correctly redirected to change password page")
            else:
                print("   ❌ Redirected to wrong location")
        elif response.status_code == 200:
            print("   ⚠️ Page loaded (user might not have temp password)")
        else:
            print(f"   ❌ Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Test API endpoint (should return 403 if user has temp password)
    print("\n4. Testing API endpoint access...")
    try:
        response = requests.get(f"{base_url}/api/schedule")
        print(f"   Status: {response.status_code}")
        if response.status_code == 403:
            try:
                data = response.json()
                if data.get('error') == 'Password change required':
                    print("   ✅ Correctly blocked with password change required message")
                else:
                    print(f"   ⚠️ Blocked but wrong error message: {data}")
            except:
                print("   ⚠️ Blocked but no JSON response")
        elif response.status_code == 401:
            print("   ⚠️ Unauthorized (no session)")
        elif response.status_code == 200:
            print("   ⚠️ API accessible (user might not have temp password)")
        else:
            print(f"   ❌ Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: Test static file access (should be accessible)
    print("\n5. Testing static file access...")
    try:
        response = requests.get(f"{base_url}/static/css/style.css")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Static files are accessible")
        else:
            print(f"   ❌ Static files not accessible: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print(f"\n📋 Summary:")
    print(f"   - Server is running and responding")
    print(f"   - Middleware should be active")
    print(f"   - To test with a real session, you need to:")
    print(f"     1. Login with a user that has temporary password")
    print(f"     2. Try accessing /mobile or other pages")
    print(f"     3. Should be redirected to /change-password")


if __name__ == "__main__":
    test_middleware_live() 