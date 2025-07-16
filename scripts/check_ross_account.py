#!/usr/bin/env python3
"""
Check Ross Freedman's account details
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query_one
from werkzeug.security import check_password_hash


def check_ross_account():
    """Check Ross Freedman's account details"""
    
    print("🔍 Checking Ross Freedman's account...")
    
    email = "rossfreedman@gmail.com"
    
    user_query = """
        SELECT id, email, first_name, last_name, password_hash, phone_number
        FROM users 
        WHERE email = %s
    """
    
    user = execute_query_one(user_query, [email])
    
    if not user:
        print("❌ Ross Freedman account not found")
        return False
    
    print(f"✅ Found Ross Freedman:")
    print(f"   ID: {user['id']}")
    print(f"   Email: {user['email']}")
    print(f"   Name: {user['first_name']} {user['last_name']}")
    print(f"   Phone: {user['phone_number']}")
    print(f"   Password hash: {user['password_hash'][:50]}...")
    
    # Test if "test" password works
    test_works = check_password_hash(user['password_hash'], "test")
    print(f"   'test' password works: {test_works}")
    
    # Test if "temp123" password works
    temp_works = check_password_hash(user['password_hash'], "temp123")
    print(f"   'temp123' password works: {temp_works}")
    
    return True


if __name__ == "__main__":
    success = check_ross_account()
    if success:
        print("\n✅ Ross account check completed")
    else:
        print("\n❌ Ross account check failed")
        sys.exit(1) 