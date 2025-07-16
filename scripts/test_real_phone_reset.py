#!/usr/bin/env python3
"""
Test password reset with real phone number
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.password_reset_service import send_password_via_sms


def test_real_phone_reset():
    """Test password reset with a real phone number"""
    
    print("🧪 Testing password reset with real phone number...")
    
    # Use a real phone number for testing
    real_phone = "7732138911"  # This should be a real number for testing
    
    print(f"Testing with phone: {real_phone}")
    
    try:
        result = send_password_via_sms(real_phone)
        
        print(f"Result: {result}")
        
        if result['success']:
            print("✅ Password reset test successful!")
            print("📱 Check your phone for the SMS message")
            return True
        else:
            print(f"❌ Password reset failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during password reset test: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_real_phone_reset()
    if success:
        print("\n✅ Password reset test completed successfully")
    else:
        print("\n❌ Password reset test failed")
        sys.exit(1) 