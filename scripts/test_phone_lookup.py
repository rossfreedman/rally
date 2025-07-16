#!/usr/bin/env python3
"""
Test the improved phone number lookup
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.password_reset_service import _find_user_by_phone


def test_phone_lookup():
    """Test the improved phone number lookup"""
    
    print("🧪 Testing improved phone number lookup...")
    
    # Test different phone number formats
    test_phones = [
        "7732138911",      # Plain format
        "+17732138911",    # With +1
        "+7732138911",     # With + but no 1
        "17732138911",     # With 1 but no +
        "(773) 213-8911",  # Formatted
        "773-213-8911",    # Dashed
        "773 213 8911",    # Spaced
    ]
    
    for phone in test_phones:
        print(f"\nTesting phone: {phone}")
        user = _find_user_by_phone(phone)
        
        if user:
            print(f"✅ Found user: {user['first_name']} {user['last_name']} ({user['email']})")
            print(f"   Stored phone: {user['phone_number']}")
        else:
            print(f"❌ No user found")
    
    return True


if __name__ == "__main__":
    success = test_phone_lookup()
    if success:
        print("\n✅ Phone lookup test completed")
    else:
        print("\n❌ Phone lookup test failed")
        sys.exit(1) 