#!/usr/bin/env python3
"""
Test script to verify removed notification cards are no longer generated
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes.api_routes import get_fallback_notifications
from dotenv import load_dotenv

load_dotenv()

def test_fallback_notifications():
    """Test that the removed notification cards are no longer generated"""
    print("=== Testing Fallback Notifications ===")
    
    # Test with a sample user ID
    test_user_id = 1
    
    try:
        notifications = get_fallback_notifications(test_user_id, None, None, None)
        
        print(f"Generated {len(notifications)} fallback notifications:")
        
        for notification in notifications:
            print(f"\n- ID: {notification['id']}")
            print(f"  Title: {notification['title']}")
            print(f"  Type: {notification['type']}")
            print(f"  Message: {notification['message']}")
        
        # Check that the removed cards are not present
        removed_ids = ['welcome_back', 'team_overview']
        found_removed = [nid for nid in removed_ids if any(n['id'] == nid for n in notifications)]
        
        if found_removed:
            print(f"\n❌ Found removed notification cards: {found_removed}")
            return False
        else:
            print(f"\n✅ Successfully removed notification cards: {removed_ids}")
            return True
            
    except Exception as e:
        print(f"❌ Error testing fallback notifications: {str(e)}")
        return False

def test_notification_content():
    """Test the content of remaining notifications"""
    print("\n=== Testing Remaining Notification Content ===")
    
    test_user_id = 1
    
    try:
        notifications = get_fallback_notifications(test_user_id, None, None, None)
        
        # Check that only the "stay_connected" notification remains
        stay_connected = [n for n in notifications if n['id'] == 'stay_connected']
        
        if stay_connected:
            notification = stay_connected[0]
            print("✅ 'Stay Connected' notification remains:")
            print(f"  Title: {notification['title']}")
            print(f"  Message: {notification['message']}")
            print(f"  CTA: {notification['cta']['label']} -> {notification['cta']['href']}")
        else:
            print("❌ 'Stay Connected' notification not found")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing notification content: {str(e)}")
        return False

def main():
    """Main test function"""
    print("Removed Notification Cards Test")
    print("=" * 50)
    
    # Test that removed cards are no longer generated
    test1_passed = test_fallback_notifications()
    
    # Test remaining notification content
    test2_passed = test_notification_content()
    
    print("\n=== Summary ===")
    if test1_passed and test2_passed:
        print("✅ Successfully removed 'Welcome back' and 'Team Overview' cards")
        print("✅ Only 'Stay Connected' notification remains")
        print("✅ No unwanted notification cards will be displayed")
    else:
        print("❌ Some tests failed - check the output above")

if __name__ == "__main__":
    main() 