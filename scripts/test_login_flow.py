#!/usr/bin/env python3
"""
Test script to simulate login flow with temporary password
"""

import sys
import os
import requests
import json

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query_one

def test_login_flow():
    """Test the login flow with temporary password"""
    
    print("🧪 Testing Login Flow with Temporary Password")
    print("=" * 50)
    
    # Test user
    test_email = "rossfreedman@gmail.com"
    test_password = "BDMMSEdD"  # This should be the temporary password
    
    print(f"\n1. Checking user status in database...")
    
    # Check user status
    user = execute_query_one(
        "SELECT id, email, has_temporary_password FROM users WHERE email = %s",
        [test_email]
    )
    
    if not user:
        print("   ❌ User not found")
        return
    
    print(f"   ✅ User found: {user['email']}")
    print(f"   📋 has_temporary_password: {user['has_temporary_password']}")
    
    if not user['has_temporary_password']:
        print("   ⚠️  User doesn't have temporary password - setting it for testing")
        
        # Set temporary password for testing
        from database_utils import execute_update
        execute_update(
            "UPDATE users SET has_temporary_password = TRUE WHERE email = %s",
            [test_email]
        )
        print("   ✅ Set has_temporary_password = TRUE for testing")
    
    print(f"\n2. Testing login API...")
    
    # Test login
    login_data = {
        "email": test_email,
        "password": test_password
    }
    
    try:
        response = requests.post(
            "http://localhost:8080/api/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Login successful")
            print(f"   📋 Response data: {json.dumps(data, indent=2)}")
            
            # Check if redirect is set correctly
            if data.get("has_temporary_password"):
                print(f"   🎯 has_temporary_password: {data['has_temporary_password']}")
                print(f"   🔀 redirect: {data.get('redirect', 'not set')}")
                
                if data.get("redirect") == "/change-password":
                    print("   ✅ Redirect correctly set to /change-password")
                else:
                    print(f"   ❌ Redirect not set correctly: {data.get('redirect')}")
            else:
                print("   ❌ has_temporary_password not set in response")
        else:
            print(f"   ❌ Login failed: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Login request failed: {e}")
    
    print(f"\n3. Testing direct access to /change-password...")
    
    # Test direct access to change password page
    try:
        response = requests.get("http://localhost:8080/change-password")
        print(f"   📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Change password page accessible")
        elif response.status_code == 302:
            print("   🔀 Redirected (expected for unauthenticated user)")
            print(f"   📋 Location header: {response.headers.get('Location', 'not set')}")
        else:
            print(f"   ❌ Unexpected status: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Change password request failed: {e}")
    
    print(f"\n4. Testing access to /mobile (should be blocked)...")
    
    # Test access to mobile page (should be blocked)
    try:
        response = requests.get("http://localhost:8080/mobile")
        print(f"   📊 Response status: {response.status_code}")
        
        if response.status_code == 302:
            print("   🔀 Redirected (expected)")
            print(f"   📋 Location header: {response.headers.get('Location', 'not set')}")
        else:
            print(f"   ❌ Unexpected status: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Mobile page request failed: {e}")

if __name__ == "__main__":
    test_login_flow() 