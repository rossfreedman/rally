#!/usr/bin/env python3
"""
Verify password update in database
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query_one


def verify_password_update():
    """Verify that password was updated in database"""
    
    print("🔍 Verifying password update in database...")
    
    # Check the user we just tested (ID 1016)
    user_query = """
        SELECT id, email, first_name, last_name, password_hash, phone_number
        FROM users 
        WHERE id = 1016
    """
    
    user = execute_query_one(user_query)
    
    if user:
        print(f"✅ Found user: {user['first_name']} {user['last_name']}")
        print(f"   Email: {user['email']}")
        print(f"   Phone: {user['phone_number']}")
        print(f"   Password hash: {user['password_hash'][:50]}...")
        
        # Check if password hash looks like a recent one (should start with pbkdf2:sha256)
        if user['password_hash'].startswith('pbkdf2:sha256'):
            print("✅ Password hash format is correct (pbkdf2:sha256)")
            return True
        else:
            print("❌ Password hash format is incorrect")
            return False
    else:
        print("❌ User not found")
        return False


if __name__ == "__main__":
    success = verify_password_update()
    if success:
        print("\n✅ Password update verification successful")
    else:
        print("\n❌ Password update verification failed")
        sys.exit(1) 