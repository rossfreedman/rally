#!/usr/bin/env python3
"""
Check all users with this phone number
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query


def check_all_phone_users():
    """Check all users with this phone number"""
    
    print("🔍 Checking all users with phone number variations...")
    
    # Check all users with any variation of this phone number
    phone_query = """
        SELECT id, email, first_name, last_name, phone_number
        FROM users 
        WHERE phone_number LIKE '%7732138911%'
           OR phone_number LIKE '%+17732138911%'
           OR phone_number LIKE '%+7732138911%'
           OR phone_number LIKE '%17732138911%'
        ORDER BY id
    """
    
    users = execute_query(phone_query)
    
    if not users:
        print("❌ No users found with this phone number")
        return False
    
    print(f"✅ Found {len(users)} user(s) with this phone number:")
    for user in users:
        print(f"   - ID: {user['id']}, Email: {user['email']}, Name: {user['first_name']} {user['last_name']}")
        print(f"     Phone: {user['phone_number']}")
    
    # Also check with normalized phone number
    print(f"\n🔍 Checking with normalized phone number...")
    normalized_query = """
        SELECT id, email, first_name, last_name, phone_number
        FROM users 
        WHERE REPLACE(REPLACE(REPLACE(phone_number, '+', ''), '-', ''), ' ', '') LIKE '%7732138911%'
        ORDER BY id
    """
    
    normalized_users = execute_query(normalized_query)
    
    if normalized_users:
        print(f"✅ Found {len(normalized_users)} user(s) with normalized phone number:")
        for user in normalized_users:
            print(f"   - ID: {user['id']}, Email: {user['email']}, Name: {user['first_name']} {user['last_name']}")
            print(f"     Phone: {user['phone_number']}")
    else:
        print("❌ No users found with normalized phone number")
    
    return True


if __name__ == "__main__":
    success = check_all_phone_users()
    if success:
        print("\n✅ Phone user check completed")
    else:
        print("\n❌ Phone user check failed")
        sys.exit(1) 