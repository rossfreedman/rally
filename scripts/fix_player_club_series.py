#!/usr/bin/env python3

"""
Fix Player Club and Series IDs

This script updates the club_id and series_id for a specific player
in both the players table and player_leagues table (if it exists).
"""

import os
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one, execute_update

def fix_player_club_series(player_id='nndz-WkMrK3didjlnUT09', club_name='Tennaqua', series_name='Chicago 22'):
    """Fix club_id and series_id for a specific player."""
    print(f"🔄 Fixing club and series for player: {player_id}")
    
    try:
        # 1. Get player info
        player_query = """
            SELECT id, first_name, last_name, club_id, series_id, league_id
            FROM players
            WHERE tenniscores_player_id = %s
        """
        player = execute_query_one(player_query, [player_id])
        
        if not player:
            print(f"❌ Player not found with ID: {player_id}")
            return False
            
        print(f"✅ Found player: {player['first_name']} {player['last_name']}")
        print(f"   Current club_id: {player['club_id']}")
        print(f"   Current series_id: {player['series_id']}")
        
        # 2. Get club ID
        club_query = "SELECT id FROM clubs WHERE name ILIKE %s"
        club = execute_query_one(club_query, [f"%{club_name}%"])
        
        if not club:
            print(f"❌ Club not found: {club_name}")
            return False
            
        club_id = club['id']
        print(f"✅ Found club_id: {club_id}")
        
        # 3. Get series ID
        series_query = "SELECT id FROM series WHERE name ILIKE %s"
        series = execute_query_one(series_query, [f"%{series_name}%"])
        
        if not series:
            print(f"❌ Series not found: {series_name}")
            return False
            
        series_id = series['id']
        print(f"✅ Found series_id: {series_id}")
        
        # 4. Update players table
        update_player_query = """
            UPDATE players
            SET club_id = %s, series_id = %s
            WHERE tenniscores_player_id = %s
        """
        execute_update(update_player_query, [club_id, series_id, player_id])
        print("✅ Updated players table")
        
        # 5. Check if player_leagues table exists
        check_table_query = """
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_name = 'player_leagues'
            )
        """
        has_player_leagues = execute_query_one(check_table_query)['exists']
        
        if has_player_leagues:
            print("✅ Found player_leagues table")
            
            # Check if player already has a row
            check_row_query = """
                SELECT id FROM player_leagues 
                WHERE player_id = %s AND league_id = %s
            """
            existing_row = execute_query_one(check_row_query, [player['id'], player['league_id']])
            
            if existing_row:
                # Update existing row
                update_leagues_query = """
                    UPDATE player_leagues
                    SET club_id = %s, series_id = %s, is_active = true
                    WHERE player_id = %s AND league_id = %s
                """
                execute_update(update_leagues_query, [club_id, series_id, player['id'], player['league_id']])
                print("✅ Updated player_leagues table")
            else:
                # Insert new row
                insert_leagues_query = """
                    INSERT INTO player_leagues (player_id, league_id, club_id, series_id, is_active)
                    VALUES (%s, %s, %s, %s, true)
                """
                execute_update(insert_leagues_query, [player['id'], player['league_id'], club_id, series_id])
                print("✅ Inserted new row in player_leagues table")
        
        # 6. Verify the updates
        verify_query = """
            SELECT 
                p.first_name,
                p.last_name,
                p.club_id,
                p.series_id,
                c.name as club_name,
                s.name as series_name
            FROM players p
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.tenniscores_player_id = %s
        """
        result = execute_query_one(verify_query, [player_id])
        
        print("\n📊 Final Result:")
        print(f"   Player: {result['first_name']} {result['last_name']}")
        print(f"   Club: {result['club_name']} (ID: {result['club_id']})")
        print(f"   Series: {result['series_name']} (ID: {result['series_id']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    # You can override these defaults when calling the script
    PLAYER_ID = 'nndz-WkMrK3didjlnUT09'  # Your player ID
    CLUB_NAME = 'Tennaqua'                # Your club
    SERIES_NAME = 'Chicago 22'            # Your series
    
    success = fix_player_club_series(PLAYER_ID, CLUB_NAME, SERIES_NAME)
    if success:
        print("\n🎉 Successfully updated player club and series!")
        print("   Log out and back in to see the changes.")
    else:
        print("\n❌ Failed to update player club and series.")
        print("   Check the error messages above.") 