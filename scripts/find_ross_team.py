#!/usr/bin/env python3
"""
Script to find Ross's correct team ID
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db

def find_ross_team():
    print("=== Finding Ross's Correct Team ID ===\n")
    
    player_id = "nndz-WlNhd3hMYi9nQT09"  # Ross's player ID
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Find Ross's player record
        player_query = """
            SELECT 
                p.id,
                p.tenniscores_player_id,
                p.pti,
                p.series_id,
                p.club_id,
                p.team_id,
                s.name as series_name,
                c.name as club_name,
                t.team_name
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE p.tenniscores_player_id = %s
        """
        
        cursor.execute(player_query, [player_id])
        player_records = cursor.fetchall()
        
        print(f"1. Found {len(player_records)} player records for Ross:")
        
        for i, record in enumerate(player_records, 1):
            print(f"   Record {i}:")
            print(f"   - Player ID: {record[1]}")
            print(f"   - PTI: {record[2]}")
            print(f"   - Series: {record[6]} (ID: {record[3]})")
            print(f"   - Club: {record[7]} (ID: {record[4]})")
            print(f"   - Team: {record[8]} (ID: {record[5]})")
            print()
        
        # Find teams that match Ross's series and club
        teams_query = """
            SELECT 
                t.id,
                t.team_name,
                t.series_id,
                s.name as series_name,
                c.name as club_name
            FROM teams t
            LEFT JOIN series s ON t.series_id = s.id
            LEFT JOIN clubs c ON t.club_id = c.id
            WHERE s.name = 'Chicago 22' AND c.name = 'Tennaqua'
            ORDER BY t.id
        """
        
        cursor.execute(teams_query)
        matching_teams = cursor.fetchall()
        
        print(f"2. Teams matching 'Chicago 22' and 'Tennaqua':")
        
        if matching_teams:
            for team in matching_teams:
                print(f"   - Team ID: {team[0]}, Name: {team[1]}, Series: {team[3]}, Club: {team[4]}")
        else:
            print("   ❌ No teams found matching 'Chicago 22' and 'Tennaqua'")
        
        # Check what teams exist for Tennaqua
        tennaqua_teams_query = """
            SELECT 
                t.id,
                t.team_name,
                t.series_id,
                s.name as series_name,
                c.name as club_name
            FROM teams t
            LEFT JOIN series s ON t.series_id = s.id
            LEFT JOIN clubs c ON t.club_id = c.id
            WHERE c.name = 'Tennaqua'
            ORDER BY t.id
        """
        
        cursor.execute(tennaqua_teams_query)
        tennaqua_teams = cursor.fetchall()
        
        print(f"\n3. All Tennaqua teams:")
        
        if tennaqua_teams:
            for team in tennaqua_teams:
                print(f"   - Team ID: {team[0]}, Name: {team[1]}, Series: {team[3]}, Club: {team[4]}")
        else:
            print("   ❌ No Tennaqua teams found")
        
        # Check what series exist for Chicago
        chicago_series_query = """
            SELECT 
                s.id,
                s.name,
                l.name as league_name
            FROM series s
            LEFT JOIN leagues l ON s.league_id = l.id
            WHERE s.name LIKE '%Chicago%'
            ORDER BY s.name
        """
        
        cursor.execute(chicago_series_query)
        chicago_series = cursor.fetchall()
        
        print(f"\n4. Chicago series:")
        
        if chicago_series:
            for series in chicago_series:
                print(f"   - Series ID: {series[0]}, Name: {series[1]}, League: {series[2]}")
        else:
            print("   ❌ No Chicago series found")
    
    print("\n✅ Analysis completed")

if __name__ == "__main__":
    find_ross_team() 