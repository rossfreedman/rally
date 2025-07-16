#!/usr/bin/env python3
"""
Test phone lookup with Ross's exact phone number
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.password_reset_service import _find_user_by_phone


def test_ross_phone_lookup():
    """Test phone lookup with Ross's exact phone number"""
    
    print("🧪 Testing phone lookup with Ross's phone number...")
    
    # Ross's exact phone number from database
    ross_phone = "+17732138911"
    
    print(f"Testing Ross's phone: {ross_phone}")
    user = _find_user_by_phone(ross_phone)
    
    if user:
        print(f"✅ Found user: {user['first_name']} {user['last_name']} ({user['email']})")
        print(f"   Stored phone: {user['phone_number']}")
        
        if user['email'] == "rossfreedman@gmail.com":
            print("✅ SUCCESS: Found Ross Freedman!")
        else:
            print("❌ ERROR: Found wrong user!")
    else:
        print("❌ No user found")
    
    # Also test without +1
    print(f"\nTesting without +1: 7732138911")
    user2 = _find_user_by_phone("7732138911")
    
    if user2:
        print(f"✅ Found user: {user2['first_name']} {user2['last_name']} ({user2['email']})")
        print(f"   Stored phone: {user2['phone_number']}")
        
        if user2['email'] == "rossfreedman@gmail.com":
            print("✅ SUCCESS: Found Ross Freedman!")
        else:
            print("❌ ERROR: Found wrong user!")
    else:
        print("❌ No user found")
    
    return True


if __name__ == "__main__":
    success = test_ross_phone_lookup()
    if success:
        print("\n✅ Ross phone lookup test completed")
    else:
        print("\n❌ Ross phone lookup test failed")
        sys.exit(1) 