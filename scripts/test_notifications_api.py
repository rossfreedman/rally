#!/usr/bin/env python3
"""
Script to test the notifications API with Ross's session data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes.api_routes import get_home_notifications
from app.services.session_service import get_session_data_for_user

def test_notifications_api():
    print("=== Testing Notifications API for Ross ===\n")
    
    user_email = "rossfreedman@gmail.com"
    
    print(f"1. Getting session data for {user_email}...")
    
    try:
        # Get Ross's session data
        session_data = get_session_data_for_user(user_email)
        
        if not session_data:
            print("❌ No session data returned")
            return
        
        print(f"   ✅ Session data retrieved:")
        print(f"   - User ID: {session_data.get('id')}")
        print(f"   - Team ID: {session_data.get('team_id')}")
        print(f"   - League ID: {session_data.get('league_id')}")
        print(f"   - Player ID: {session_data.get('tenniscores_player_id')}")
        
        print(f"\n2. Testing notifications API...")
        
        # Mock the session for the API call
        import flask
        from flask import session
        
        # Create a mock session
        with flask.Flask(__name__).app_context():
            session["user"] = session_data
            
            # Call the notifications function
            from flask import jsonify
            response = get_home_notifications()
            
            if hasattr(response, 'json'):
                notifications_data = response.json
            else:
                notifications_data = response[0].json
            
            print(f"   ✅ API returned {len(notifications_data.get('notifications', []))} notifications:")
            
            for i, notification in enumerate(notifications_data.get('notifications', []), 1):
                print(f"   {i}. {notification['title']} (Priority: {notification['priority']})")
                print(f"      Message: {notification['message'][:80]}...")
                
                # Check if this is the upcoming schedule notification
                if notification['title'] == 'Upcoming Schedule':
                    print(f"      ✅ Found Upcoming Schedule notification!")
                elif notification['title'] == 'Pickup Game Available':
                    print(f"      ✅ Found Pickup Game notification!")
        
    except Exception as e:
        print(f"❌ Error testing API: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Test completed")

if __name__ == "__main__":
    test_notifications_api() 