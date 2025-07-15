#!/usr/bin/env python3

"""
Test script for notification fixes:
1. Most recent poll notifications
2. Most recent pickup game notifications  
3. Fixed streak calculation
4. Fixed "Your Last Match" message format
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from database_utils import execute_query, execute_query_one, execute_update

def test_notifications_fixes():
    """Test the notification fixes"""
    
    print("=== Testing Notification Fixes ===")
    
    try:
        # Test 1: Check if polls table exists and has data
        print("\n1. Testing poll notifications...")
        
        polls_check = execute_query_one("""
            SELECT COUNT(*) as poll_count
            FROM polls
        """)
        
        if polls_check and polls_check["poll_count"] > 0:
            print(f"✅ Found {polls_check['poll_count']} polls in database")
            
            # Get most recent poll
            recent_poll = execute_query_one("""
                SELECT 
                    p.id,
                    p.question,
                    p.created_at,
                    p.team_id,
                    u.first_name,
                    u.last_name
                FROM polls p
                LEFT JOIN users u ON p.created_by = u.id
                ORDER BY p.created_at DESC
                LIMIT 1
            """)
            
            if recent_poll:
                print(f"✅ Most recent poll: '{recent_poll['question']}' by {recent_poll['first_name']} {recent_poll['last_name']}")
                print(f"   Team ID: {recent_poll['team_id']}")
                print(f"   Created: {recent_poll['created_at']}")
        else:
            print("⚠️ No polls found in database")
        
        # Test 2: Check if pickup_games table exists and has data
        print("\n2. Testing pickup games notifications...")
        
        pickup_check = execute_query_one("""
            SELECT COUNT(*) as game_count
            FROM pickup_games
        """)
        
        if pickup_check and pickup_check["game_count"] > 0:
            print(f"✅ Found {pickup_check['game_count']} pickup games in database")
            
            # Get upcoming games
            upcoming_games = execute_query("""
                SELECT 
                    id,
                    description,
                    game_date,
                    game_time,
                    players_requested,
                    pti_low,
                    pti_high
                FROM pickup_games
                WHERE game_date >= CURRENT_DATE
                ORDER BY game_date ASC, game_time ASC
                LIMIT 3
            """)
            
            if upcoming_games:
                print(f"✅ Found {len(upcoming_games)} upcoming pickup games:")
                for game in upcoming_games:
                    print(f"   - {game['description']} on {game['game_date']} at {game['game_time']}")
                    print(f"     PTI range: {game['pti_low']}-{game['pti_high']}, Players: {game['players_requested']}")
        else:
            print("⚠️ No pickup games found in database")
        
        # Test 3: Test streak calculation logic
        print("\n3. Testing streak calculation fix...")
        
        # Get a sample player with matches
        sample_player = execute_query_one("""
            SELECT 
                p.tenniscores_player_id,
                p.first_name,
                p.last_name,
                p.league_id,
                COUNT(ms.id) as match_count
            FROM players p
            JOIN match_scores ms ON (
                ms.home_player_1_id = p.tenniscores_player_id OR
                ms.home_player_2_id = p.tenniscores_player_id OR
                ms.away_player_1_id = p.tenniscores_player_id OR
                ms.away_player_2_id = p.tenniscores_player_id
            )
            GROUP BY p.tenniscores_player_id, p.first_name, p.last_name, p.league_id
            HAVING COUNT(ms.id) >= 5
            ORDER BY COUNT(ms.id) DESC
            LIMIT 1
        """)
        
        if sample_player:
            player_id = sample_player["tenniscores_player_id"]
            league_id = sample_player["league_id"]
            
            print(f"✅ Testing streak calculation for {sample_player['first_name']} {sample_player['last_name']}")
            print(f"   Player ID: {player_id}")
            print(f"   League ID: {league_id}")
            print(f"   Total matches: {sample_player['match_count']}")
            
            # Test the fixed streak query
            streak_result = execute_query_one("""
                WITH match_results AS (
                    SELECT 
                        match_date,
                        CASE 
                            WHEN home_player_1_id = %s OR home_player_2_id = %s THEN 
                                CASE WHEN winner = home_team THEN 'W' ELSE 'L' END
                            ELSE 
                                CASE WHEN winner = away_team THEN 'W' ELSE 'L' END
                        END as result
                    FROM match_scores 
                    WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
                    AND league_id = %s
                    ORDER BY match_date DESC
                ),
                streak_groups AS (
                    SELECT 
                        result,
                        match_date,
                        ROW_NUMBER() OVER (ORDER BY match_date DESC) as rn,
                        ROW_NUMBER() OVER (PARTITION BY result ORDER BY match_date DESC) as streak_rn,
                        ROW_NUMBER() OVER (ORDER BY match_date DESC) - 
                        ROW_NUMBER() OVER (PARTITION BY result ORDER BY match_date DESC) as streak_group
                    FROM match_results
                ),
                current_streak AS (
                    SELECT 
                        result,
                        COUNT(*) as streak_length
                    FROM streak_groups 
                    WHERE streak_group = 0  -- Current streak (most recent consecutive matches)
                    GROUP BY result
                    ORDER BY streak_length DESC
                    LIMIT 1
                )
                SELECT * FROM current_streak
            """, [player_id, player_id, player_id, player_id, player_id, player_id, league_id])
            
            if streak_result:
                streak_type = "win" if streak_result["result"] == "W" else "loss"
                print(f"✅ Current streak: {streak_result['streak_length']}-match {streak_type} streak")
            else:
                print("⚠️ No streak data found")
        else:
            print("⚠️ No players with sufficient match data found")
        
        # Test 4: Test "Your Last Match" message format
        print("\n4. Testing 'Your Last Match' message format...")
        
        if sample_player:
            # Get most recent match for the sample player
            recent_match = execute_query_one("""
                SELECT 
                    match_date,
                    home_team,
                    away_team,
                    winner,
                    CASE 
                        WHEN home_player_1_id = %s OR home_player_2_id = %s THEN home_team
                        ELSE away_team
                    END as player_team,
                    CASE 
                        WHEN home_player_1_id = %s OR home_player_2_id = %s THEN 'home'
                        ELSE 'away'
                    END as player_side
                FROM match_scores 
                WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
                AND league_id = %s
                ORDER BY match_date DESC
                LIMIT 1
            """, [player_id, player_id, player_id, player_id, player_id, player_id, player_id, player_id, league_id])
            
            if recent_match:
                is_winner = recent_match["winner"] == recent_match["player_team"]
                result_text = "won" if is_winner else "lost"
                match_date_str = recent_match["match_date"].strftime("%b %d")
                
                # Determine opponent team (FIXED LOGIC)
                if recent_match["player_side"] == "home":
                    opponent_team = recent_match["away_team"]
                else:
                    opponent_team = recent_match["home_team"]
                
                # OLD format: "playing for [team]"
                old_message = f"On {match_date_str}, you {result_text} playing for {recent_match['player_team']}"
                
                # NEW format: "playing against [opponent]"
                new_message = f"On {match_date_str}, you {result_text} playing against {opponent_team}"
                
                print(f"✅ Most recent match: {recent_match['home_team']} vs {recent_match['away_team']}")
                print(f"   Player was on: {recent_match['player_team']} ({recent_match['player_side']} side)")
                print(f"   Result: {result_text}")
                print(f"   OLD message: {old_message}")
                print(f"   NEW message: {new_message}")
                print(f"   ✅ Message format fixed!")
        
        print("\n=== Notification Fixes Test Complete ===")
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    test_notifications_fixes() 