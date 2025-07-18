#!/usr/bin/env python3
"""
Script to debug Ross's session data and fix the team_id issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db
from app.services.session_service import get_session_data_for_user

def debug_ross_session():
    print("=== Debugging Ross's Session Data ===\n")
    
    user_email = "rossfreedman@gmail.com"  # Ross's email
    
    print(f"1. Ross's email: {user_email}")
    
    # Get Ross's session data
    try:
        session_data = get_session_data_for_user(user_email)
        
        print(f"\n2. Current session data:")
        print(f"   - User ID: {session_data.get('id')}")
        print(f"   - Email: {session_data.get('email')}")
        print(f"   - Name: {session_data.get('first_name')} {session_data.get('last_name')}")
        print(f"   - Player ID: {session_data.get('tenniscores_player_id')}")
        print(f"   - League ID: {session_data.get('league_id')}")
        print(f"   - Team ID: {session_data.get('team_id')}")
        print(f"   - Club: {session_data.get('club')}")
        print(f"   - Series: {session_data.get('series')}")
        
        # Check if team_id is correct
        current_team_id = session_data.get('team_id')
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Check if the current team_id exists
            if current_team_id:
                team_check_query = """
                    SELECT 
                        t.id,
                        t.team_name,
                        s.name as series_name,
                        c.name as club_name
                    FROM teams t
                    LEFT JOIN series s ON t.series_id = s.id
                    LEFT JOIN clubs c ON t.club_id = c.id
                    WHERE t.id = %s
                """
                
                cursor.execute(team_check_query, [current_team_id])
                team_info = cursor.fetchone()
                
                if team_info:
                    print(f"\n3. Current team info (ID: {current_team_id}):")
                    print(f"   - Team Name: {team_info[1]}")
                    print(f"   - Series: {team_info[2]}")
                    print(f"   - Club: {team_info[3]}")
                else:
                    print(f"\n3. ❌ Current team ID {current_team_id} does not exist in database")
            
            # Find the correct team for Chicago 22
            correct_team_query = """
                SELECT 
                    t.id,
                    t.team_name,
                    s.name as series_name,
                    c.name as club_name
                FROM teams t
                LEFT JOIN series s ON t.series_id = s.id
                LEFT JOIN clubs c ON t.club_id = c.id
                WHERE s.name = 'Chicago 22' AND c.name = 'Tennaqua'
                LIMIT 1
            """
            
            cursor.execute(correct_team_query)
            correct_team = cursor.fetchone()
            
            if correct_team:
                print(f"\n4. Correct team for Chicago 22:")
                print(f"   - Team ID: {correct_team[0]}")
                print(f"   - Team Name: {correct_team[1]}")
                print(f"   - Series: {correct_team[2]}")
                print(f"   - Club: {correct_team[3]}")
                
                # Check if Ross has a player record for Chicago 22
                player_check_query = """
                    SELECT 
                        p.id,
                        p.tenniscores_player_id,
                        p.pti,
                        p.series_id,
                        p.team_id,
                        s.name as series_name,
                        t.team_name
                    FROM players p
                    LEFT JOIN series s ON p.series_id = s.id
                    LEFT JOIN teams t ON p.team_id = t.id
                    WHERE p.tenniscores_player_id = %s AND s.name = 'Chicago 22'
                """
                
                cursor.execute(player_check_query, [session_data.get('tenniscores_player_id')])
                chicago_player = cursor.fetchone()
                
                if chicago_player:
                    print(f"\n5. Ross's Chicago 22 player record:")
                    print(f"   - Player ID: {chicago_player[1]}")
                    print(f"   - PTI: {chicago_player[2]}")
                    print(f"   - Series: {chicago_player[5]} (ID: {chicago_player[3]})")
                    print(f"   - Team: {chicago_player[6]} (ID: {chicago_player[4]})")
                    
                    if chicago_player[4] != correct_team[0]:
                        print(f"   ⚠️  Team ID mismatch: Player has {chicago_player[4]}, should be {correct_team[0]}")
                    else:
                        print(f"   ✅ Team ID matches: {chicago_player[4]}")
                else:
                    print(f"\n5. ❌ No Chicago 22 player record found for Ross")
            else:
                print(f"\n4. ❌ No team found for Chicago 22 and Tennaqua")
        
    except Exception as e:
        print(f"❌ Error getting session data: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Debug completed")

if __name__ == "__main__":
    debug_ross_session() 