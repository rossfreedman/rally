#!/usr/bin/env python3
"""
Fix Twilio Messaging Service Configuration
==========================================

This script helps identify and fix the messaging service SID configuration
issue that's causing 404 errors in production diagnostics.

Usage:
    python scripts/fix_twilio_messaging_service.py
"""

import os
import sys
import requests
from requests.auth import HTTPBasicAuth

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import TwilioConfig

def check_messaging_services():
    """Check all messaging services in the Twilio account"""
    print("🔍 CHECKING ALL MESSAGING SERVICES")
    print("=" * 50)
    
    if not TwilioConfig.is_configured():
        print("❌ Twilio not configured")
        return
    
    try:
        # List all messaging services
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TwilioConfig.ACCOUNT_SID}/Messaging/Services.json"
        auth = HTTPBasicAuth(TwilioConfig.ACCOUNT_SID, TwilioConfig.AUTH_TOKEN)
        
        response = requests.get(url, auth=auth, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            services = data.get('messaging_services', [])
            
            print(f"📱 Found {len(services)} messaging services:")
            print()
            
            for i, service in enumerate(services, 1):
                print(f"Service {i}:")
                print(f"  📋 Name: {service.get('friendly_name', 'Unknown')}")
                print(f"  🆔 SID: {service.get('sid', 'Unknown')}")
                print(f"  📅 Created: {service.get('date_created', 'Unknown')}")
                print(f"  🔄 Status: Active")
                print()
                
                # Check phone numbers for this service
                check_service_phone_numbers(service.get('sid'))
            
            print(f"🔧 CURRENT CONFIGURATION:")
            print(f"  Config Default: {TwilioConfig.MESSAGING_SERVICE_SID}")
            print(f"  Environment: {os.getenv('TWILIO_MESSAGING_SERVICE_SID', 'Not Set')}")
            print()
            
            # Provide recommendations
            if services:
                recommended_sid = services[0].get('sid')
                print(f"💡 RECOMMENDATION:")
                print(f"  Use messaging service: {recommended_sid}")
                print(f"  Name: {services[0].get('friendly_name', 'Unknown')}")
                print()
                print(f"🔧 TO FIX:")
                print(f"  1. Update Railway environment variable:")
                print(f"     TWILIO_MESSAGING_SERVICE_SID={recommended_sid}")
                print(f"  2. Or update config.py default to:")
                print(f"     MESSAGING_SERVICE_SID = os.getenv('TWILIO_MESSAGING_SERVICE_SID', '{recommended_sid}')")
            
        else:
            print(f"❌ Failed to list messaging services: HTTP {response.status_code}")
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error checking messaging services: {e}")

def check_service_phone_numbers(service_sid):
    """Check phone numbers for a specific messaging service"""
    if not service_sid:
        return
        
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TwilioConfig.ACCOUNT_SID}/Messaging/Services/{service_sid}/PhoneNumbers.json"
        auth = HTTPBasicAuth(TwilioConfig.ACCOUNT_SID, TwilioConfig.AUTH_TOKEN)
        
        response = requests.get(url, auth=auth, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            phone_numbers = data.get('phone_numbers', [])
            print(f"  📞 Phone numbers: {len(phone_numbers)}")
            for phone in phone_numbers:
                print(f"    - {phone.get('phone_number', 'Unknown')}")
        else:
            print(f"  ⚠️  Could not check phone numbers (HTTP {response.status_code})")
            
    except Exception as e:
        print(f"  ❌ Error checking phone numbers: {e}")

def test_service_sid(service_sid):
    """Test if a specific messaging service SID works"""
    print(f"\n🧪 TESTING SERVICE SID: {service_sid}")
    print("=" * 50)
    
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TwilioConfig.ACCOUNT_SID}/Messaging/Services/{service_sid}.json"
        auth = HTTPBasicAuth(TwilioConfig.ACCOUNT_SID, TwilioConfig.AUTH_TOKEN)
        
        response = requests.get(url, auth=auth, timeout=10)
        
        if response.status_code == 200:
            service_data = response.json()
            print(f"✅ Service found: {service_data.get('friendly_name', 'Unknown')}")
            print(f"✅ SID: {service_data.get('sid')}")
            return True
        else:
            print(f"❌ Service not found: HTTP {response.status_code}")
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing service: {e}")
        return False

def main():
    print("🔧 TWILIO MESSAGING SERVICE CONFIGURATION FIX")
    print("=" * 60)
    
    # Check current configuration
    print(f"📋 Current Configuration:")
    print(f"  Account SID: {TwilioConfig.ACCOUNT_SID[:8]}...")
    print(f"  Config Default: {TwilioConfig.MESSAGING_SERVICE_SID}")
    print(f"  Environment Variable: {os.getenv('TWILIO_MESSAGING_SERVICE_SID', 'Not Set')}")
    print()
    
    # Test current messaging service
    current_sid = TwilioConfig.MESSAGING_SERVICE_SID
    print(f"🧪 Testing current messaging service: {current_sid}")
    if test_service_sid(current_sid):
        print("✅ Current messaging service is valid")
    else:
        print("❌ Current messaging service has issues")
    print()
    
    # Check all available services
    check_messaging_services()

if __name__ == "__main__":
    main() 