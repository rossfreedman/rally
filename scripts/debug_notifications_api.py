#!/usr/bin/env python3
"""
Debug script to check what the notifications API actually returns
"""

import requests
import json

def debug_notifications_api():
    """Check what the notifications API returns"""
    
    # You'll need to replace this with your actual session cookie
    # Get this from your browser's dev tools -> Network tab -> cookies
    session_cookie = "your_session_cookie_here"  # Replace with actual cookie
    
    headers = {
        'Cookie': f'session={session_cookie}',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        # Make request to the notifications API
        response = requests.get('http://localhost:5000/api/home/notifications', headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            notifications = data.get('notifications', [])
            
            print(f"\nFound {len(notifications)} notifications:")
            for i, notification in enumerate(notifications, 1):
                print(f"\n{i}. Type: {notification.get('type')}")
                print(f"   Title: {notification.get('title')}")
                print(f"   Message: {notification.get('message')}")
                print(f"   Priority: {notification.get('priority')}")
                print(f"   ID: {notification.get('id')}")
            
            # Check specifically for schedule notification
            schedule_notifications = [n for n in notifications if n.get('type') == 'schedule']
            if schedule_notifications:
                print(f"\n✅ Schedule notification found: {schedule_notifications[0]}")
            else:
                print(f"\n❌ No schedule notification found!")
                
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Error making request: {str(e)}")

if __name__ == "__main__":
    print("To use this script:")
    print("1. Open your browser's dev tools")
    print("2. Go to Network tab")
    print("3. Reload the page")
    print("4. Find the request to /api/home/notifications")
    print("5. Copy the session cookie value")
    print("6. Replace 'your_session_cookie_here' in this script")
    print("7. Run the script")
    print()
    debug_notifications_api() 