#!/usr/bin/env python3
"""
Force a staging notification test by directly calling the logging function.
This bypasses all authentication and database checks to test pure email sending.
"""

import os
import sys
from datetime import datetime

# Set environment to use staging database URL if provided
if len(sys.argv) > 1 and sys.argv[1] == '--staging':
    # This would use staging DATABASE_URL if you set it
    os.environ['USE_STAGING'] = 'true'

# Add the parent directory to the path so we can import from the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SendGridConfig
from app.services.notifications_service import send_admin_activity_notification

def force_notification_test():
    """Force send a notification to test email delivery"""
    print("🚀 FORCE STAGING NOTIFICATION TEST")
    print("=" * 60)
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print(f"\n📧 Attempting to send email to: {SendGridConfig.ADMIN_EMAIL}")
    print(f"📤 From: {SendGridConfig.FROM_EMAIL}")
    print(f"🔑 API Key: {SendGridConfig.API_KEY[:15]}..." if SendGridConfig.API_KEY else "❌ NO API KEY")
    
    try:
        result = send_admin_activity_notification(
            user_email="staging-test@example.com",
            first_name="Staging Test",
            last_name="User", 
            activity_type="STAGING_FORCE_TEST",
            page="/test/force-staging",
            details=f"Forced staging notification test at {datetime.now().isoformat()}"
        )
        
        if result.get('success'):
            print(f"\n✅ EMAIL SENT SUCCESSFULLY!")
            print(f"📧 Message ID: {result.get('message_id', 'N/A')}")
            print(f"🎯 Sent to: {SendGridConfig.ADMIN_EMAIL}")
            
            print(f"\n⏰ CHECK YOUR EMAIL NOW:")
            print(f"   • Subject: Rally User Activity Alert")
            print(f"   • From: {SendGridConfig.FROM_EMAIL}")
            print(f"   • To: {SendGridConfig.ADMIN_EMAIL}")
            print(f"   • Should arrive within 1-2 minutes")
            
            return True
        else:
            print(f"\n❌ EMAIL FAILED TO SEND")
            print(f"Error: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"\n❌ EXCEPTION OCCURRED: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return False

def main():
    """Main test function"""
    success = force_notification_test()
    
    if success:
        print(f"\n🎉 If this email works but real user activity doesn't,")
        print(f"   the issue is in the activity logging flow, not email sending.")
    else:
        print(f"\n🔧 Email sending is broken - need to fix SendGrid configuration.")

if __name__ == "__main__":
    main()
