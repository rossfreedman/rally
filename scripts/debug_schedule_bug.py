#!/usr/bin/env python3
"""
Debug Schedule Notification Bug

This script investigates the issue where:
1. Shows "Practice: Jul 24 at 6:00 PM" when no practices exist
2. Shows "No upcoming matches" but then shows matches correctly
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db

def debug_schedule_bug():
    """Debug the schedule notification bug"""
    
    # User data from the bug report
    player_id = "nndz-WlNhd3hMYnhoUT09"  # Ross's NSTF player ID
    team_id = 75996  # Tennaqua - 22 team ID (local)
    # team_id = 49865  # Tennaqua - 22 team ID (production)
    
    print("🔍 Debugging Schedule Notification Bug")
    print("=" * 50)
    print(f"Player ID: {player_id}")
    print(f"Team ID: {team_id}")
    print()
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 1. Check user's team information
            print("1. Checking user's team information...")
            user_info_query = """
                SELECT 
                    c.name as club_name,
                    s.name as series_name,
                    p.tenniscores_player_id
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
                club_name = user_info[0]
                series_name = user_info[1]
                print(f"   ✅ Found user info:")
                print(f"      Club: {club_name}")
                print(f"      Series: {series_name}")
            else:
                print(f"   ❌ No user info found for player ID: {player_id}")
                return
            
            # 2. Check team information
            print(f"\n2. Checking team information...")
            team_query = """
                SELECT 
                    t.id,
                    t.team_name,
                    t.display_name,
                    t.club_id,
                    c.name as club_name,
                    s.name as series_name
                FROM teams t
                LEFT JOIN clubs c ON t.club_id = c.id
                LEFT JOIN series s ON t.series_id = s.id
                WHERE t.id = %s
            """
            
            cursor.execute(team_query, [team_id])
            team_info = cursor.fetchone()
            
            if team_info:
                team_name = team_info[1]
                display_name = team_info[2]
                team_club = team_info[4]
                team_series = team_info[5]
                print(f"   ✅ Found team info:")
                print(f"      Team ID: {team_id}")
                print(f"      Team Name: {team_name}")
                print(f"      Display Name: {display_name}")
                print(f"      Team Club: {team_club}")
                print(f"      Team Series: {team_series}")
            else:
                print(f"   ❌ No team info found for team ID: {team_id}")
                return
            
            # 3. Check schedule entries for this team
            print(f"\n3. Checking schedule entries...")
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
                AND s.match_date >= CURRENT_DATE
                ORDER BY s.match_date ASC, s.match_time ASC
                LIMIT 10
            """
            
            cursor.execute(schedule_query, [team_id, team_id, team_id])
            schedule_entries = cursor.fetchall()
            
            print(f"   Found {len(schedule_entries)} upcoming schedule entries:")
            
            practices = []
            matches = []
            
            for entry in schedule_entries:
                entry_id, match_date, match_time, home_team_id, away_team_id, home_team, away_team, location, entry_type = entry
                
                if entry_type == 'practice':
                    practices.append({
                        'id': entry_id,
                        'date': match_date,
                        'time': match_time,
                        'home_team': home_team,
                        'away_team': away_team,
                        'location': location
                    })
                else:
                    matches.append({
                        'id': entry_id,
                        'date': match_date,
                        'time': match_time,
                        'home_team': home_team,
                        'away_team': away_team,
                        'location': location
                    })
                
                print(f"      {match_date} {match_time}: {home_team} vs {away_team} ({entry_type})")
            
            # 4. Analyze the notification logic
            print(f"\n4. Analyzing notification logic...")
            
            # Find next practice and next match
            next_practice = practices[0] if practices else None
            next_match = matches[0] if matches else None
            
            print(f"   Next practice: {next_practice}")
            print(f"   Next match: {next_match}")
            
            # Build notification message
            practice_text = "No upcoming practices"
            match_text = "No upcoming matches"
            
            if next_practice:
                practice_date = next_practice["date"].strftime("%b %d")
                practice_time = next_practice["time"].strftime("%I:%M %p").lstrip("0") if next_practice["time"] else ""
                practice_text = f"Practice: {practice_date}"
                if practice_time:
                    practice_text += f" at {practice_time}"
            
            if next_match:
                match_date = next_match["date"].strftime("%b %d")
                match_time = next_match["time"].strftime("%I:%M %p").lstrip("0") if next_match["time"] else ""
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
            
            print(f"\n5. Notification message would be:")
            print(f"   {practice_text}")
            print(f"   {match_text}")
            
            # 6. Check if there are any practice entries that might be causing the issue
            print(f"\n6. Checking for any practice-related entries...")
            
            # Check if there are any schedule entries with "Practice" in the team name
            practice_check_query = """
                SELECT 
                    s.id,
                    s.match_date,
                    s.match_time,
                    s.home_team,
                    s.away_team,
                    s.location
                FROM schedule s
                WHERE (s.home_team LIKE '%%Practice%%' OR s.away_team LIKE '%%Practice%%')
                AND s.match_date >= CURRENT_DATE
                ORDER BY s.match_date ASC, s.match_time ASC
                LIMIT 5
            """
            
            cursor.execute(practice_check_query)
            practice_entries = cursor.fetchall()
            
            print(f"   Found {len(practice_entries)} entries with 'Practice' in team name:")
            for entry in practice_entries:
                entry_id, match_date, match_time, home_team, away_team, location = entry
                print(f"      {match_date} {match_time}: {home_team} vs {away_team} ({location})")
            
            # 7. Check if the issue is with the team_id logic
            print(f"\n7. Checking team_id logic...")
            
            # The logic assumes that when home_team_id = team_id, it's a practice
            # But this might be incorrect for NSTF
            print(f"   Current logic: home_team_id = {team_id} = 'practice'")
            print(f"   This might be wrong for NSTF teams")
            
            # Check what the actual team_id values are in schedule
            team_id_check_query = """
                SELECT DISTINCT
                    home_team_id,
                    away_team_id,
                    home_team,
                    away_team,
                    COUNT(*) as count
                FROM schedule
                WHERE match_date >= CURRENT_DATE
                AND (home_team LIKE '%%Tennaqua%%' OR away_team LIKE '%%Tennaqua%%')
                GROUP BY home_team_id, away_team_id, home_team, away_team
                ORDER BY count DESC
                LIMIT 10
            """
            
            cursor.execute(team_id_check_query)
            team_entries = cursor.fetchall()
            
            print(f"   Tennaqua schedule entries by team_id:")
            for entry in team_entries:
                home_team_id, away_team_id, home_team, away_team, count = entry
                print(f"      {home_team_id} vs {away_team_id}: {home_team} vs {away_team} ({count} entries)")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_schedule_bug() 