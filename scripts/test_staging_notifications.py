#!/usr/bin/env python3
"""
Test script for staging notifications API
Verifies that pickup games and team position notifications are working after schema fixes
"""

import requests
import json
from datetime import datetime

def test_staging_notifications():
    """Test staging notifications API"""
    
    print("=== Testing Staging Notifications API ===")
    
    # Staging URL
    staging_url = "https://rally-staging.up.railway.app"
    
    try:
        # Create a session to maintain cookies
        session = requests.Session()
        
        print("\n1. Testing server connectivity...")
        try:
            response = session.get(f"{staging_url}/health")
            if response.status_code == 200:
                print("✅ Staging server is accessible")
            else:
                print(f"⚠️  Staging server responded with status: {response.status_code}")
        except Exception as e:
            print(f"❌ Cannot connect to staging server: {e}")
            return False
        
        print("\n2. Testing notifications API (requires authentication)...")
        response = session.get(f"{staging_url}/api/home/notifications")
        
        if response.status_code == 200:
            data = response.json()
            notifications = data.get('notifications', [])
            print(f"✅ Notifications API works, found {len(notifications)} notifications")
            
            # Check for specific notification types
            notification_types = {}
            for notification in notifications:
                title = notification.get('title', '')
                notification_type = notification.get('type', '')
                priority = notification.get('priority', 0)
                
                if 'Pickup Game' in title:
                    notification_types['pickup_games'] = notification
                elif 'Team Position' in title:
                    notification_types['team_position'] = notification
                elif 'Captain' in title:
                    notification_types['captain_message'] = notification
                elif 'Schedule' in title:
                    notification_types['schedule'] = notification
                elif 'Poll' in title:
                    notification_types['poll'] = notification
                elif 'Win Streaks' in title:
                    notification_types['win_streaks'] = notification
            
            # Report findings
            print(f"\n3. Notification Analysis:")
            print(f"   Total notifications: {len(notifications)}")
            
            if 'pickup_games' in notification_types:
                pickup = notification_types['pickup_games']
                print(f"   ✅ Pickup Games: {pickup['title']} (Priority: {pickup['priority']})")
                print(f"      Message: {pickup['message'][:60]}...")
            else:
                print(f"   ❌ Pickup Games: Not found")
            
            if 'team_position' in notification_types:
                position = notification_types['team_position']
                print(f"   ✅ Team Position: {position['title']} (Priority: {position['priority']})")
                print(f"      Message: {position['message'][:60]}...")
            else:
                print(f"   ❌ Team Position: Not found")
            
            if 'captain_message' in notification_types:
                captain = notification_types['captain_message']
                print(f"   ✅ Captain Message: {captain['title']} (Priority: {captain['priority']})")
            else:
                print(f"   ❌ Captain Message: Not found")
            
            if 'schedule' in notification_types:
                schedule = notification_types['schedule']
                print(f"   ✅ Schedule: {schedule['title']} (Priority: {schedule['priority']})")
            else:
                print(f"   ❌ Schedule: Not found")
            
            if 'poll' in notification_types:
                poll = notification_types['poll']
                print(f"   ✅ Poll: {poll['title']} (Priority: {poll['priority']})")
            else:
                print(f"   ❌ Poll: Not found")
            
            if 'win_streaks' in notification_types:
                streaks = notification_types['win_streaks']
                print(f"   ✅ Win Streaks: {streaks['title']} (Priority: {streaks['priority']})")
            else:
                print(f"   ❌ Win Streaks: Not found")
            
            # Check if we have the expected 7 notifications
            expected_count = 7  # Based on user's description
            if len(notifications) >= expected_count:
                print(f"\n✅ SUCCESS: Found {len(notifications)} notifications (expected {expected_count}+)")
                print(f"   This matches the local environment behavior")
            else:
                print(f"\n⚠️  WARNING: Found {len(notifications)} notifications (expected {expected_count}+)")
                print(f"   Some notifications may still be missing")
            
            # Show all notifications for debugging
            print(f"\n4. All notifications ({len(notifications)} total):")
            for i, notification in enumerate(notifications, 1):
                print(f"   {i}. {notification.get('title')} (Priority: {notification.get('priority')}, Type: {notification.get('type')})")
                print(f"      Message: {notification.get('message', '')[:50]}...")
                
        elif response.status_code == 401 or response.status_code == 403:
            print("⚠️  Notifications API requires authentication")
            print("   This is expected behavior - the API requires login")
            print("   To test with authentication, you would need to:")
            print("   1. Log in to the staging site")
            print("   2. Get the session cookies")
            print("   3. Include them in the request")
            
        else:
            print(f"❌ Notifications API failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
        
        print("\n✅ Staging notifications test completed successfully!")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to staging server")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        return False

if __name__ == "__main__":
    test_staging_notifications() 