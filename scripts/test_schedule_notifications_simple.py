#!/usr/bin/env python3
"""
Simple test for schedule notifications without weather service
"""

import os
import sys
import psycopg2
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one

def test_schedule_notifications_simple():
    """Test schedule notifications without weather service"""
    
    # Test user data
    user_id = 888  # Rob Werman
    player_id = "nndz-WkNHeHdiZjVoUT09"
    league_id = 4492  # NSTF
    team_id = 57329  # Tennaqua S1
    
    print("🔍 Testing Schedule Notifications (Simple)")
    print("=" * 50)
    print(f"👤 User ID: {user_id}")
    print(f"🏆 Team ID: {team_id}")
    print(f"🏆 League ID: {league_id}")
    print()
    
    try:
        # Get user's team information from database
        user_info_query = """
            SELECT 
                c.name as club_name,
                s.name as series_name
            FROM players p
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.tenniscores_player_id = %s
            ORDER BY p.id DESC
            LIMIT 1
        """
        
        user_info = execute_query_one(user_info_query, [player_id])
        if not user_info:
            print("❌ No user info found")
            return
            
        user_club = user_info.get("club_name")
        user_series = user_info.get("series_name")
        
        print(f"🏆 Club: {user_club}")
        print(f"🏆 Series: {user_series}")
        print()
        
        if not user_club or not user_series:
            print("❌ Missing club or series info")
            return
        
        # Get current date/time
        now = datetime.now()
        current_date = now.date()
        
        print(f"📅 Current date: {current_date}")
        print()
        
        # Query upcoming schedule entries using team_id
        schedule_query = """
            SELECT 
                s.id,
                s.match_date,
                s.match_time,
                s.home_team_id,
                s.away_team_id,
                s.home_team,
                s.away_team,
                s.location,
                CASE 
                    WHEN s.home_team_id = %s THEN 'practice'
                    ELSE 'match'
                END as type
            FROM schedule s
            WHERE (s.home_team_id = %s OR s.away_team_id = %s)
            AND s.match_date >= %s
            ORDER BY s.match_date ASC, s.match_time ASC
            LIMIT 10
        """
        
        schedule_entries = execute_query(schedule_query, [team_id, team_id, team_id, current_date])
        
        print(f"📅 Found {len(schedule_entries)} schedule entries")
        
        # Convert to dicts (execute_query already returns dicts)
        schedule_entries = [
            {
                'id': row['id'],
                'match_date': row['match_date'],
                'match_time': row['match_time'],
                'home_team_id': row['home_team_id'],
                'away_team_id': row['away_team_id'],
                'home_team': row['home_team'],
                'away_team': row['away_team'],
                'location': row['location'],
                'type': row['type'],
            }
            for row in schedule_entries
        ]
        
        if not schedule_entries:
            print("❌ No schedule entries found")
            return
        
        # Find next practice and next match
        next_practice = None
        next_match = None
        
        for entry in schedule_entries:
            print(f"   - {entry['match_date']}: {entry['home_team']} vs {entry['away_team']} ({entry['type']})")
            if entry["type"] == "practice" and not next_practice:
                next_practice = entry
            elif entry["type"] == "match" and not next_match:
                next_match = entry
            
            if next_practice and next_match:
                break
        
        print()
        
        # Build notification message
        practice_text = "No upcoming practices"
        match_text = "No upcoming matches"
        
        if next_practice:
            practice_date = next_practice["match_date"].strftime("%b %d")
            practice_time = next_practice["match_time"].strftime("%I:%M %p").lstrip("0") if next_practice["match_time"] else ""
            practice_text = f"Practice: {practice_date}"
            if practice_time:
                practice_text += f" at {practice_time}"
        
        if next_match:
            match_date = next_match["match_date"].strftime("%b %d")
            match_time = next_match["match_time"].strftime("%I:%M %p").lstrip("0") if next_match["match_time"] else ""
            # Determine opponent using team_id
            if next_match["home_team_id"] == team_id:
                opponent = next_match["away_team"]
            else:
                opponent = next_match["home_team"]
            match_text = f"Match: {match_date}"
            if match_time:
                match_text += f" at {match_time}"
            if opponent:
                match_text += f" vs {opponent}"
        
        print("📢 Notification Message:")
        print(f"   {practice_text}")
        print(f"   {match_text}")
        print()
        
        # Create notification data
        notification_data = {
            "id": "upcoming_schedule",
            "type": "schedule",
            "title": "Upcoming Schedule",
            "message": f"{practice_text}\n{match_text}",
            "cta": {"label": "View Schedule", "href": "/mobile/availability"},
            "priority": 2
        }
        
        print("✅ Schedule notification created successfully!")
        print(f"   Title: {notification_data['title']}")
        print(f"   Message: {notification_data['message']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_schedule_notifications_simple() 