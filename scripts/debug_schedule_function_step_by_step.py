#!/usr/bin/env python3
"""
Step-by-step debug of get_upcoming_schedule_notifications function
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db
from app.routes.api_routes import execute_query, execute_query_one

def debug_schedule_function():
    """Debug the schedule notification function step by step"""
    
    print("🔍 Step-by-Step Debug of Schedule Notification Function")
    print("=" * 60)
    
    # Test data from previous debug
    user_id = 43
    player_id = "nndz-WkMrK3didjlnUT09"
    league_id = 4763
    team_id = 57314
    
    print(f"Test data:")
    print(f"  User ID: {user_id}")
    print(f"  Player ID: {player_id}")
    print(f"  League ID: {league_id}")
    print(f"  Team ID: {team_id}")
    
    # Step 1: Check if team_id exists
    print(f"\n1. Checking if team_id exists...")
    if not team_id:
        print("❌ team_id is None or empty")
        return
    print("✅ team_id is valid")
    
    # Step 2: Get user's team information from database
    print(f"\n2. Getting user's team information...")
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
    
    try:
        user_info = execute_query_one(user_info_query, [player_id])
        if not user_info:
            print("❌ No user info found for player_id")
            return
            
        user_club = user_info.get("club_name")
        user_series = user_info.get("series_name")
        
        print(f"✅ User info found:")
        print(f"   Club: {user_club}")
        print(f"   Series: {user_series}")
        
        if not user_club or not user_series:
            print("❌ Missing club or series information")
            return
            
    except Exception as e:
        print(f"❌ Error getting user info: {e}")
        return
    
    # Step 3: Build team patterns
    print(f"\n3. Building team patterns...")
    
    # Build team pattern for matches
    if "Series" in user_series:
        # NSTF format: "Series 2B" -> "S2B"
        series_code = user_series.replace("Series ", "S")
        team_pattern = f"{user_club} {series_code} - {user_series}"
    elif "Division" in user_series:
        # CNSWPL format: "Division 12" -> "12"
        division_num = user_series.replace("Division ", "")
        team_pattern = f"{user_club} {division_num} - Series {division_num}"
    else:
        # APTA format: "Chicago 22" -> extract number
        series_num = user_series.split()[-1] if user_series else ""
        team_pattern = f"{user_club} - {series_num}"
    
    # Build practice pattern
    if "Division" in user_series:
        division_num = user_series.replace("Division ", "")
        practice_pattern = f"{user_club} Practice - Series {division_num}"
    else:
        practice_pattern = f"{user_club} Practice - {user_series}"
    
    print(f"✅ Team patterns built:")
    print(f"   Team pattern: {team_pattern}")
    print(f"   Practice pattern: {practice_pattern}")
    
    # Step 4: Get current date
    print(f"\n4. Getting current date...")
    now = datetime.now()
    current_date = now.date()
    print(f"✅ Current date: {current_date}")
    
    # Step 5: Query upcoming schedule entries
    print(f"\n5. Querying upcoming schedule entries...")
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
            c.club_address,
            CASE 
                WHEN s.home_team_id = %s THEN 'practice'
                ELSE 'match'
            END as type
        FROM schedule s
        LEFT JOIN teams t ON (s.home_team_id = t.id OR s.away_team_id = t.id)
        LEFT JOIN clubs c ON t.club_id = c.id
        WHERE (s.home_team_id = %s OR s.away_team_id = %s)
        AND s.match_date >= %s
        ORDER BY s.match_date ASC, s.match_time ASC
        LIMIT 10
    """
    
    try:
        schedule_entries = execute_query(schedule_query, [team_id, team_id, team_id, current_date])
        print(f"✅ Found {len(schedule_entries)} schedule entries")
        
        if schedule_entries:
            print(f"   Sample entries:")
            for i, entry in enumerate(schedule_entries[:3]):
                print(f"     Entry {i+1}: {entry[1]} {entry[2]} - {entry[5]} vs {entry[6]} ({entry[8]}) - {entry[9]}")
        else:
            print("❌ No schedule entries found")
            return
            
    except Exception as e:
        print(f"❌ Error querying schedule: {e}")
        return
    
    # Step 6: Convert to dicts
    print(f"\n6. Converting to dictionaries...")
    try:
        schedule_entries = [
            {
                'id': row[0],
                'match_date': row[1],
                'match_time': row[2],
                'home_team_id': row[3],
                'away_team_id': row[4],
                'home_team': row[5],
                'away_team': row[6],
                'location': row[7],
                'club_address': row[8],
                'type': row[9],
            }
            for row in schedule_entries
        ]
        print(f"✅ Converted {len(schedule_entries)} entries to dictionaries")
        
    except Exception as e:
        print(f"❌ Error converting to dicts: {e}")
        return
    
    # Step 7: Find next practice and next match
    print(f"\n7. Finding next practice and next match...")
    next_practice = None
    next_match = None
    
    for entry in schedule_entries:
        if entry["type"] == "practice" and not next_practice:
            next_practice = entry
            print(f"✅ Found next practice: {entry['match_date']} {entry['match_time']}")
        elif entry["type"] == "match" and not next_match:
            next_match = entry
            print(f"✅ Found next match: {entry['match_date']} {entry['match_time']}")
        
        if next_practice and next_match:
            break
    
    if not next_practice:
        print("❌ No next practice found")
    if not next_match:
        print("❌ No next match found")
    
    # Step 8: Build notification message
    print(f"\n8. Building notification message...")
    practice_text = "No upcoming practices"
    match_text = "No upcoming matches"
    
    if next_practice:
        practice_date = next_practice["match_date"].strftime("%b %d")
        practice_time = next_practice["match_time"].strftime("%I:%M %p").lstrip("0") if next_practice["match_time"] else ""
        practice_text = f"Practice: {practice_date}"
        if practice_time:
            practice_text += f" at {practice_time}"
        print(f"✅ Practice text: {practice_text}")
    
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
        print(f"✅ Match text: {match_text}")
    
    # Step 9: Create notification
    print(f"\n9. Creating notification...")
    notification_data = {
        "id": "upcoming_schedule",
        "type": "schedule",
        "title": "Upcoming Schedule",
        "message": f"{practice_text}\n{match_text}",
        "cta": {"label": "View Schedule", "href": "/mobile/availability"},
        "priority": 2
    }
    
    print(f"✅ Notification created:")
    print(f"   ID: {notification_data['id']}")
    print(f"   Title: {notification_data['title']}")
    print(f"   Message: {notification_data['message']}")
    print(f"   Type: {notification_data['type']}")
    print(f"   Priority: {notification_data['priority']}")
    
    print(f"\n🎉 Function completed successfully!")
    print(f"   The notification should be generated and returned")

if __name__ == "__main__":
    debug_schedule_function() 