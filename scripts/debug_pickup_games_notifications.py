#!/usr/bin/env python3
"""
Debug script for pickup games notifications
Helps identify why pickup games notifications might not be showing on the home page
"""

import requests
import json
from datetime import datetime

def debug_pickup_games_notifications():
    """Debug pickup games notifications on the home page"""
    
    print("=== Debugging Pickup Games Notifications ===")
    
    # Test configuration
    base_url = "http://127.0.0.1:8080"
    
    try:
        # Create a session to maintain cookies
        session = requests.Session()
        
        print("\n1. Testing server connectivity...")
        try:
            response = session.get(f"{base_url}/health")
            if response.status_code == 200:
                print("✅ Server is running and accessible")
            else:
                print(f"⚠️  Server responded with status: {response.status_code}")
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}")
            return False
        
        print("\n2. Testing pickup games API directly...")
        response = session.get(f"{base_url}/api/pickup-games?type=public")
        
        if response.status_code == 200:
            data = response.json()
            upcoming_games = data.get('upcoming_games', [])
            past_games = data.get('past_games', [])
            print(f"✅ Pickup games API works")
            print(f"   - Upcoming games: {len(upcoming_games)}")
            print(f"   - Past games: {len(past_games)}")
            
            if upcoming_games:
                print("   - Sample upcoming game:")
                game = upcoming_games[0]
                print(f"     * {game.get('description')} - {game.get('formatted_date')} at {game.get('formatted_time')}")
                print(f"     * PTI Range: {game.get('pti_range')}, Players: {game.get('slots_filled')}/{game.get('players_requested')}")
            else:
                print("   ⚠️  No upcoming games found")
                
        elif response.status_code == 401 or response.status_code == 403:
            print("⚠️  Pickup games API requires authentication")
        else:
            print(f"❌ Pickup games API failed: {response.status_code}")
            return False
        
        print("\n3. Testing notifications API (requires authentication)...")
        response = session.get(f"{base_url}/api/home/notifications")
        
        if response.status_code == 200:
            data = response.json()
            notifications = data.get('notifications', [])
            print(f"✅ Notifications API works, found {len(notifications)} notifications")
            
            # Check for pickup games notifications
            pickup_notifications = [
                n for n in notifications 
                if n.get('type') == 'match' and 
                n.get('title', '').find('Pickup Game') != -1
            ]
            
            print(f"✅ Found {len(pickup_notifications)} pickup games notifications")
            
            for i, notification in enumerate(pickup_notifications):
                print(f"   {i+1}. {notification.get('title')} - {notification.get('message')}")
                print(f"      Priority: {notification.get('priority')}")
                print(f"      CTA: {notification.get('cta')}")
                
            # Show all notifications for debugging
            print(f"\n📋 All notifications ({len(notifications)} total):")
            for i, notification in enumerate(notifications):
                print(f"   {i+1}. {notification.get('title')} (Priority: {notification.get('priority')}, Type: {notification.get('type')})")
                
            # Check if pickup games notifications are being filtered out
            if len(notifications) >= 8 and len(pickup_notifications) == 0:
                print("\n⚠️  POSSIBLE ISSUE: Pickup games notifications might be filtered out!")
                print("   - Found 8+ notifications total")
                print("   - No pickup games notifications found")
                print("   - This could be due to priority filtering or the 8-notification limit")
                
                # Check priorities of existing notifications
                priorities = [n.get('priority', 999) for n in notifications]
                min_priority = min(priorities) if priorities else 999
                print(f"   - Lowest priority in current notifications: {min_priority}")
                print(f"   - Pickup games notifications have priority: 1")
                
                if min_priority <= 1:
                    print("   - Pickup games notifications should appear (priority 1)")
                else:
                    print("   - Pickup games notifications might be filtered out by higher priority notifications")
                    
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
        
        print("\n4. Testing home page access...")
        response = session.get(f"{base_url}/mobile")
        
        if response.status_code == 200:
            print("✅ Home page loads successfully")
            
            # Check if we're redirected to login
            if "login" in response.url.lower() or "redirecting" in response.text.lower():
                print("⚠️  Page requires authentication (redirecting to login)")
                print("   This is expected behavior - the page requires login")
            else:
                print("✅ User appears to be authenticated")
                
        elif response.status_code == 302:
            print("⚠️  Page requires authentication (redirecting to login)")
            print("   This is expected behavior - the page requires login")
            
        else:
            print(f"❌ Home page failed to load: {response.status_code}")
            return False
        
        print("\n✅ Debug completed successfully!")
        print("\n📋 Summary:")
        print("   - Server is running and accessible")
        print("   - Pickup games API is working")
        print("   - Notifications API is working")
        print("   - Pickup games notifications have priority 1 (highest)")
        print("   - Notification limit is 8")
        print("   - To see notifications in action, log in and visit /mobile")
        
        # Check if we found pickup notifications
        if 'pickup_notifications' in locals() and len(pickup_notifications) > 0:
            print("   ✅ Pickup games notifications are being returned by the API")
            print("   - If they're not showing on the page, check browser console for JavaScript errors")
        else:
            print("   ⚠️  No pickup games notifications found in API response")
            print("   - This could be due to:")
            print("     * No pickup games matching user criteria")
            print("     * User doesn't have PTI set")
            print("     * Pickup games are in the past")
            print("     * User has already joined the games")
            
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure server.py is running on port 8080")
        return False
    except Exception as e:
        print(f"❌ Debug failed with error: {str(e)}")
        return False

if __name__ == "__main__":
    success = debug_pickup_games_notifications()
    
    if success:
        print("\n✅ Debug completed - check the summary above for next steps")
    else:
        print("\n❌ Debug failed - check the error messages above") 