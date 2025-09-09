#!/usr/bin/env python3
"""
SMS Diagnostic Tool
===================

Helps diagnose SMS delivery issues by testing different phone number formats
and providing detailed Twilio response information.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.notifications_service import send_sms_notification, validate_phone_number
from config import TwilioConfig

def test_phone_number(phone, description=""):
    """Test SMS delivery to a specific phone number"""
    print(f"\n{'='*50}")
    print(f"Testing {description}: {phone}")
    print(f"{'='*50}")
    
    # Step 1: Validate phone number
    is_valid, validation_result = validate_phone_number(phone)
    print(f"1. Phone Validation:")
    print(f"   Input: {phone}")
    print(f"   Valid: {is_valid}")
    print(f"   Result: {validation_result}")
    
    if not is_valid:
        print(f"   ❌ FAILED: {validation_result}")
        return False
    
    # Step 2: Send test SMS
    test_message = f"SMS Test to {phone} - If you receive this, SMS is working!"
    print(f"\n2. Sending SMS:")
    print(f"   Message: {test_message}")
    
    result = send_sms_notification(phone, test_message)
    
    print(f"   Success: {result.get('success')}")
    print(f"   Message SID: {result.get('message_sid')}")
    print(f"   Status Code: {result.get('status_code')}")
    print(f"   Twilio Status: {result.get('twilio_status')}")
    
    if result.get('success'):
        print(f"   ✅ SMS sent successfully!")
        print(f"   📱 Check your phone for the message")
    else:
        print(f"   ❌ SMS failed: {result.get('error')}")
    
    return result.get('success')

def main():
    """Main diagnostic function"""
    print("🔍 Rally SMS Diagnostic Tool")
    print("============================")
    
    # Check Twilio configuration
    config = TwilioConfig.validate_config()
    print(f"Twilio Config Valid: {config['is_valid']}")
    if config['missing_vars']:
        print(f"Missing vars: {config['missing_vars']}")
        return
    
    # Test different phone number formats
    test_numbers = [
        ("+17732138911", "Ross's working number"),
        ("+17732139811", "Amy's number (current)"),
        ("7732139811", "Amy's number (no +1)"),
        ("(773) 213-9811", "Amy's number (formatted)"),
    ]
    
    print(f"\nTesting {len(test_numbers)} phone number formats...")
    
    success_count = 0
    for phone, description in test_numbers:
        if test_phone_number(phone, description):
            success_count += 1
    
    print(f"\n{'='*50}")
    print(f"RESULTS: {success_count}/{len(test_numbers)} tests successful")
    print(f"{'='*50}")
    
    if success_count == 0:
        print("❌ No SMS messages were sent successfully")
        print("Check Twilio configuration and phone numbers")
    elif success_count < len(test_numbers):
        print("⚠️  Some SMS messages failed")
        print("Check the failed phone number formats")
    else:
        print("✅ All SMS messages sent successfully!")

if __name__ == "__main__":
    main()
