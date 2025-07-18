#!/usr/bin/env python3
"""
Debug script for Ross's pickup games notifications
Checks why pickup games notifications aren't showing for Ross specifically
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db
from datetime import datetime

def debug_ross_pickup_games():
    """Debug pickup games notifications for Ross specifically"""
    
    print("=== Debugging Ross's Pickup Games Notifications ===")
    
    try:
        # Get database connection
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 1. Find Ross's user record
            print("\n1. Finding Ross's user record...")
            cursor.execute("""
                SELECT id, email, first_name, last_name, tenniscores_player_id, league_id
                FROM users 
                WHERE first_name ILIKE '%ross%' OR email ILIKE '%ross%'
                ORDER BY id DESC
            """)
            
            ross_users = cursor.fetchall()
            if not ross_users:
                print("❌ No user found with name containing 'Ross'")
                return False
                
            print(f"✅ Found {len(ross_users)} user(s) with 'Ross' in name:")
            for user in ross_users:
                print(f"   - ID: {user[0]}, Email: {user[1]}, Name: {user[2]} {user[3]}")
                print(f"     Player ID: {user[4]}, League: {user[5]}")
            
            # Use the first Ross user
            ross_user = ross_users[0]
            user_id = ross_user[0]
            player_id = ross_user[4]
            
            print(f"\n2. Using Ross user ID: {user_id}, Player ID: {player_id}")
            
            # 2. Check Ross's player associations and PTI
            print("\n3. Checking Ross's player associations and PTI...")
            cursor.execute("""
                SELECT 
                    upa.tenniscores_player_id,
                    p.pti,
                    p.series_id,
                    s.name as series_name,
                    c.name as club_name,
                    t.team_name
                FROM user_player_associations upa
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                LEFT JOIN series s ON p.series_id = s.id
                LEFT JOIN clubs c ON p.club_id = c.id
                LEFT JOIN teams t ON p.team_id = t.id
                WHERE upa.user_id = %s
                ORDER BY p.pti DESC
            """, [user_id])
            
            associations = cursor.fetchall()
            if not associations:
                print("❌ No player associations found for Ross")
                return False
                
            print(f"✅ Found {len(associations)} player associations:")
            for assoc in associations:
                print(f"   - Player ID: {assoc[0]}")
                print(f"     PTI: {assoc[1]}")
                print(f"     Series: {assoc[3]} (ID: {assoc[2]})")
                print(f"     Club: {assoc[4]}")
                print(f"     Team: {assoc[5]}")
            
            # Get Ross's highest PTI
            highest_pti = max([assoc[1] for assoc in associations if assoc[1] is not None])
            print(f"\n4. Ross's highest PTI: {highest_pti}")
            
            # 3. Check current pickup games
            print("\n5. Checking current pickup games...")
            cursor.execute("""
                SELECT 
                    id,
                    description,
                    game_date,
                    game_time,
                    players_requested,
                    pti_low,
                    pti_high,
                    series_low,
                    series_high,
                    club_only,
                    created_at
                FROM pickup_games
                WHERE ((game_date > CURRENT_DATE) OR (game_date = CURRENT_DATE AND game_time > CURRENT_TIME))
                ORDER BY game_date ASC, game_time ASC
            """)
            
            pickup_games = cursor.fetchall()
            print(f"✅ Found {len(pickup_games)} future pickup games:")
            
            matching_games = []
            for game in pickup_games:
                game_id, description, game_date, game_time, players_requested, pti_low, pti_high, series_low, series_high, club_only, created_at = game
                
                print(f"\n   Game {game_id}: {description}")
                print(f"     Date: {game_date}, Time: {game_time}")
                print(f"     PTI Range: {pti_low}-{pti_high}, Players: {players_requested}")
                print(f"     Series Range: {series_low}-{series_high}, Club Only: {club_only}")
                
                # Check if Ross matches this game
                pti_match = pti_low <= highest_pti <= pti_high if pti_low is not None and pti_high is not None else False
                series_match = True  # Assume match for now, would need more complex logic
                
                # Check if Ross has already joined
                cursor.execute("""
                    SELECT COUNT(*) FROM pickup_game_participants 
                    WHERE pickup_game_id = %s AND user_id = %s
                """, [game_id, user_id])
                
                already_joined = cursor.fetchone()[0] > 0
                
                # Check current participants
                cursor.execute("""
                    SELECT COUNT(*) FROM pickup_game_participants 
                    WHERE pickup_game_id = %s
                """, [game_id])
                
                current_participants = cursor.fetchone()[0]
                has_open_slots = current_participants < players_requested
                
                print(f"     PTI Match: {pti_match} (Ross PTI: {highest_pti}, Range: {pti_low}-{pti_high})")
                print(f"     Already Joined: {already_joined}")
                print(f"     Open Slots: {has_open_slots} ({current_participants}/{players_requested})")
                
                if pti_match and not already_joined and has_open_slots:
                    matching_games.append(game)
                    print(f"     ✅ MATCHES ROSS'S CRITERIA")
                else:
                    print(f"     ❌ Does not match Ross's criteria")
            
            print(f"\n6. Summary:")
            print(f"   - Ross's PTI: {highest_pti}")
            print(f"   - Future pickup games: {len(pickup_games)}")
            print(f"   - Games matching Ross's criteria: {len(matching_games)}")
            
            if matching_games:
                print(f"   ✅ Ross should see {len(matching_games)} pickup games notifications")
                print(f"   - If notifications aren't showing, check the API response")
            else:
                print(f"   ❌ Ross doesn't match any pickup games criteria")
                print(f"   - This explains why no pickup games notifications are showing")
            
            # 4. Test the pickup games notifications function for Ross
            print(f"\n7. Testing pickup games notifications function for Ross...")
            
            # Import the function
            from app.routes.api_routes import get_pickup_games_notifications
            
            notifications = get_pickup_games_notifications(user_id, player_id, ross_user[5], None)
            
            print(f"   Function returned {len(notifications)} notifications")
            for i, notification in enumerate(notifications):
                print(f"   {i+1}. {notification.get('title')} - {notification.get('message')}")
                print(f"      Priority: {notification.get('priority')}")
            
            if notifications:
                print(f"   ✅ Function is working and returning notifications for Ross")
            else:
                print(f"   ❌ Function is not returning notifications for Ross")
                print(f"   - This explains why no pickup games notifications appear on the home page")
            
            cursor.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error debugging Ross's pickup games: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_ross_pickup_games()
    
    if success:
        print("\n✅ Debug completed - check the summary above")
    else:
        print("\n❌ Debug failed - check the error messages above") 