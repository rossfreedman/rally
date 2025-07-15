#!/usr/bin/env python3

"""
Test script for pickup games notifications debugging
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from database_utils import execute_query, execute_query_one

def test_pickup_games_notifications():
    """Test pickup games notifications function"""
    
    print("=== Testing Pickup Games Notifications ===")
    
    try:
        # Test 1: Check pickup games table
        print("\n1. Checking pickup games table...")
        
        games_check = execute_query_one("""
            SELECT COUNT(*) as game_count
            FROM pickup_games
        """)
        
        game_count = games_check["game_count"] if games_check else 0
        print(f"   Found {game_count} pickup games in database")
        
        if game_count == 0:
            print("   ❌ No pickup games found - create some games first")
            return False
        
        # Test 2: Check recent pickup games
        print("\n2. Checking recent pickup games...")
        
        recent_games = execute_query("""
            SELECT 
                id, description, game_date, game_time, 
                players_requested, pti_low, pti_high,
                created_at
            FROM pickup_games
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        for game in recent_games:
            print(f"   Game {game['id']}: {game['description'][:50]}...")
            print(f"     Date: {game['game_date']}, Time: {game['game_time']}")
            print(f"     PTI Range: {game['pti_low']}-{game['pti_high']}, Players: {game['players_requested']}")
            print(f"     Created: {game['created_at']}")
            print()
        
        # Test 3: Check if any games are in the future
        now = datetime.now()
        current_date = now.date()
        current_time = now.time()
        
        print(f"3. Current date/time: {current_date} {current_time}")
        
        future_games = execute_query("""
            SELECT COUNT(*) as future_count
            FROM pickup_games
            WHERE (game_date > %s) OR (game_date = %s AND game_time > %s)
        """, [current_date, current_date, current_time])
        
        future_count = future_games[0]["future_count"] if future_games else 0
        print(f"   Found {future_count} future pickup games")
        
        if future_count == 0:
            print("   ❌ No future pickup games found - all games are in the past")
            print("   💡 Solution: Create pickup games with future dates")
            return False
        
        # Test 4: Test with a specific user
        print("\n4. Testing with specific user...")
        
        # Get a user with player data
        user_result = execute_query_one("""
            SELECT 
                u.id as user_id,
                u.email,
                p.tenniscores_player_id,
                p.pti,
                p.series_id,
                p.club_id
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            WHERE p.pti IS NOT NULL
            LIMIT 1
        """)
        
        if not user_result:
            print("   ❌ No users with PTI data found")
            return False
        
        user_id = user_result["user_id"]
        player_id = user_result["tenniscores_player_id"]
        user_pti = user_result["pti"]
        
        print(f"   Testing with user {user_id} ({user_result['email']})")
        print(f"   Player ID: {player_id}")
        print(f"   User PTI: {user_pti}")
        
        # Test 5: Import and test the function
        print("\n5. Testing pickup games notifications function...")
        
        from app.routes.api_routes import get_pickup_games_notifications
        
        # Test with dummy parameters (we'll use the user's actual data)
        notifications = get_pickup_games_notifications(
            user_id=user_id,
            player_id=player_id,
            league_id=1,  # Dummy league ID
            team_id=1     # Dummy team ID
        )
        
        print(f"   Function returned {len(notifications)} notifications")
        
        for i, notification in enumerate(notifications):
            print(f"   Notification {i+1}:")
            print(f"     Title: {notification['title']}")
            print(f"     Message: {notification['message']}")
            print(f"     CTA: {notification['cta']}")
            print()
        
        # Test 6: Check what games the user should see
        print("\n6. Checking what games user should see...")
        
        user_games_query = """
            SELECT 
                pg.id,
                pg.description,
                pg.game_date,
                pg.game_time,
                pg.players_requested,
                pg.pti_low,
                pg.pti_high,
                pg.series_low,
                pg.series_high,
                pg.club_only,
                COUNT(pgp.id) as current_participants
            FROM pickup_games pg
            LEFT JOIN pickup_game_participants pgp ON pg.id = pgp.pickup_game_id
            WHERE (pg.game_date > %s) OR (pg.game_date = %s AND pg.game_time > %s)
            AND pg.pti_low <= %s AND pg.pti_high >= %s
            GROUP BY pg.id
            HAVING COUNT(pgp.id) < pg.players_requested
            ORDER BY pg.game_date ASC, pg.game_time ASC
        """
        
        user_games = execute_query(user_games_query, [
            current_date, current_date, current_time,
            user_pti, user_pti
        ])
        
        print(f"   User should see {len(user_games)} games based on PTI criteria")
        
        for game in user_games:
            print(f"     Game {game['id']}: {game['description'][:50]}...")
            print(f"       PTI: {game['pti_low']}-{game['pti_high']}, User PTI: {user_pti}")
            print(f"       Participants: {game['current_participants']}/{game['players_requested']}")
            print()
        
        return len(notifications) > 0
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pickup_games_notifications()
    if success:
        print("\n✅ Pickup games notifications are working!")
    else:
        print("\n❌ Pickup games notifications need fixing") 