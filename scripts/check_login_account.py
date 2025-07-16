#!/usr/bin/env python3
"""
Check what account is being used for login and verify password hash
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query_one, execute_query
from werkzeug.security import check_password_hash


def check_login_account():
    """Check what account is being used for login"""
    
    print("🔍 Checking login account and password verification...")
    
    # Check all users with phone number 7732138911
    phone = "7732138911"
    
    print(f"\n1. Looking up all users with phone: {phone}")
    users_query = """
        SELECT id, email, first_name, last_name, password_hash, phone_number
        FROM users 
        WHERE phone_number = %s
    """
    
    users = execute_query(users_query, [phone])
    
    if not users:
        print("❌ No users found with this phone number")
        return False
    
    print(f"✅ Found {len(users)} user(s) with this phone number:")
    for user in users:
        print(f"   - ID: {user['id']}, Email: {user['email']}, Name: {user['first_name']} {user['last_name']}")
        print(f"     Password hash: {user['password_hash'][:50]}...")
        
        # Test if "test" password works with this hash
        test_works = check_password_hash(user['password_hash'], "test")
        print(f"     'test' password works: {test_works}")
        
        # Test if "temp123" password works (from our debug script)
        temp_works = check_password_hash(user['password_hash'], "temp123")
        print(f"     'temp123' password works: {temp_works}")
    
    # Also check if there are any users with "test" as their password
    print(f"\n2. Looking for users with 'test' password...")
    test_password_query = """
        SELECT id, email, first_name, last_name, password_hash
        FROM users 
        WHERE password_hash = 'test' OR password_hash = 'test123'
    """
    
    test_users = execute_query(test_password_query)
    if test_users:
        print(f"⚠️ Found {len(test_users)} user(s) with 'test' password:")
        for user in test_users:
            print(f"   - ID: {user['id']}, Email: {user['email']}, Name: {user['first_name']} {user['last_name']}")
    else:
        print("✅ No users found with 'test' password")
    
    # Check what email you're actually logging in with
    print(f"\n3. Common test emails to check:")
    test_emails = [
        "rossfreedman@gmail.com",
        "brian.benavides@gmail.com", 
        "test@example.com",
        "admin@rally.com"
    ]
    
    for email in test_emails:
        email_user_query = """
            SELECT id, email, first_name, last_name, password_hash
            FROM users 
            WHERE email = %s
        """
        
        email_user = execute_query_one(email_user_query, [email])
        if email_user:
            print(f"   - {email}: Found user {email_user['first_name']} {email_user['last_name']}")
            test_works = check_password_hash(email_user['password_hash'], "test")
            print(f"     'test' password works: {test_works}")
        else:
            print(f"   - {email}: Not found")
    
    return True


if __name__ == "__main__":
    success = check_login_account()
    if success:
        print("\n✅ Login account check completed")
    else:
        print("\n❌ Login account check failed")
        sys.exit(1) 