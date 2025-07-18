#!/usr/bin/env python3
"""
Create a test pickup game that Ross would match
This will help test if pickup games notifications work for Ross
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db
from datetime import datetime, timedelta

def create_test_pickup_game_for_ross():
    """Create a pickup game that Ross would match"""
    
    print("=== Creating Test Pickup Game for Ross ===")
    
    try:
        # Get database connection
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 1. Find Ross's user record and PTI
            print("\n1. Finding Ross's PTI...")
            cursor.execute("""
                SELECT id, email, first_name, last_name, tenniscores_player_id
                FROM users 
                WHERE first_name ILIKE '%ross%' OR email ILIKE '%ross%'
                ORDER BY id DESC
                LIMIT 1
            """)
            
            ross_user = cursor.fetchone()
            if not ross_user:
                print("❌ No user found with name containing 'Ross'")
                return False
            
            user_id = ross_user[0]
            player_id = ross_user[4]
            
            # Get Ross's highest PTI
            cursor.execute("""
                SELECT MAX(p.pti) as max_pti
                FROM user_player_associations upa
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                WHERE upa.user_id = %s AND p.pti IS NOT NULL
            """, [user_id])
            
            result = cursor.fetchone()
            ross_pti = result[0] if result and result[0] else 50.0
            
            print(f"✅ Ross's PTI: {ross_pti}")
            
            # 2. Create a pickup game that Ross would match
            print("\n2. Creating pickup game for Ross...")
            
            # Game date: tomorrow
            game_date = datetime.now().date() + timedelta(days=1)
            game_time = datetime.strptime("19:00:00", "%H:%M:%S").time()
            
            # PTI range: Ross's PTI ± 5
            pti_low = max(0, ross_pti - 5)
            pti_high = ross_pti + 5
            
            # Description
            description = f"Test pickup game for Ross (PTI {ross_pti}) - {game_date.strftime('%A, %b %d')} at {game_time.strftime('%I:%M %p')}"
            
            cursor.execute("""
                INSERT INTO pickup_games (
                    description, game_date, game_time, players_requested,
                    pti_low, pti_high, series_low, series_high, club_only,
                    creator_user_id, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, [
                description, game_date, game_time, 4,
                pti_low, pti_high, None, None, False,  # Not club-only, no series restrictions
                user_id, datetime.now()
            ])
            
            game_id = cursor.fetchone()[0]
            conn.commit()
            
            print(f"✅ Created pickup game ID: {game_id}")
            print(f"   Description: {description}")
            print(f"   Date: {game_date}, Time: {game_time}")
            print(f"   PTI Range: {pti_low}-{pti_high} (Ross's PTI: {ross_pti})")
            print(f"   Players: 4, Club Only: False")
            
            # 3. Verify the game was created
            print("\n3. Verifying game creation...")
            cursor.execute("""
                SELECT 
                    id, description, game_date, game_time, players_requested,
                    pti_low, pti_high, series_low, series_high, club_only
                FROM pickup_games
                WHERE id = %s
            """, [game_id])
            
            game = cursor.fetchone()
            if game:
                print(f"✅ Game verified in database")
                print(f"   - ID: {game[0]}")
                print(f"   - Description: {game[1]}")
                print(f"   - PTI Range: {game[5]}-{game[6]}")
            else:
                print(f"❌ Game not found in database")
                return False
            
            # 4. Test if Ross matches this game
            print("\n4. Testing if Ross matches this game...")
            
            # Check PTI match
            pti_match = pti_low <= ross_pti <= pti_high
            print(f"   PTI Match: {pti_match} (Ross PTI: {ross_pti}, Range: {pti_low}-{pti_high})")
            
            # Check if already joined
            cursor.execute("""
                SELECT COUNT(*) FROM pickup_game_participants 
                WHERE pickup_game_id = %s AND user_id = %s
            """, [game_id, user_id])
            
            already_joined = cursor.fetchone()[0] > 0
            print(f"   Already Joined: {already_joined}")
            
            # Check open slots
            cursor.execute("""
                SELECT COUNT(*) FROM pickup_game_participants 
                WHERE pickup_game_id = %s
            """, [game_id])
            
            current_participants = cursor.fetchone()[0]
            has_open_slots = current_participants < 4
            print(f"   Open Slots: {has_open_slots} ({current_participants}/4)")
            
            if pti_match and not already_joined and has_open_slots:
                print(f"   ✅ Ross matches this game!")
                print(f"   - Should see pickup games notification on home page")
            else:
                print(f"   ❌ Ross doesn't match this game")
            
            # 5. Test the pickup games notifications function
            print("\n5. Testing pickup games notifications function...")
            
            # Import the function
            from app.routes.api_routes import get_pickup_games_notifications
            
            notifications = get_pickup_games_notifications(user_id, player_id, None, None)
            
            print(f"   Function returned {len(notifications)} notifications")
            for i, notification in enumerate(notifications):
                print(f"   {i+1}. {notification.get('title')} - {notification.get('message')}")
                print(f"      Priority: {notification.get('priority')}")
            
            if notifications:
                print(f"   ✅ Function is working and returning notifications for Ross")
                print(f"   - Pickup games notifications should now appear on the home page")
            else:
                print(f"   ❌ Function is still not returning notifications for Ross")
                print(f"   - There might be another issue with the function")
            
            cursor.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating test pickup game: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_test_pickup_game_for_ross()
    
    if success:
        print("\n✅ Test pickup game created successfully!")
        print("   - Ross should now see pickup games notifications on the home page")
        print("   - Log in and check /mobile to verify")
    else:
        print("\n❌ Failed to create test pickup game") 