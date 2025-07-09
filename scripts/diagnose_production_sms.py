#!/usr/bin/env python3
"""
Production SMS Diagnostic Script
===============================

Diagnose SMS/MMS issues in production environment.
Tests Twilio configuration and messaging service setup.
"""

import os
import sys
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import TwilioConfig


def test_twilio_config():
    """Test Twilio configuration"""
    print("🔍 TWILIO CONFIGURATION CHECK")
    print("=" * 50)
    
    print(f"ACCOUNT_SID: {TwilioConfig.ACCOUNT_SID[:10]}..." if TwilioConfig.ACCOUNT_SID else "❌ Not set")
    print(f"AUTH_TOKEN: {'✅ Set' if TwilioConfig.AUTH_TOKEN else '❌ Not set'}")
    print(f"MESSAGING_SERVICE_SID: {TwilioConfig.MESSAGING_SERVICE_SID[:10]}..." if TwilioConfig.MESSAGING_SERVICE_SID else "❌ Not set")
    print(f"SENDER_PHONE: {TwilioConfig.SENDER_PHONE}")
    
    config_status = TwilioConfig.validate_config()
    print(f"\nConfiguration valid: {'✅ Yes' if config_status['is_valid'] else '❌ No'}")
    if not config_status['is_valid']:
        print(f"Missing variables: {config_status['missing_vars']}")
    
    return config_status['is_valid']


def test_messaging_service():
    """Test if the messaging service is valid"""
    print("\n🔍 MESSAGING SERVICE CHECK")  
    print("=" * 50)
    
    if not TwilioConfig.ACCOUNT_SID or not TwilioConfig.AUTH_TOKEN:
        print("❌ Cannot test - missing account credentials")
        return False
    
    # Test the messaging service
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TwilioConfig.ACCOUNT_SID}/Messages/Services/{TwilioConfig.MESSAGING_SERVICE_SID}.json"
    auth = HTTPBasicAuth(TwilioConfig.ACCOUNT_SID, TwilioConfig.AUTH_TOKEN)
    
    try:
        response = requests.get(url, auth=auth, timeout=10)
        
        if response.status_code == 200:
            service_info = response.json()
            print(f"✅ Messaging service valid: {service_info.get('friendly_name', 'Unknown')}")
            print(f"   Status: {service_info.get('status', 'Unknown')}")
            print(f"   SID: {service_info.get('sid', 'Unknown')}")
            return True
        else:
            print(f"❌ Messaging service invalid: {response.status_code}")
            try:
                error_info = response.json()
                print(f"   Error: {error_info.get('message', 'Unknown error')}")
            except:
                print(f"   Raw response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing messaging service: {str(e)}")
        return False


def test_media_url():
    """Test if the media URL is accessible"""
    print("\n🔍 MEDIA URL CHECK")
    print("=" * 50)
    
    media_url = "https://www.lovetorally.com/static/images/rallylogo.png"
    print(f"Testing URL: {media_url}")
    
    try:
        response = requests.head(media_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Media URL accessible")
            print(f"   Content-Type: {response.headers.get('content-type', 'Unknown')}")
            print(f"   Content-Length: {response.headers.get('content-length', 'Unknown')}")
            return True
        else:
            print(f"❌ Media URL not accessible: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing media URL: {str(e)}")
        return False


def test_sms_send():
    """Test sending an SMS"""
    print("\n🔍 SMS SEND TEST")
    print("=" * 50)
    
    if not TwilioConfig.validate_config()['is_valid']:
        print("❌ Cannot test - invalid configuration")
        return False
    
    # Test phone number - use your number
    test_phone = "+17732138911"  # Ross's number
    
    print(f"Testing SMS send to {test_phone}")
    
    # Try SMS first
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TwilioConfig.ACCOUNT_SID}/Messages.json"
    auth = HTTPBasicAuth(TwilioConfig.ACCOUNT_SID, TwilioConfig.AUTH_TOKEN)
    
    sms_data = {
        "To": test_phone,
        "MessagingServiceSid": TwilioConfig.MESSAGING_SERVICE_SID,
        "Body": f"🧪 SMS Test from Rally Production - {datetime.now().strftime('%H:%M:%S')}"
    }
    
    try:
        print("Attempting SMS send...")
        response = requests.post(url, data=sms_data, auth=auth, timeout=30)
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ SMS sent successfully!")
            print(f"   Message SID: {result.get('sid')}")
            print(f"   Status: {result.get('status')}")
            return True
        else:
            print(f"❌ SMS failed: {response.status_code}")
            try:
                error_info = response.json()
                print(f"   Error: {error_info.get('message', 'Unknown error')}")
                print(f"   Error Code: {error_info.get('code', 'Unknown')}")
            except:
                print(f"   Raw response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending SMS: {str(e)}")
        return False


def test_mms_send():
    """Test sending an MMS"""
    print("\n🔍 MMS SEND TEST")
    print("=" * 50)
    
    if not TwilioConfig.validate_config()['is_valid']:
        print("❌ Cannot test - invalid configuration")
        return False
    
    test_phone = "+17732138911"  # Ross's number
    
    print(f"Testing MMS send to {test_phone}")
    
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TwilioConfig.ACCOUNT_SID}/Messages.json"
    auth = HTTPBasicAuth(TwilioConfig.ACCOUNT_SID, TwilioConfig.AUTH_TOKEN)
    
    mms_data = {
        "To": test_phone,
        "MessagingServiceSid": TwilioConfig.MESSAGING_SERVICE_SID,
        "Body": f"🧪 MMS Test from Rally Production - {datetime.now().strftime('%H:%M:%S')}",
        "MediaUrl": "https://www.lovetorally.com/static/images/rallylogo.png"
    }
    
    try:
        print("Attempting MMS send...")
        response = requests.post(url, data=mms_data, auth=auth, timeout=30)
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ MMS sent successfully!")
            print(f"   Message SID: {result.get('sid')}")
            print(f"   Status: {result.get('status')}")
            return True
        else:
            print(f"❌ MMS failed: {response.status_code}")
            try:
                error_info = response.json()
                print(f"   Error: {error_info.get('message', 'Unknown error')}")
                print(f"   Error Code: {error_info.get('code', 'Unknown')}")
            except:
                print(f"   Raw response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending MMS: {str(e)}")
        return False


def main():
    """Run all diagnostic tests"""
    print("🔧 PRODUCTION SMS DIAGNOSTIC")
    print(f"📅 {datetime.now()}")
    print("=" * 60)
    
    print("\n📝 Environment Information:")
    print(f"   Python: {sys.version}")
    print(f"   Platform: {sys.platform}")
    print(f"   Environment: {'Production' if os.getenv('RAILWAY_ENVIRONMENT') else 'Local'}")
    
    # Run all tests
    tests = [
        ("Configuration", test_twilio_config),
        ("Messaging Service", test_messaging_service),
        ("Media URL", test_media_url),
        ("SMS Send", test_sms_send),
        ("MMS Send", test_mms_send)
    ]
    
    results = {}
    for test_name, test_func in tests:
        results[test_name] = test_func()
    
    # Summary
    print("\n📊 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if not result:
            all_passed = False
    
    print(f"\nOverall Status: {'✅ All tests passed' if all_passed else '❌ Some tests failed'}")
    
    if not all_passed:
        print("\n🔧 TROUBLESHOOTING STEPS:")
        if not results.get("Configuration"):
            print("   1. Check environment variables in Railway")
        if not results.get("Messaging Service"):
            print("   2. Verify Twilio messaging service SID")
        if not results.get("Media URL"):
            print("   3. Check static file serving in production")
        if not results.get("SMS Send") or not results.get("MMS Send"):
            print("   4. Check Twilio account status and billing")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main()) 