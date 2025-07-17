#!/usr/bin/env python3
"""
Debug why Upcoming Schedule notification isn't showing up

This script checks the entire flow from database to frontend to identify
why the Upcoming Schedule notification is missing from the mobile home screen.
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db
from app.routes.api_routes import get_upcoming_schedule_notifications, get_home_notifications
from app.services.session_service import get_session_data_for_user

def debug_upcoming_schedule():
    """Debug the entire Upcoming Schedule notification flow"""
    
    print("🔍 Debugging Upcoming Schedule Notification")
    print("=" * 50)
    
    # Test with a known user (Ross Freedman)
    test_email = "rossfreedman@gmail.com"
    
    print(f"\n1. Testing with user: {test_email}")
    
    # Get session data
    try:
        session_data = get_session_data_for_user(test_email)
        if not session_data:
            print("❌ No session data found for user")
            return
            
        player_id = session_data.get("tenniscores_player_id")
        league_id = session_data.get("league_id")
        team_id = session_data.get("team_id")
        
        # Get user_id from database since it's not in session_data
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("SELECT id FROM users WHERE email = %s", (test_email,))
            result = cursor.fetchone()
            user_id = result[0] if result else None
        
        print(f"✅ Session data found:")
        print(f"   User ID: {user_id}")
        print(f"   Player ID: {player_id}")
        print(f"   League ID: {league_id}")
        print(f"   Team ID: {team_id}")
        
    except Exception as e:
        print(f"❌ Error getting session data: {e}")
        return
    
    # Test the schedule notification function directly
    print(f"\n2. Testing get_upcoming_schedule_notifications() directly")
    try:
        schedule_notifications = get_upcoming_schedule_notifications(user_id, player_id, league_id, team_id)
        print(f"✅ Schedule notifications returned: {len(schedule_notifications)}")
        
        for i, notification in enumerate(schedule_notifications):
            print(f"   Notification {i+1}:")
            print(f"     ID: {notification.get('id')}")
            print(f"     Title: {notification.get('title')}")
            print(f"     Message: {notification.get('message')}")
            print(f"     Type: {notification.get('type')}")
            print(f"     Priority: {notification.get('priority')}")
            
    except Exception as e:
        print(f"❌ Error in get_upcoming_schedule_notifications: {e}")
        import traceback
        traceback.print_exc()
    
    # Test the full home notifications function
    print(f"\n3. Testing get_home_notifications() function")
    try:
        # Mock the session for the API function
        class MockSession:
            def get(self, key, default=None):
                if key == "user":
                    return {
                        "id": user_id,
                        "email": test_email,
                        "tenniscores_player_id": player_id
                    }
                return default
        
        # Mock the request context
        import flask
        from flask import g
        
        # Create a mock request context
        with flask.Flask(__name__).app_context():
            g.user = {
                "id": user_id,
                "email": test_email,
                "tenniscores_player_id": player_id
            }
            
            # Call the function
            result = get_home_notifications()
            
            if hasattr(result, 'json'):
                notifications = result.json.get('notifications', [])
            else:
                notifications = result.get('notifications', [])
            
            print(f"✅ Home notifications returned: {len(notifications)}")
            
            # Look for Upcoming Schedule
            upcoming_schedule_found = False
            for i, notification in enumerate(notifications):
                print(f"   Notification {i+1}: {notification.get('title')} (Priority: {notification.get('priority')})")
                if notification.get('title') == 'Upcoming Schedule':
                    upcoming_schedule_found = True
                    print(f"     ✅ Found Upcoming Schedule notification!")
                    print(f"     Message: {notification.get('message')}")
                    print(f"     Type: {notification.get('type')}")
            
            if not upcoming_schedule_found:
                print(f"   ❌ Upcoming Schedule notification NOT found in home notifications")
                
    except Exception as e:
        print(f"❌ Error in get_home_notifications: {e}")
        import traceback
        traceback.print_exc()
    
    # Check database for schedule data
    print(f"\n4. Checking database for schedule data")
    try:
        with get_db() as db:
            cursor = db.cursor()
        
        # Check if team has any schedule entries
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM schedule 
            WHERE (home_team_id = %s OR away_team_id = %s)
            AND match_date >= CURRENT_DATE
        """, (team_id, team_id))
        
        result = cursor.fetchone()
        upcoming_count = result[0] if result else 0
        print(f"✅ Found {upcoming_count} upcoming schedule entries for team {team_id}")
        
        if upcoming_count > 0:
            # Show the actual schedule entries
            cursor.execute("""
                SELECT 
                    match_date,
                    match_time,
                    home_team,
                    away_team,
                    location,
                    CASE 
                        WHEN home_team_id = %s THEN 'practice'
                        ELSE 'match'
                    END as type
                FROM schedule 
                WHERE (home_team_id = %s OR away_team_id = %s)
                AND match_date >= CURRENT_DATE
                ORDER BY match_date ASC, match_time ASC
                LIMIT 5
            """, (team_id, team_id, team_id))
            
            entries = cursor.fetchall()
            print(f"   Upcoming entries:")
            for entry in entries:
                print(f"     {entry[0]} {entry[1]}: {entry[2]} vs {entry[3]} ({entry[4]}) - {entry[5]}")
        else:
            print(f"   ❌ No upcoming schedule entries found - this explains why notification is missing")
        
        cursor.close()
        db.close()
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()
    
            # Check if there are any completed matches (to verify team_id is correct)
    print(f"\n5. Verifying team_id is correct")
    try:
        with get_db() as db:
            cursor = db.cursor()
        
        # Check for any matches (past or future) for this team
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM schedule 
            WHERE (home_team_id = %s OR away_team_id = %s)
        """, (team_id, team_id))
        
        result = cursor.fetchone()
        total_count = result[0] if result else 0
        print(f"✅ Found {total_count} total schedule entries for team {team_id}")
        
        if total_count == 0:
            print(f"   ❌ No schedule entries at all for team {team_id}")
            print(f"   This suggests the team_id might be wrong")
            
            # Try to find the correct team_id
            cursor.execute("""
                SELECT t.id, t.name, c.name as club_name, s.name as series_name
                FROM teams t
                JOIN clubs c ON t.club_id = c.id
                JOIN series s ON t.series_id = s.id
                WHERE c.name LIKE '%%Tennaqua%%'
                ORDER BY t.id DESC
                LIMIT 10
            """)
            
            teams = cursor.fetchall()
            print(f"   Available Tennaqua teams:")
            for team in teams:
                print(f"     Team ID {team[0]}: {team[1]} ({team[2]} - {team[3]})")
        
            cursor.close()
        
    except Exception as e:
        print(f"❌ Error verifying team_id: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n" + "=" * 50)
    print(f"🔍 Debug Summary:")
    print(f"   - Check if team_id {team_id} has any schedule entries")
    print(f"   - If no entries, the notification won't show")
    print(f"   - If entries exist, check the notification generation logic")
    print(f"   - Verify the API endpoint is being called correctly")

if __name__ == "__main__":
    debug_upcoming_schedule() 