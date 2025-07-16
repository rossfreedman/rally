#!/usr/bin/env python3
"""
Test password reset functionality
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query_one, execute_query
from app.services.password_reset_service import send_password_via_sms


def test_password_reset():
    """Test the password reset functionality"""
    
    print("🧪 Testing password reset functionality...")
    
    # Test 1: Check if any users have phone numbers
    print("\n1. Checking users with phone numbers...")
    users_with_phones_query = """
        SELECT id, email, first_name, last_name, phone_number
        FROM users 
        WHERE phone_number IS NOT NULL 
        AND phone_number != ''
        LIMIT 5
    """
    
    users_with_phones = execute_query(users_with_phones_query)
    
    if users_with_phones:
        print(f"✅ Found {len(users_with_phones)} users with phone numbers:")
        for user in users_with_phones:
            print(f"   - {user['first_name']} {user['last_name']}: {user['phone_number']}")
    else:
        print("❌ No users found with phone numbers")
        return False
    
    # Test 2: Try password reset with first user's phone number
    test_phone = users_with_phones[0]['phone_number']
    print(f"\n2. Testing password reset for phone: {test_phone}")
    
    try:
        result = send_password_via_sms(test_phone)
        
        print(f"Result: {result}")
        
        if result['success']:
            print("✅ Password reset test successful!")
            return True
        else:
            print(f"❌ Password reset failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during password reset test: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_password_reset()
    if success:
        print("\n✅ Password reset test completed successfully")
    else:
        print("\n❌ Password reset test failed")
        sys.exit(1) 