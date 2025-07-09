#!/usr/bin/env python3
"""
Production SMS Diagnostic Script
===============================

This script helps diagnose and fix SMS issues in production by:
1. Testing Twilio configuration and credentials
2. Checking messaging service status
3. Testing actual SMS delivery
4. Providing recommendations for error code 21704

Usage:
    python scripts/diagnose_production_sms.py --test-number +17732138911
"""

import argparse
import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from requests.auth import HTTPBasicAuth
from config import TwilioConfig

def check_twilio_configuration() -> Dict:
    """Check Twilio configuration completeness"""
    print("🔍 CHECKING TWILIO CONFIGURATION")
    print("=" * 50)
    
    config_status = TwilioConfig.validate_config()
    
    print(f"✅ Account SID: {config_status['account_sid'][:8]}... (configured)")
    print(f"✅ Messaging Service: {config_status['messaging_service_sid'][:8]}... (configured)")
    print(f"✅ Sender Phone: {TwilioConfig.SENDER_PHONE}")
    
    if config_status['is_valid']:
        print(f"✅ Auth Token: {'*' * 20} (configured)")
        print("✅ All required environment variables are set")
        return {"status": "✅ CONFIGURED", "details": config_status}
    else:
        missing = config_status['missing_vars']
        for var in missing:
            print(f"❌ {var}: NOT SET")
        return {"status": "❌ MISSING VARIABLES", "details": config_status, "missing": missing}

def test_twilio_api_connectivity() -> Dict:
    """Test basic Twilio API connectivity"""
    print("\n🌐 TESTING TWILIO API CONNECTIVITY")
    print("=" * 50)
    
    if not TwilioConfig.is_configured():
        return {"status": "❌ SKIPPED", "reason": "Configuration incomplete"}
    
    try:
        # Test API with account details endpoint
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TwilioConfig.ACCOUNT_SID}.json"
        auth = HTTPBasicAuth(TwilioConfig.ACCOUNT_SID, TwilioConfig.AUTH_TOKEN)
        
        response = requests.get(url, auth=auth, timeout=10)
        
        if response.status_code == 200:
            account_data = response.json()
            print("✅ API connectivity successful")
            print(f"✅ Account status: {account_data.get('status', 'unknown')}")
            print(f"✅ Account type: {account_data.get('type', 'unknown')}")
            return {
                "status": "✅ CONNECTED",
                "account_status": account_data.get('status'),
                "account_type": account_data.get('type')
            }
        else:
            print(f"❌ API connectivity failed: HTTP {response.status_code}")
            print(f"❌ Error: {response.text}")
            return {"status": "❌ FAILED", "http_status": response.status_code, "error": response.text}
            
    except Exception as e:
        print(f"❌ API connectivity error: {e}")
        return {"status": "❌ ERROR", "error": str(e)}

def check_messaging_service_status() -> Dict:
    """Check the status of the messaging service"""
    print("\n📱 CHECKING MESSAGING SERVICE STATUS")
    print("=" * 50)
    
    if not TwilioConfig.is_configured():
        return {"status": "❌ SKIPPED", "reason": "Configuration incomplete"}
    
    try:
        # Get messaging service details
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TwilioConfig.ACCOUNT_SID}/Messaging/Services/{TwilioConfig.MESSAGING_SERVICE_SID}.json"
        auth = HTTPBasicAuth(TwilioConfig.ACCOUNT_SID, TwilioConfig.AUTH_TOKEN)
        
        response = requests.get(url, auth=auth, timeout=10)
        
        if response.status_code == 200:
            service_data = response.json()
            print(f"✅ Messaging service found: {service_data.get('friendly_name', 'Unknown')}")
            print(f"✅ Service status: Active")
            
            # Check phone numbers in the service
            numbers_url = f"{url}/PhoneNumbers"
            numbers_response = requests.get(numbers_url, auth=auth, timeout=10)
            
            if numbers_response.status_code == 200:
                numbers_data = numbers_response.json()
                phone_numbers = numbers_data.get('phone_numbers', [])
                print(f"✅ Phone numbers in service: {len(phone_numbers)}")
                for number in phone_numbers:
                    print(f"   📞 {number.get('phone_number', 'Unknown')}")
                
                if len(phone_numbers) == 0:
                    print("⚠️  WARNING: No phone numbers in messaging service")
                    print("   This could cause error 21703/21704")
                
                return {
                    "status": "✅ ACTIVE",
                    "service_name": service_data.get('friendly_name'),
                    "phone_count": len(phone_numbers),
                    "phone_numbers": [n.get('phone_number') for n in phone_numbers]
                }
            else:
                print(f"⚠️  Could not check phone numbers: HTTP {numbers_response.status_code}")
                return {"status": "✅ ACTIVE", "warning": "Could not verify phone numbers"}
        else:
            print(f"❌ Messaging service check failed: HTTP {response.status_code}")
            print(f"❌ Error: {response.text}")
            return {"status": "❌ FAILED", "http_status": response.status_code, "error": response.text}
            
    except Exception as e:
        print(f"❌ Messaging service check error: {e}")
        return {"status": "❌ ERROR", "error": str(e)}

def send_test_sms(test_number: str) -> Dict:
    """Send a test SMS to verify functionality"""
    print(f"\n📤 SENDING TEST SMS TO {test_number}")
    print("=" * 50)
    
    if not TwilioConfig.is_configured():
        return {"status": "❌ SKIPPED", "reason": "Configuration incomplete"}
    
    try:
        from app.services.notifications_service import send_sms_notification
        
        test_message = f"🧪 Rally SMS Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        print(f"📝 Message: {test_message}")
        print("⏳ Sending...")
        
        result = send_sms_notification(test_number, test_message, test_mode=False)
        
        if result["success"]:
            print("✅ Test SMS sent successfully!")
            print(f"✅ Message SID: {result.get('message_sid')}")
            print(f"✅ Status: {result.get('twilio_status', 'unknown')}")
            return {"status": "✅ SENT", "message_sid": result.get('message_sid'), "result": result}
        else:
            print("❌ Test SMS failed!")
            print(f"❌ Error: {result.get('error')}")
            print(f"❌ Error code: {result.get('error_code')}")
            return {"status": "❌ FAILED", "error": result.get('error'), "error_code": result.get('error_code')}
            
    except Exception as e:
        print(f"❌ Test SMS error: {e}")
        return {"status": "❌ ERROR", "error": str(e)}

def check_recent_message_status(hours_back: int = 24) -> Dict:
    """Check status of recent messages to understand patterns"""
    print(f"\n📊 CHECKING RECENT MESSAGES (last {hours_back} hours)")
    print("=" * 50)
    
    if not TwilioConfig.is_configured():
        return {"status": "❌ SKIPPED", "reason": "Configuration incomplete"}
    
    try:
        # Calculate date filter
        start_date = datetime.utcnow() - timedelta(hours=hours_back)
        date_filter = start_date.strftime('%Y-%m-%d')
        
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TwilioConfig.ACCOUNT_SID}/Messages.json"
        auth = HTTPBasicAuth(TwilioConfig.ACCOUNT_SID, TwilioConfig.AUTH_TOKEN)
        
        params = {
            "DateSent>": date_filter,
            "PageSize": 50
        }
        
        response = requests.get(url, auth=auth, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            messages = data.get('messages', [])
            
            # Analyze message statuses
            status_counts = {}
            error_codes = {}
            total_messages = len(messages)
            
            for msg in messages:
                status = msg.get('status', 'unknown')
                error_code = msg.get('error_code')
                
                status_counts[status] = status_counts.get(status, 0) + 1
                
                if error_code:
                    error_codes[error_code] = error_codes.get(error_code, 0) + 1
            
            print(f"📈 Total messages found: {total_messages}")
            print("\n📊 Status breakdown:")
            for status, count in status_counts.items():
                percentage = (count / total_messages * 100) if total_messages > 0 else 0
                print(f"   {status}: {count} ({percentage:.1f}%)")
            
            if error_codes:
                print("\n⚠️  Error codes found:")
                for code, count in error_codes.items():
                    print(f"   {code}: {count} occurrences")
            else:
                print("\n✅ No error codes found")
            
            return {
                "status": "✅ ANALYZED",
                "total_messages": total_messages,
                "status_counts": status_counts,
                "error_codes": error_codes
            }
        else:
            print(f"❌ Recent messages check failed: HTTP {response.status_code}")
            return {"status": "❌ FAILED", "http_status": response.status_code}
            
    except Exception as e:
        print(f"❌ Recent messages check error: {e}")
        return {"status": "❌ ERROR", "error": str(e)}

def provide_error_21704_recommendations():
    """Provide specific recommendations for error 21704"""
    print("\n💡 ERROR 21704 RECOMMENDATIONS")
    print("=" * 50)
    print("Error 21704: 'Provider experiencing disruptions/timeouts'")
    print()
    print("🔧 IMMEDIATE SOLUTIONS:")
    print("1. ⏰ Wait and retry - this is usually a temporary Twilio infrastructure issue")
    print("2. 🔄 Implement exponential backoff in SMS sending")
    print("3. 📱 Add backup SMS provider (like MessageBird) for critical messages")
    print()
    print("🛡️  LONG-TERM SOLUTIONS:")
    print("1. 📊 Monitor Twilio status page: https://status.twilio.com")
    print("2. 🚨 Set up Twilio webhook for delivery status notifications")
    print("3. 📝 Log all SMS attempts with retry logic")
    print("4. 🎯 Use multiple messaging services for redundancy")
    print()
    print("📈 IF PROBLEM PERSISTS:")
    print("1. 📞 Contact Twilio Support with specific message SIDs")
    print("2. 🔍 Check your account for compliance issues")
    print("3. 🏗️  Verify messaging service has active phone numbers")

def main():
    parser = argparse.ArgumentParser(description='Diagnose production SMS issues')
    parser.add_argument('--test-number', default='+17732138911', 
                       help='Phone number to send test SMS to')
    parser.add_argument('--hours-back', type=int, default=24,
                       help='Hours back to check recent messages')
    parser.add_argument('--skip-test-sms', action='store_true',
                       help='Skip sending actual test SMS')
    
    args = parser.parse_args()
    
    print("🩺 RALLY PRODUCTION SMS DIAGNOSTIC")
    print("=" * 60)
    print(f"⏰ Timestamp: {datetime.now().isoformat()}")
    print(f"🎯 Test number: {args.test_number}")
    print()
    
    # Run all diagnostic checks
    results = {}
    
    results['config'] = check_twilio_configuration()
    results['api'] = test_twilio_api_connectivity()
    results['messaging_service'] = check_messaging_service_status()
    results['recent_messages'] = check_recent_message_status(args.hours_back)
    
    if not args.skip_test_sms:
        results['test_sms'] = send_test_sms(args.test_number)
    
    # Provide recommendations
    provide_error_21704_recommendations()
    
    # Summary
    print("\n📋 DIAGNOSTIC SUMMARY")
    print("=" * 50)
    
    all_passing = True
    for check, result in results.items():
        status = result.get('status', '❓ UNKNOWN')
        print(f"{check.upper()}: {status}")
        if '❌' in status:
            all_passing = False
    
    if all_passing:
        print("\n🎉 All checks passed! The SMS system appears to be properly configured.")
        print("   Error 21704 is likely a temporary Twilio infrastructure issue.")
        print("   Monitor and retry failed messages.")
    else:
        print("\n⚠️  Issues detected. Review the diagnostic output above.")
        print("   Fix configuration issues before addressing 21704 errors.")
    
    # Save results to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f"logs/sms_diagnostic_{timestamp}.json"
    os.makedirs('logs', exist_ok=True)
    
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'test_number': args.test_number,
            'results': results
        }, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: {results_file}")

if __name__ == "__main__":
    main() 