#!/usr/bin/env python3
"""
Script to debug why schedule notifications aren't finding data for team 59176
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db

def debug_schedule_data():
    print("=== Debugging Schedule Data for Team 59176 ===\n")
    
    team_id = 59176  # Tennaqua - 22
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check team info
        team_query = """
            SELECT 
                t.id,
                t.team_name,
                t.series_id,
                s.name as series_name,
                c.name as club_name
            FROM teams t
            LEFT JOIN series s ON t.series_id = s.id
            LEFT JOIN clubs c ON t.club_id = c.id
            WHERE t.id = %s
        """
        
        cursor.execute(team_query, [team_id])
        team_info = cursor.fetchone()
        
        if team_info:
            print(f"1. Team info for ID {team_id}:")
            print(f"   - Team Name: {team_info[1]}")
            print(f"   - Series: {team_info[3]} (ID: {team_info[2]})")
            print(f"   - Club: {team_info[4]}")
        else:
            print(f"1. ❌ No team found for ID {team_id}")
            return
        
        # Check schedule entries for this team
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
        
        print(f"\n2. Schedule entries for team {team_id}:")
        print(f"   Found {len(schedule_entries)} entries")
        
        if schedule_entries:
            for entry in schedule_entries:
                print(f"   - {entry[1]} at {entry[2]}: {entry[8]} ({entry[5]} vs {entry[6]})")
        else:
            print("   ❌ No schedule entries found")
        
        # Check what schedule entries exist for Tennaqua
        tennaqua_schedule_query = """
            SELECT 
                s.id,
                s.match_date,
                s.match_time,
                s.home_team,
                s.away_team,
                s.home_team_id,
                s.away_team_id,
                t.team_name,
                s2.name as series_name
            FROM schedule s
            LEFT JOIN teams t ON (s.home_team_id = t.id OR s.away_team_id = t.id)
            LEFT JOIN series s2 ON t.series_id = s2.id
            WHERE (s.home_team LIKE '%Tennaqua%' OR s.away_team LIKE '%Tennaqua%')
            AND s.match_date >= CURRENT_DATE
            ORDER BY s.match_date ASC
            LIMIT 10
        """
        
        cursor.execute(tennaqua_schedule_query)
        tennaqua_entries = cursor.fetchall()
        
        print(f"\n3. Tennaqua schedule entries:")
        print(f"   Found {len(tennaqua_entries)} entries")
        
        if tennaqua_entries:
            for entry in tennaqua_entries:
                print(f"   - {entry[1]} at {entry[2]}: {entry[3]} vs {entry[4]}")
                print(f"     Home Team ID: {entry[5]}, Away Team ID: {entry[6]}")
                print(f"     Team Name: {entry[7]}, Series: {entry[8]}")
        else:
            print("   ❌ No Tennaqua schedule entries found")
        
        # Check what the schedule table structure looks like
        print(f"\n4. Checking schedule table structure...")
        
        structure_query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'schedule' 
            ORDER BY ordinal_position
        """
        
        cursor.execute(structure_query)
        columns = cursor.fetchall()
        
        print(f"   Schedule table columns:")
        for col in columns:
            print(f"   - {col[0]}: {col[1]}")
        
        # Check a few sample schedule entries
        sample_query = """
            SELECT 
                s.id,
                s.match_date,
                s.match_time,
                s.home_team,
                s.away_team,
                s.home_team_id,
                s.away_team_id
            FROM schedule s
            WHERE s.match_date >= CURRENT_DATE
            ORDER BY s.match_date ASC
            LIMIT 5
        """
        
        cursor.execute(sample_query)
        sample_entries = cursor.fetchall()
        
        print(f"\n5. Sample schedule entries:")
        for entry in sample_entries:
            print(f"   - ID: {entry[0]}, Date: {entry[1]}, Time: {entry[2]}")
            print(f"     Teams: {entry[3]} vs {entry[4]}")
            print(f"     Team IDs: {entry[5]} vs {entry[6]}")
    
    print("\n✅ Debug completed")

if __name__ == "__main__":
    debug_schedule_data() 