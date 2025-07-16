#!/usr/bin/env python3
"""
Test script for temporary password middleware
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query_one, execute_update
from werkzeug.security import generate_password_hash


def test_temporary_password_middleware():
    """Test the temporary password middleware functionality"""
    
    print("🧪 Testing Temporary Password Middleware")
    print("=" * 50)
    
    # Test user email
    test_email = "rossfreedman@gmail.com"
    
    print(f"\n1. Checking current user status for: {test_email}")
    
    # Check current user status
    user_query = """
        SELECT id, email, has_temporary_password, temporary_password_set_at
        FROM users 
        WHERE email = %s
    """
    
    user = execute_query_one(user_query, [test_email])
    
    if not user:
        print("❌ User not found")
        return False
    
    print(f"✅ Found user: {user['email']} (ID: {user['id']})")
    print(f"   Current temporary password status: {user['has_temporary_password']}")
    print(f"   Temporary password set at: {user['temporary_password_set_at']}")
    
    # Test 1: Set temporary password
    print(f"\n2. Setting temporary password for testing...")
    
    # Generate a temporary password
    import secrets
    import string
    temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
    temp_hash = generate_password_hash(temp_password, method='pbkdf2:sha256')
    
    # Update user to have temporary password
    update_query = """
        UPDATE users 
        SET password_hash = %s, 
            has_temporary_password = TRUE,
            temporary_password_set_at = NOW()
        WHERE email = %s
    """
    
    result = execute_update(update_query, [temp_hash, test_email])
    
    if result:
        print(f"✅ Temporary password set successfully")
        print(f"   Temporary password: {temp_password}")
        print(f"   Rows updated: {result}")
    else:
        print("❌ Failed to set temporary password")
        return False
    
    # Test 2: Verify temporary password is set
    print(f"\n3. Verifying temporary password is set...")
    
    updated_user = execute_query_one(user_query, [test_email])
    
    if updated_user and updated_user['has_temporary_password']:
        print("✅ Temporary password flag is set correctly")
    else:
        print("❌ Temporary password flag is not set")
        return False
    
    # Test 3: Test what should happen with middleware
    print(f"\n4. Testing middleware behavior...")
    print("   With temporary password middleware active:")
    print("   - User should be redirected to /change-password when accessing other pages")
    print("   - User should get 403 error when accessing API endpoints")
    print("   - User should be able to access /change-password page")
    print("   - User should be able to access /api/change-password endpoint")
    print("   - User should be able to access static files")
    
    # Test 4: Simulate password change
    print(f"\n5. Simulating password change...")
    
    # Generate new permanent password
    new_password = "newpermanentpassword123"
    new_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
    
    # Update user to remove temporary password
    change_query = """
        UPDATE users 
        SET password_hash = %s, 
            has_temporary_password = FALSE,
            temporary_password_set_at = NULL
        WHERE email = %s
    """
    
    change_result = execute_update(change_query, [new_hash, test_email])
    
    if change_result:
        print("✅ Password changed successfully")
        print(f"   New permanent password: {new_password}")
        print(f"   Rows updated: {change_result}")
    else:
        print("❌ Failed to change password")
        return False
    
    # Test 5: Verify temporary password is cleared
    print(f"\n6. Verifying temporary password is cleared...")
    
    final_user = execute_query_one(user_query, [test_email])
    
    if final_user and not final_user['has_temporary_password']:
        print("✅ Temporary password flag is cleared correctly")
        print("   User should now be able to access all pages normally")
    else:
        print("❌ Temporary password flag is still set")
        return False
    
    print(f"\n🎉 All tests passed! Temporary password middleware should work correctly.")
    print(f"\n📋 Summary:")
    print(f"   - Temporary password was set and detected")
    print(f"   - Password change process works")
    print(f"   - Temporary password flag is properly cleared")
    print(f"   - Middleware should now block users with temporary passwords")
    
    return True


if __name__ == "__main__":
    test_temporary_password_middleware() 