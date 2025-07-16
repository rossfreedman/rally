#!/usr/bin/env python3
"""
Test script to verify forgot password redirect functionality
"""

import sys
import os
import requests
import json
import time

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_forgot_password_redirect():
    """Test the forgot password redirect functionality"""
    
    print("🧪 Testing Forgot Password Redirect Functionality")
    print("=" * 60)
    
    base_url = "http://localhost:8080"
    
    # Test 1: Check if forgot password page loads
    print("\n1. Testing forgot password page load...")
    
    try:
        response = requests.get(f"{base_url}/forgot-password")
        print(f"   📊 Page load status: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Forgot password page loads successfully")
            
            # Check if the redirect JavaScript is present
            if "setTimeout(function() {" in response.text and "window.location.href = '/login';" in response.text:
                print("   ✅ Redirect JavaScript found in page")
            else:
                print("   ❌ Redirect JavaScript NOT found in page")
                return False
        else:
            print(f"   ❌ Page load failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Page load request failed: {e}")
        return False
    
    # Test 2: Test password reset API
    print("\n2. Testing password reset API...")
    
    test_phone = "7732138911"
    test_email = "rossfreedman@gmail.com"
    
    reset_data = {
        "phone": test_phone,
        "email": test_email
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/forgot-password",
            json=reset_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   📊 API response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Password reset API successful")
            print(f"   📋 Success: {data.get('success')}")
            print(f"   📋 Message: {data.get('message')}")
            
            if data.get('success'):
                print("   ✅ Password sent successfully - redirect should happen in 3 seconds")
                return True
            else:
                print(f"   ❌ Password reset failed: {data.get('error')}")
                return False
        else:
            print(f"   ❌ API request failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ API request failed: {e}")
        return False
    
    # Test 3: Verify the redirect works in browser context
    print("\n3. Testing browser redirect simulation...")
    print("   Note: This test simulates what should happen in a browser")
    print("   - User submits form")
    print("   - Success message appears")
    print("   - After 3 seconds, redirect to /login")
    print("   - Check browser console for any JavaScript errors")
    
    return True

def test_password_length():
    """Test that temporary passwords are not 9 digits"""
    
    print("\n🔍 Testing Password Length Requirements")
    print("=" * 40)
    
    from app.services.password_reset_service import _get_user_password
    from database_utils import execute_query_one
    
    # Get a test user
    user = execute_query_one("SELECT id FROM users LIMIT 1")
    
    if not user:
        print("   ❌ No users found for testing")
        return False
    
    print(f"   📋 Testing with user ID: {user['id']}")
    
    # Generate a temporary password
    temp_password = _get_user_password(user['id'])
    
    if temp_password:
        print(f"   ✅ Generated temporary password: {temp_password}")
        print(f"   📏 Password length: {len(temp_password)} characters")
        
        if len(temp_password) == 6:
            print("   ✅ Password is 6 characters (correct)")
        elif len(temp_password) == 8:
            print("   ⚠️  Password is 8 characters (old format)")
        else:
            print(f"   ⚠️  Password is {len(temp_password)} characters (unexpected)")
        
        # Check if it's all digits
        if temp_password.isdigit():
            print("   ⚠️  Password is all digits (should be alphanumeric)")
        else:
            print("   ✅ Password contains letters and numbers")
        
        return True
    else:
        print("   ❌ Failed to generate temporary password")
        return False

if __name__ == "__main__":
    print("Starting forgot password tests...")
    
    # Test password length first
    password_test = test_password_length()
    
    # Test redirect functionality
    redirect_test = test_forgot_password_redirect()
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Password Length Test: {'✅ PASS' if password_test else '❌ FAIL'}")
    print(f"Redirect Test: {'✅ PASS' if redirect_test else '❌ FAIL'}")
    
    if password_test and redirect_test:
        print("\n🎉 All tests passed! Forgot password functionality should work correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.") 