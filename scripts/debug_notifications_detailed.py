#!/usr/bin/env python3
"""
Debug why Captain's Message and Upcoming Schedule notifications aren't showing
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def debug_notifications_detailed():
    """Debug why specific notifications aren't showing"""
    
    print("🔍 Debugging Notifications - Detailed Analysis")
    print("=" * 60)
    
    # Staging database URL
    staging_url = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"
    
    try:
        # Parse and connect to staging database
        parsed = urlparse(staging_url)
        conn = psycopg2.connect(
            dbname=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port
        )
        
        cursor = conn.cursor()
        
        # Test user data (Ross)
        user_id = 43
        player_id = "nndz-WkMrK3didjlnUT09"
        league_id = 4823
        team_id = 48003
        
        print(f"Testing with user data:")
        print(f"  User ID: {user_id}")
        print(f"  Player ID: {player_id}")
        print(f"  League ID: {league_id}")
        print(f"  Team ID: {team_id}")
        print()
        
        # 1. Check Captain Messages
        print("1. 🔍 Checking Captain Messages")
        print("-" * 40)
        
        captain_query = """
            SELECT 
                cm.id,
                cm.message,
                cm.created_at,
                u.first_name,
                u.last_name
            FROM captain_messages cm
            JOIN users u ON cm.captain_user_id = u.id
            WHERE cm.team_id = %s
            ORDER BY cm.created_at DESC
            LIMIT 5
        """
        
        cursor.execute(captain_query, [team_id])
        captain_messages = cursor.fetchall()
        
        if captain_messages:
            print(f"✅ Found {len(captain_messages)} captain messages:")
            for msg in captain_messages:
                print(f"   - ID: {msg[0]}, Message: {msg[1][:50]}..., Created: {msg[2]}")
        else:
            print("❌ No captain messages found for team_id:", team_id)
        
        print()
        
        # 2. Check User Info for Schedule
        print("2. 🔍 Checking User Info for Schedule")
        print("-" * 40)
        
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
        
        cursor.execute(user_info_query, [player_id])
        user_info = cursor.fetchone()
        
        if user_info:
            club_name, series_name = user_info
            print(f"✅ User info found:")
            print(f"   - Club: {club_name}")
            print(f"   - Series: {series_name}")
        else:
            print("❌ No user info found for player_id:", player_id)
            return
        
        # 3. Check Schedule Entries
        print()
        print("3. 🔍 Checking Schedule Entries")
        print("-" * 40)
        
        # Build patterns
        if "Series" in series_name:
            series_code = series_name.replace("Series ", "S")
            team_pattern = f"{club_name} {series_code} - {series_name}"
        elif "Division" in series_name:
            division_num = series_name.replace("Division ", "")
            team_pattern = f"{club_name} {division_num} - Series {division_num}"
        else:
            series_num = series_name.split()[-1] if series_name else ""
            team_pattern = f"{club_name} - {series_num}"
        
        if "Division" in series_name:
            division_num = series_name.replace("Division ", "")
            practice_pattern = f"{club_name} Practice - Series {division_num}"
        else:
            practice_pattern = f"{club_name} Practice - {series_name}"
        
        print(f"Team pattern: {team_pattern}")
        print(f"Practice pattern: {practice_pattern}")
        
        # Check schedule entries
        schedule_query = """
            SELECT 
                s.id,
                s.match_date,
                s.match_time,
                s.home_team,
                s.away_team,
                s.location,
                CASE 
                    WHEN s.home_team ILIKE %s THEN 'practice'
                    ELSE 'match'
                END as type
            FROM schedule s
            WHERE (
                (s.home_team ILIKE %s OR s.away_team ILIKE %s) OR  -- Regular matches
                (s.home_team ILIKE %s)  -- Practices
            )
            AND s.match_date >= CURRENT_DATE
            ORDER BY s.match_date ASC, s.match_time ASC
            LIMIT 10
        """
        
        cursor.execute(schedule_query, [
            practice_pattern,  # For type detection
            f"%{team_pattern}%", f"%{team_pattern}%",  # Regular matches
            f"%{practice_pattern}%",  # Practices
        ])
        
        schedule_entries = cursor.fetchall()
        
        if schedule_entries:
            print(f"✅ Found {len(schedule_entries)} schedule entries:")
            for entry in schedule_entries:
                print(f"   - {entry[6]}: {entry[3]} vs {entry[4]} on {entry[1]} at {entry[2]}")
        else:
            print("❌ No schedule entries found")
            
            # Check what's in the schedule table
            cursor.execute("SELECT DISTINCT home_team FROM schedule WHERE match_date >= CURRENT_DATE LIMIT 10")
            sample_teams = cursor.fetchall()
            print(f"   Sample teams in schedule: {[t[0] for t in sample_teams]}")
        
        print()
        
        # 4. Check Weather Cache
        print("4. 🔍 Checking Weather Cache")
        print("-" * 40)
        
        cursor.execute("SELECT COUNT(*) FROM weather_cache")
        weather_count = cursor.fetchone()[0]
        print(f"Weather cache entries: {weather_count}")
        
        if weather_count > 0:
            cursor.execute("SELECT location, date, temperature_high, temperature_low FROM weather_cache LIMIT 3")
            sample_weather = cursor.fetchall()
            print(f"Sample weather data: {sample_weather}")
        
        print()
        
        # 5. Test the actual notification functions
        print("5. 🔍 Testing Notification Functions")
        print("-" * 40)
        
        # Import the functions
        from app.routes.api_routes import get_captain_messages, get_upcoming_schedule_notifications
        
        # Test captain messages
        captain_notifications = get_captain_messages(user_id, player_id, league_id, team_id)
        print(f"Captain notifications returned: {len(captain_notifications)}")
        for notif in captain_notifications:
            print(f"   - {notif.get('title')}: {notif.get('message')}")
        
        # Test schedule notifications
        schedule_notifications = get_upcoming_schedule_notifications(user_id, player_id, league_id, team_id)
        print(f"Schedule notifications returned: {len(schedule_notifications)}")
        for notif in schedule_notifications:
            print(f"   - {notif.get('title')}: {notif.get('message')}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_notifications_detailed() 