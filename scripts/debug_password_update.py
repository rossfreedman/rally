#!/usr/bin/env python3
"""
Debug password update issue
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query_one, execute_query
from werkzeug.security import generate_password_hash, check_password_hash


def debug_password_update():
    """Debug why password update isn't working"""
    
    print("🔍 Debugging password update issue...")
    
    # Find the user by phone number
    phone = "7732138911"
    
    print(f"\n1. Looking up user by phone: {phone}")
    user_query = """
        SELECT id, email, first_name, last_name, password_hash, phone_number
        FROM users 
        WHERE phone_number = %s
    """
    
    user = execute_query_one(user_query, [phone])
    
    if not user:
        print("❌ User not found")
        return False
    
    print(f"✅ Found user: {user['first_name']} {user['last_name']} (ID: {user['id']})")
    print(f"   Current password hash: {user['password_hash'][:50]}...")
    
    # Test if "test" password works with current hash
    print(f"\n2. Testing if 'test' password works with current hash...")
    test_password_works = check_password_hash(user['password_hash'], "test")
    print(f"   'test' password works: {test_password_works}")
    
    # Generate a new password hash manually
    print(f"\n3. Generating new password hash manually...")
    new_password = "temp123"
    new_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
    print(f"   New password: {new_password}")
    print(f"   New hash: {new_hash[:50]}...")
    
    # Update the password manually
    print(f"\n4. Updating password manually...")
    from database_utils import execute_update
    
    update_query = """
        UPDATE users 
        SET password_hash = %s 
        WHERE id = %s
    """
    
    result = execute_update(update_query, [new_hash, user['id']])
    print(f"   Update result: {result}")
    
    # Verify the update
    print(f"\n5. Verifying password update...")
    updated_user = execute_query_one(user_query, [phone])
    print(f"   Updated hash: {updated_user['password_hash'][:50]}...")
    
    # Test if new password works
    new_password_works = check_password_hash(updated_user['password_hash'], new_password)
    print(f"   New password works: {new_password_works}")
    
    # Test if old password still works
    old_password_works = check_password_hash(updated_user['password_hash'], "test")
    print(f"   Old password still works: {old_password_works}")
    
    return True


if __name__ == "__main__":
    success = debug_password_update()
    if success:
        print("\n✅ Password update debug completed")
    else:
        print("\n❌ Password update debug failed")
        sys.exit(1) 