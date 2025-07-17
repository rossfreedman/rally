#!/usr/bin/env python3
"""
Test local notifications with team ID-based matching
"""

import os
import sys
import psycopg2
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.routes.api_routes import get_captain_messages, get_upcoming_schedule_notifications
from app.services.session_service import get_session_data_for_user

def test_local_notifications():
    """Test notifications on local database"""
    
    # Test user (Rob Werman)
    test_user_email = "rwerman@gmail.com"
    
    print("🔍 Testing Local Notifications")
    print("=" * 50)
    
    # Get user session data
    session_data = get_session_data_for_user(test_user_email)
    
    if not session_data:
        print("❌ Could not get session data for user")
        return
    
    print(f"👤 User: {session_data['first_name']} {session_data['last_name']}")
    print(f"🏆 Team: {session_data['team_name']}")
    print(f"🏆 Team ID: {session_data['team_id']}")
    print(f"🏆 League: {session_data['league_name']}")
    print()
    
    # Test captain messages
    print("📢 Testing Captain Messages:")
    captain_messages = get_captain_messages(session_data['id'], session_data['tenniscores_player_id'], session_data['league_id'], session_data['team_id'])
    print(f"   Found {len(captain_messages)} captain messages")
    for msg in captain_messages:
        print(f"   - {msg.get('title', 'No title')}: {msg.get('message', 'No message')[:50]}...")
    print()
    
    # Test upcoming schedule
    print("📅 Testing Upcoming Schedule:")
    schedule_notifications = get_upcoming_schedule_notifications(session_data['id'], session_data['tenniscores_player_id'], session_data['league_id'], session_data['team_id'])
    print(f"   Found {len(schedule_notifications)} schedule notifications")
    for notif in schedule_notifications:
        print(f"   - {notif.get('title', 'No title')}: {notif.get('message', 'No message')[:50]}...")
    print()
    
    # Check schedule data directly
    print("🔍 Direct Schedule Data Check:")
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL', 'postgresql://localhost/rally'))
        cursor = conn.cursor()
        
        # Check upcoming schedule entries for user's team
        if session_data['team_id']:
            team_id = session_data['team_id']
            today = datetime.now().date()
            
            cursor.execute("""
                SELECT id, match_date, home_team, away_team, home_team_id, away_team_id
                FROM schedule 
                WHERE (home_team_id = %s OR away_team_id = %s)
                AND match_date >= %s
                ORDER BY match_date
                LIMIT 5
            """, [team_id, team_id, today])
            
            schedule_entries = cursor.fetchall()
            print(f"   Found {len(schedule_entries)} upcoming schedule entries for team ID {team_id}")
            
            for entry in schedule_entries:
                print(f"   - {entry[1]}: {entry[2]} vs {entry[3]} (IDs: {entry[4]}/{entry[5]})")
        else:
            print("   No team context available")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"   Error checking schedule: {e}")
    
    print()
    print("✅ Local notification test complete")

if __name__ == "__main__":
    test_local_notifications() 