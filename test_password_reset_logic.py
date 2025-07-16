#!/usr/bin/env python3
"""
Test script for password reset logic
"""

from app.services.password_reset_service import send_password_via_sms

def test_password_reset_logic():
    """Test the password reset logic with different scenarios"""
    
    print("Testing password reset logic...")
    
    # Test 1: Single user with phone number (should work without email)
    print("\n1. Testing single user scenario...")
    result1 = send_password_via_sms("7732138911")  # Ross's phone
    print(f"   Result: {result1}")
    
    # Test 2: Multiple users scenario with email (should work)
    print("\n2. Testing multiple users scenario with email...")
    result2 = send_password_via_sms("7732138911", "rossfreedman@gmail.com")  # Ross's email
    print(f"   Result: {result2}")
    
    # Test 3: Multiple users scenario with wrong email (should fail)
    print("\n3. Testing multiple users scenario with wrong email...")
    result3 = send_password_via_sms("7732138911", "wrong@email.com")
    print(f"   Result: {result3}")
    
    # Test 4: Non-existent phone number
    print("\n4. Testing non-existent phone...")
    result4 = send_password_via_sms("9999999999")
    print(f"   Result: {result4}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_password_reset_logic() 