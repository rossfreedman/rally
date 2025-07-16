#!/usr/bin/env python3
"""
Check user's team pattern and what the schedule notification should be looking for
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db
from datetime import datetime, date

def check_user_team_pattern():
    """Check user's team pattern"""
    
    player_id = "nndz-WlNhd3hMYi9nQT09"  # Ross's player ID
    
    print(f"Checking team pattern for player: {player_id}")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get user's team information
        cursor.execute("""
            SELECT 
                p.tenniscores_player_id,
                c.name as club_name,
                s.name as series_name
            FROM players p
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.tenniscores_player_id = %s
            ORDER BY p.id DESC
        """, [player_id])
        
        player_records = cursor.fetchall()
        print(f"\nFound {len(player_records)} player records:")
        for record in player_records:
            print(f"  Club: {record[1]}")
            print(f"  Series: {record[2]}")
            print()
        
        # Check what team pattern would be generated
        if player_records:
            user_club = player_records[0][1]
            user_series = player_records[0][2]
            
            print(f"User Club: {user_club}")
            print(f"User Series: {user_series}")
            
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
            
            print(f"\nGenerated patterns:")
            print(f"  Team Pattern: {team_pattern}")
            print(f"  Practice Pattern: {practice_pattern}")
            
            # Check if this pattern matches any schedule entries
            cursor.execute("""
                SELECT 
                    match_date,
                    match_time,
                    home_team,
                    away_team,
                    location
                FROM schedule 
                WHERE (home_team ILIKE %s OR away_team ILIKE %s)
                AND match_date >= CURRENT_DATE
                ORDER BY match_date ASC, match_time ASC
                LIMIT 5
            """, [f"%{team_pattern}%", f"%{team_pattern}%"])
            
            matching_entries = cursor.fetchall()
            print(f"\nFound {len(matching_entries)} matching schedule entries:")
            for entry in matching_entries:
                print(f"  {entry}")
        
        cursor.close()

if __name__ == "__main__":
    check_user_team_pattern() 