#!/usr/bin/env python3
"""
Trace the complete activity logging flow to identify where it's failing.
"""

import os
import sys
from datetime import datetime

# Add the parent directory to the path so we can import from the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SendGridConfig
from app.services.admin_service import get_detailed_logging_notifications_setting
from app.services.notifications_service import send_admin_activity_notification
from utils.logging import log_user_activity, _send_detailed_logging_notification

def test_complete_activity_flow():
    """Test the complete activity logging flow step by step"""
    print("🔍 TRACING COMPLETE ACTIVITY LOGGING FLOW")
    print("=" * 60)
    
    # Step 1: Check SendGrid Config
    print("\n1️⃣ CHECKING SENDGRID CONFIGURATION")
    print("-" * 40)
    
    if not SendGridConfig.is_configured():
        print("❌ SendGrid not configured")
        return False
    
    print(f"✅ SendGrid configured")
    print(f"📧 Admin email: {SendGridConfig.ADMIN_EMAIL}")
    print(f"🔑 API key: {SendGridConfig.API_KEY[:15]}...")
    
    # Step 2: Check detailed logging setting
    print("\n2️⃣ CHECKING DETAILED LOGGING DATABASE SETTING")
    print("-" * 40)
    
    try:
        setting = get_detailed_logging_notifications_setting()
        print(f"📊 Database setting result: {setting}")
        
        if setting.get('success') and setting.get('enabled'):
            print("✅ Detailed logging ENABLED in database")
        else:
            print("❌ Detailed logging DISABLED in database")
            print(f"   Setting details: {setting}")
            return False
    except Exception as e:
        print(f"❌ Error checking detailed logging setting: {e}")
        return False
    
    # Step 3: Test the notification sending function directly
    print("\n3️⃣ TESTING EMAIL NOTIFICATION FUNCTION")
    print("-" * 40)
    
    try:
        result = send_admin_activity_notification(
            user_email="test@example.com",
            user_name="Test User",
            activity_type="FLOW_TEST",
            page_url="/test/flow",
            additional_info="Testing complete activity logging flow"
        )
        
        if result.get('success'):
            print("✅ Email notification function works")
            print(f"📧 Message ID: {result.get('message_id', 'N/A')}")
        else:
            print(f"❌ Email notification failed: {result.get('error')}")
            return False
    except Exception as e:
        print(f"❌ Error in email notification function: {e}")
        import traceback
        print(traceback.format_exc())
        return False
    
    # Step 4: Test the detailed logging notification wrapper
    print("\n4️⃣ TESTING DETAILED LOGGING NOTIFICATION WRAPPER")
    print("-" * 40)
    
    try:
        result = _send_detailed_logging_notification(
            user_email="test@example.com",
            user_name="Test User", 
            activity_type="WRAPPER_TEST",
            page_url="/test/wrapper",
            additional_info="Testing detailed logging wrapper function"
        )
        
        print(f"📨 Wrapper function result: {result}")
        
        if result:
            print("✅ Detailed logging wrapper works")
        else:
            print("❌ Detailed logging wrapper failed")
            return False
    except Exception as e:
        print(f"❌ Error in detailed logging wrapper: {e}")
        import traceback
        print(traceback.format_exc())
        return False
    
    # Step 5: Test the complete log_user_activity function
    print("\n5️⃣ TESTING COMPLETE log_user_activity FUNCTION")
    print("-" * 40)
    
    try:
        result = log_user_activity(
            user_email="test@example.com",
            activity_type="COMPLETE_TEST",
            page="test_complete_flow",
            first_name="Test",
            last_name="User",
            details="Testing complete log_user_activity function"
        )
        
        print(f"📝 log_user_activity result: {result}")
        
        if result:
            print("✅ Complete log_user_activity function works")
        else:
            print("❌ Complete log_user_activity function failed")
            return False
    except Exception as e:
        print(f"❌ Error in log_user_activity function: {e}")
        import traceback
        print(traceback.format_exc())
        return False
    
    print("\n✅ ALL TESTS PASSED - Activity logging should work!")
    return True

def check_recent_real_activity():
    """Check if there's been any real user activity recently"""
    print("\n6️⃣ CHECKING FOR RECENT REAL USER ACTIVITY")
    print("-" * 40)
    
    try:
        from core.database import get_db
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Check for recent activity in last few hours
            cursor.execute("""
                SELECT 
                    ua.timestamp,
                    ua.user_id,
                    ua.activity_type,
                    ua.page_url,
                    u.email,
                    u.first_name,
                    u.last_name
                FROM user_activity ua
                JOIN users u ON ua.user_id = u.id
                WHERE ua.timestamp >= NOW() - INTERVAL '6 HOURS'
                ORDER BY ua.timestamp DESC
                LIMIT 10
            """)
            
            activities = cursor.fetchall()
            
            if activities:
                print(f"📈 Found {len(activities)} activities in last 6 hours:")
                for activity in activities:
                    timestamp, user_id, activity_type, page_url, email, first_name, last_name = activity
                    print(f"  • {timestamp} | {first_name} {last_name} ({email}) | {activity_type} | {page_url}")
                return True
            else:
                print("❓ No real user activity found in last 6 hours")
                print("   This might explain why you're not getting notifications!")
                return False
                
    except Exception as e:
        print(f"❌ Error checking recent activity: {e}")
        return False

def main():
    """Run complete diagnostic"""
    print("🚀 ACTIVITY LOGGING FLOW DIAGNOSTIC")
    print("🕐 " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # Test the complete flow
    flow_works = test_complete_activity_flow()
    
    if flow_works:
        # Check for real activity
        has_real_activity = check_recent_real_activity()
        
        print("\n" + "=" * 60)
        print("📋 DIAGNOSTIC SUMMARY")
        print("=" * 60)
        
        if has_real_activity:
            print("🤔 MYSTERY: Everything works but no notifications received")
            print("   Possible causes:")
            print("   - Emails going to spam folder")
            print("   - SendGrid delivery issues")  
            print("   - Timing issues")
        else:
            print("💡 LIKELY CAUSE: No real user activity recently")
            print("   Solution: Visit some pages in staging to trigger activity")
            
        print("\n🎯 NEXT STEPS:")
        print("1. Check your email spam folder")
        print("2. Visit /mobile/my-series in staging")
        print("3. Check if you get an email within 1-2 minutes")
        
    else:
        print("\n❌ FOUND ISSUES IN ACTIVITY LOGGING FLOW")
        print("   Check the errors above for specific problems")

if __name__ == "__main__":
    main()
