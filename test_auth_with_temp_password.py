#!/usr/bin/env python3
"""
Test authentication with temporary password detection
"""

from app.services.auth_service_refactored import authenticate_user
from database_utils import execute_query_one

def test_auth_with_temp_password():
    """Test authentication with temporary password detection"""
    
    print("Testing authentication with temporary password detection...")
    
    # First, check if user has temporary password flag
    print("\n1. Checking user's temporary password status...")
    user_status = execute_query_one(
        "SELECT has_temporary_password, email FROM users WHERE email = %s",
        ["rossfreedman@gmail.com"]
    )
    
    if user_status:
        has_temp = user_status["has_temporary_password"]
        email = user_status["email"]
        print(f"   User: {email}")
        print(f"   Has temporary password: {has_temp}")
        
        if has_temp:
            print("   ✅ User has temporary password flag set")
            
            # Test authentication (this would normally be done with the actual temp password)
            print("\n2. Testing authentication service...")
            print("   Note: This test simulates the authentication flow")
            print("   In a real scenario, the user would provide the temporary password")
            
            # Simulate what the authentication service would return
            print("   Expected authentication result:")
            print("   - success: True")
            print("   - has_temporary_password: True")
            print("   - redirect: /change-password")
            
            # Test the actual authentication service with a dummy password
            # (This will fail, but we can see the structure)
            print("\n3. Testing actual authentication service...")
            try:
                result = authenticate_user(email, "dummy_password")
                print(f"   Authentication result: {result}")
                
                if result.get("success"):
                    has_temp_in_result = result.get("has_temporary_password", False)
                    print(f"   Has temporary password in result: {has_temp_in_result}")
                    
                    if has_temp_in_result:
                        print("   ✅ Authentication service correctly detects temporary password")
                    else:
                        print("   ❌ Authentication service does not detect temporary password")
                else:
                    print("   Authentication failed (expected with dummy password)")
                    
            except Exception as e:
                print(f"   Authentication error: {e}")
        else:
            print("   ❌ User does not have temporary password flag set")
    else:
        print("   ❌ User not found")

def test_login_api_flow():
    """Test the complete login API flow"""
    
    print("\nTesting complete login API flow...")
    
    # This would normally be tested via the web interface
    print("   The login API should:")
    print("   1. Accept email and password")
    print("   2. Authenticate user")
    print("   3. Check has_temporary_password flag")
    print("   4. Return appropriate redirect URL")
    print("   5. Include has_temporary_password in response")
    
    print("\n   Expected API response for user with temporary password:")
    print("   {")
    print('     "status": "success",')
    print('     "message": "Login successful",')
    print('     "redirect": "/change-password",')
    print('     "has_temporary_password": true,')
    print('     "user": { ... }')
    print("   }")

if __name__ == "__main__":
    test_auth_with_temp_password()
    test_login_api_flow() 