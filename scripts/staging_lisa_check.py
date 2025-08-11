#!/usr/bin/env python3
"""
Check Lisa Wagner's team assignment - run this on staging
"""

import os
import sys
sys.path.append('/app')

from database_utils import execute_query, execute_query_one

def check_lisa_wagner():
    """Check Lisa Wagner's team assignment"""
    print("🔍 Checking Lisa Wagner's team assignment...")
    
    query = """
    SELECT p.first_name, p.last_name, p.tenniscores_player_id, 
           c.name as club, s.name as series, 
           t.team_name, t.display_name, l.league_id,
           p.team_id, t.id as actual_team_id
    FROM players p 
    JOIN clubs c ON p.club_id = c.id 
    JOIN series s ON p.series_id = s.id 
    LEFT JOIN teams t ON p.team_id = t.id 
    JOIN leagues l ON p.league_id = l.id 
    WHERE p.first_name = 'Lisa' AND p.last_name = 'Wagner'
    """
    
    try:
        result = execute_query_one(query)
        
        if result:
            print("STAGING - Lisa Wagner's assignment:")
            for key, value in result.items():
                print(f"  {key}: {value}")
        else:
            print("❌ No Lisa Wagner found on staging")
            
    except Exception as e:
        print(f"❌ Error querying Lisa: {e}")

def check_tennaqua_teams():
    """Check all Tennaqua teams"""
    print("\n🔍 Checking all Tennaqua teams...")
    
    query = """
    SELECT t.id, t.team_name, t.display_name, 
           COUNT(p.id) as player_count,
           s.name as series_name
    FROM teams t
    LEFT JOIN players p ON t.id = p.team_id
    JOIN clubs c ON t.club_id = c.id
    JOIN series s ON t.series_id = s.id
    WHERE c.name = 'Tennaqua' 
    AND t.league_id = (SELECT id FROM leagues WHERE league_id = 'CNSWPL')
    GROUP BY t.id, t.team_name, t.display_name, s.name
    ORDER BY t.team_name
    """
    
    try:
        results = execute_query(query)
        
        print("STAGING - Tennaqua teams:")
        for row in results:
            print(f"  Team ID {row['id']}: {row['team_name']} ({row['display_name']}) - {row['player_count']} players - Series: {row['series_name']}")
            
    except Exception as e:
        print(f"❌ Error querying teams: {e}")

def check_series_12_players():
    """Check all players in Series 12"""
    print("\n🔍 Checking all Tennaqua Series 12 players...")
    
    query = """
    SELECT p.first_name, p.last_name, t.team_name, t.display_name
    FROM players p 
    JOIN teams t ON p.team_id = t.id
    JOIN clubs c ON t.club_id = c.id
    JOIN series s ON t.series_id = s.id
    WHERE c.name = 'Tennaqua' 
    AND s.name = 'Series 12'
    AND t.league_id = (SELECT id FROM leagues WHERE league_id = 'CNSWPL')
    ORDER BY p.first_name, p.last_name
    """
    
    try:
        results = execute_query(query)
        
        print(f"STAGING - Tennaqua Series 12 players ({len(results)} total):")
        for row in results:
            print(f"  {row['first_name']} {row['last_name']} - {row['team_name']}")
            
    except Exception as e:
        print(f"❌ Error querying Series 12 players: {e}")

if __name__ == "__main__":
    check_lisa_wagner()
    check_tennaqua_teams() 
    check_series_12_players()
