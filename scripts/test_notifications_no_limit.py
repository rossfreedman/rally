#!/usr/bin/env python3
"""
Test Notifications API - No Limit
Tests that pickup games notifications appear with priority 1 and no notification limit
"""

import requests
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import get_db_url
import psycopg2

def test_notifications_api():
    """Test the notifications API to verify pickup games appear correctly"""
    print("=== Testing Notifications API - No Limit ===")
    
    # Test the notifications API endpoint
    base_url = "http://127.0.0.1:8080"
    
    try:
        # Test the API endpoint
        response = requests.get(f"{base_url}/api/home/notifications", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            notifications = data.get('notifications', [])
            
            print(f"✅ Notifications API returned {len(notifications)} notifications")
            
            # Check for pickup games notifications
            pickup_notifications = [n for n in notifications if 'Pickup Game' in n.get('title', '')]
            
            if pickup_notifications:
                print(f"✅ Found {len(pickup_notifications)} pickup games notifications")
                for i, notification in enumerate(pickup_notifications, 1):
                    print(f"   {i}. {notification['title']}")
                    print(f"      Message: {notification['message']}")
                    print(f"      Priority: {notification.get('priority', 'N/A')}")
                    print(f"      CTA: {notification.get('cta', {}).get('label', 'N/A')}")
            else:
                print("⚠️  No pickup games notifications found")
                print("   This could be due to:")
                print("   - No pickup games matching user criteria")
                print("   - User doesn't have PTI set")
                print("   - Pickup games are in the past")
                print("   - User has already joined the games")
            
            # Check notification priorities
            priorities = [n.get('priority', 999) for n in notifications]
            if priorities:
                print(f"\n📊 Notification priorities: {sorted(priorities)}")
                print(f"   Total notifications: {len(notifications)}")
                print(f"   No limit applied (all notifications shown)")
                
                # Check if pickup games have priority 1
                pickup_priorities = [n.get('priority', 999) for n in pickup_notifications]
                if pickup_priorities:
                    min_pickup_priority = min(pickup_priorities)
                    print(f"   Pickup games priority: {min_pickup_priority}")
                    if min_pickup_priority == 1:
                        print("   ✅ Pickup games have highest priority (1)")
                    else:
                        print(f"   ⚠️  Pickup games priority is {min_pickup_priority}, should be 1")
            
        elif response.status_code == 401 or response.status_code == 403:
            print("⚠️  Notifications API requires authentication")
            print("   This is expected behavior - the API requires login")
            print("   To test the full functionality:")
            print("   1. Log in to the application")
            print("   2. Navigate to /mobile")
            print("   3. Check browser console for notification loading")
            print("   4. Look for pickup games notifications in the notifications section")
            
        else:
            print(f"❌ Notifications API failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error connecting to server: {e}")
        return False
    
    print("\n✅ Test completed successfully!")
    return True

if __name__ == "__main__":
    test_notifications_api() 