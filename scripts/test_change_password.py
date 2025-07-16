#!/usr/bin/env python3
"""
Test script to debug the change password API issue
"""

import sys
import os
import requests
import json

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_change_password_flow():
    """Test the complete change password flow"""
    
    print("🧪 Testing Change Password Flow")
    print("=" * 50)
    
    # Test user
    test_email = "rossfreedman@gmail.com"
    test_password = "KykrbPfe"  # Temporary password
    
    print(f"\n1. Testing login with temporary password...")
    
    # Step 1: Login to get a session
    login_data = {
        "email": test_email,
        "password": test_password
    }
    
    session = requests.Session()
    
    try:
        login_response = session.post(
            "http://localhost:8080/api/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   📊 Login response status: {login_response.status_code}")
        
        if login_response.status_code == 200:
            login_data = login_response.json()
            print(f"   ✅ Login successful")
            print(f"   📋 has_temporary_password: {login_data.get('has_temporary_password')}")
            print(f"   🔀 redirect: {login_data.get('redirect')}")
            
            if not login_data.get('has_temporary_password'):
                print("   ❌ has_temporary_password is False - this is the problem!")
                return
        else:
            print(f"   ❌ Login failed: {login_response.text}")
            return
            
    except Exception as e:
        print(f"   ❌ Login request failed: {e}")
        return
    
    print(f"\n2. Testing change password API...")
    
    # Step 2: Try to change password
    change_password_data = {
        "newPassword": "NewPassword123",
        "confirmPassword": "NewPassword123"
    }
    
    try:
        change_response = session.post(
            "http://localhost:8080/api/change-password",
            json=change_password_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   📊 Change password response status: {change_response.status_code}")
        
        if change_response.status_code == 200:
            change_data = change_response.json()
            print(f"   ✅ Password change successful")
            print(f"   📋 Response: {json.dumps(change_data, indent=2)}")
        else:
            print(f"   ❌ Password change failed: {change_response.text}")
            
            # Try to parse error response
            try:
                error_data = change_response.json()
                print(f"   📋 Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"   📋 Raw error: {change_response.text}")
                
    except Exception as e:
        print(f"   ❌ Change password request failed: {e}")
    
    print(f"\n3. Testing session data...")
    
    # Step 3: Check session data
    try:
        auth_response = session.get("http://localhost:8080/api/check-auth")
        
        if auth_response.status_code == 200:
            auth_data = auth_response.json()
            print(f"   ✅ Auth check successful")
            print(f"   📋 Authenticated: {auth_data.get('authenticated')}")
            
            if auth_data.get('authenticated') and auth_data.get('user'):
                user_data = auth_data['user']
                print(f"   📋 User email: {user_data.get('email')}")
                print(f"   📋 has_temporary_password: {user_data.get('has_temporary_password')}")
                print(f"   📋 User data keys: {list(user_data.keys())}")
            else:
                print(f"   ❌ Not authenticated or no user data")
        else:
            print(f"   ❌ Auth check failed: {auth_response.text}")
            
    except Exception as e:
        print(f"   ❌ Auth check request failed: {e}")

if __name__ == "__main__":
    test_change_password_flow() 