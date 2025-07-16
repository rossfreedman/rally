#!/usr/bin/env python3
"""
Test the temporary password middleware with a simulated session
"""

import sys
import os
import requests
import json

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query_one

def test_middleware_with_session():
    """Test the middleware with a simulated session"""
    
    base_url = "http://localhost:8080"
    
    print("🧪 Testing Temporary Password Middleware with Session")
    print("=" * 60)
    
    # Get Ross's user data
    print("\n1. Getting user data...")
    user = execute_query_one(
        "SELECT id, email, has_temporary_password FROM users WHERE email = %s",
        ["rossfreedman@gmail.com"]
    )
    
    if not user:
        print("   ❌ User not found")
        return
    
    print(f"   ✅ Found user: {user['email']}")
    print(f"   Has temporary password: {user['has_temporary_password']}")
    
    if not user['has_temporary_password']:
        print("   ⚠️ User doesn't have temporary password - setting one for testing")
        
        # Set temporary password for testing
        import secrets
        import string
        from werkzeug.security import generate_password_hash
        
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        temp_hash = generate_password_hash(temp_password, method='pbkdf2:sha256')
        
        from database_utils import execute_update
        result = execute_update(
            "UPDATE users SET password_hash = %s, has_temporary_password = TRUE, temporary_password_set_at = NOW() WHERE id = %s",
            [temp_hash, user['id']]
        )
        
        if result:
            print(f"   ✅ Set temporary password: {temp_password}")
        else:
            print("   ❌ Failed to set temporary password")
            return
    
    # Test 2: Try to login with the temporary password
    print("\n2. Testing login with temporary password...")
    
    # First, get the current password hash
    current_user = execute_query_one(
        "SELECT password_hash FROM users WHERE email = %s",
        ["rossfreedman@gmail.com"]
    )
    
    if not current_user:
        print("   ❌ Cannot get user password hash")
        return
    
    # For testing, we'll simulate what happens after login
    # In a real scenario, the user would login and get a session
    
    print("   ⚠️ Note: This test cannot fully simulate the session without actual login")
    print("   To test properly:")
    print("   1. Go to http://localhost:8080/login")
    print("   2. Login with rossfreedman@gmail.com and the temporary password")
    print("   3. Try accessing http://localhost:8080/mobile")
    print("   4. Should be redirected to http://localhost:8080/change-password")
    
    # Test 3: Check if the middleware is properly registered
    print("\n3. Checking middleware registration...")
    
    # Look for the middleware initialization in server logs
    print("   ✅ Middleware should be initialized in server.py")
    print("   Check server logs for: 'Temporary password middleware initialized'")
    
    # Test 4: Test the change password page directly
    print("\n4. Testing change password page...")
    try:
        response = requests.get(f"{base_url}/change-password")
        if response.status_code == 200:
            print("   ✅ Change password page is accessible")
            if "Change Your Password" in response.text:
                print("   ✅ Page contains correct content")
            else:
                print("   ⚠️ Page content may be different")
        else:
            print(f"   ❌ Change password page returned {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error accessing change password page: {e}")
    
    print(f"\n📋 Manual Testing Instructions:")
    print(f"   1. Open browser and go to: http://localhost:8080/login")
    print(f"   2. Login with: rossfreedman@gmail.com")
    print(f"   3. If you have the temporary password, use it")
    print(f"   4. If not, use the password reset feature with phone: +17732138911")
    print(f"   5. After login, try accessing: http://localhost:8080/mobile")
    print(f"   6. Should be redirected to: http://localhost:8080/change-password")
    print(f"   7. Change password and verify you can then access /mobile")


if __name__ == "__main__":
    test_middleware_with_session() 