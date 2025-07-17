#!/usr/bin/env python3
"""
Check staging notifications - captain messages and weather data
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_staging_notifications():
    """Check if captain messages and weather data are working on staging"""
    
    print("🔍 Checking Staging Notifications")
    print("=" * 50)
    
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
            port=parsed.port or 5432,
            sslmode="require",
            connect_timeout=10
        )
        
        with conn.cursor() as cursor:
            
            # 1. Check if captain_messages table exists
            print("\n1️⃣ Captain Messages Table:")
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'captain_messages'
                )
            """)
            
            table_exists = cursor.fetchone()[0]
            print(f"   Table exists: {table_exists}")
            
            if table_exists:
                # Check for any captain messages
                cursor.execute("SELECT COUNT(*) FROM captain_messages")
                message_count = cursor.fetchone()[0]
                print(f"   Total messages: {message_count}")
                
                if message_count > 0:
                    cursor.execute("""
                        SELECT cm.id, cm.message, cm.created_at, cm.team_id,
                               u.first_name, u.last_name, t.team_name
                        FROM captain_messages cm
                        JOIN users u ON cm.captain_user_id = u.id
                        JOIN teams t ON cm.team_id = t.id
                        ORDER BY cm.created_at DESC
                        LIMIT 5
                    """)
                    
                    messages = cursor.fetchall()
                    print(f"   Recent messages:")
                    for msg in messages:
                        print(f"     - ID {msg[0]}: {msg[1][:50]}... (Team: {msg[5]}, Captain: {msg[4]} {msg[5]})")
            
            # 2. Check if weather_cache table exists
            print("\n2️⃣ Weather Cache Table:")
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'weather_cache'
                )
            """)
            
            weather_table_exists = cursor.fetchone()[0]
            print(f"   Table exists: {weather_table_exists}")
            
            if weather_table_exists:
                # Check for any weather data
                cursor.execute("SELECT COUNT(*) FROM weather_cache")
                weather_count = cursor.fetchone()[0]
                print(f"   Total weather entries: {weather_count}")
                
                if weather_count > 0:
                    cursor.execute("""
                        SELECT location, date, temperature_high, temperature_low, condition
                        FROM weather_cache
                        ORDER BY created_at DESC
                        LIMIT 3
                    """)
                    
                    weather_entries = cursor.fetchall()
                    print(f"   Recent weather data:")
                    for entry in weather_entries:
                        print(f"     - {entry[0]} ({entry[1]}): {entry[2]}°F/{entry[3]}°F, {entry[4]}")
            
            # 3. Check for schedule data
            print("\n3️⃣ Schedule Data:")
            cursor.execute("SELECT COUNT(*) FROM schedule")
            schedule_count = cursor.fetchone()[0]
            print(f"   Total schedule entries: {schedule_count}")
            
            if schedule_count > 0:
                cursor.execute("""
                    SELECT match_date, match_time, home_team, away_team, location
                    FROM schedule
                    WHERE match_date >= CURRENT_DATE
                    ORDER BY match_date ASC, match_time ASC
                    LIMIT 5
                """)
                
                upcoming_schedule = cursor.fetchall()
                print(f"   Upcoming schedule entries:")
                for entry in upcoming_schedule:
                    print(f"     - {entry[0]} {entry[1]}: {entry[2]} vs {entry[3]} at {entry[4]}")
            
            # 4. Check for team data
            print("\n4️⃣ Team Data:")
            cursor.execute("SELECT COUNT(*) FROM teams")
            team_count = cursor.fetchone()[0]
            print(f"   Total teams: {team_count}")
            
            if team_count > 0:
                cursor.execute("""
                    SELECT id, team_name, club_id, series_id
                    FROM teams
                    LIMIT 5
                """)
                
                teams = cursor.fetchall()
                print(f"   Sample teams:")
                for team in teams:
                    print(f"     - ID {team[0]}: {team[1]}")
            
            # 5. Check for user data with team associations
            print("\n5️⃣ User Team Associations:")
            cursor.execute("""
                SELECT COUNT(*) FROM users WHERE team_id IS NOT NULL
            """)
            
            users_with_teams = cursor.fetchone()[0]
            print(f"   Users with team_id: {users_with_teams}")
            
            if users_with_teams > 0:
                cursor.execute("""
                    SELECT u.id, u.first_name, u.last_name, u.team_id, t.team_name
                    FROM users u
                    LEFT JOIN teams t ON u.team_id = t.id
                    WHERE u.team_id IS NOT NULL
                    LIMIT 5
                """)
                
                users = cursor.fetchall()
                print(f"   Sample users with teams:")
                for user in users:
                    print(f"     - {user[1]} {user[2]} (Team: {user[4] or 'Unknown'})")
        
        conn.close()
        print(f"\n✅ Staging database check completed")
        
    except Exception as e:
        print(f"❌ Error checking staging database: {e}")
        return False
    
    return True

if __name__ == "__main__":
    check_staging_notifications() 