#!/usr/bin/env python3
"""
Comprehensive player access test for nndz-WkMrK3didjlnUT09
Tests actual application-level access to schedule and team data, not just database relationships.
"""

import sys
import os
from datetime import datetime, date

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_config import get_db

PROBLEM_PLAYER_ID = "nndz-WkMrK3didjlnUT09"

def test_player_application_access():
    """Test actual application-level access to player data"""
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        print(f"🧪 COMPREHENSIVE ACCESS TEST FOR: {PROBLEM_PLAYER_ID}")
        print("=" * 80)
        
        # Test 1: Basic player lookup
        print("\n1. BASIC PLAYER LOOKUP TEST")
        print("-" * 50)
        
        cursor.execute("""
            SELECT p.id, p.first_name, p.last_name, p.tenniscores_player_id,
                   p.is_active, p.team_id,
                   l.league_id, l.league_name,
                   c.name as club_name,
                   s.name as series_name,
                   t.team_name
            FROM players p
            JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE p.tenniscores_player_id = %s AND p.is_active = true
        """, [PROBLEM_PLAYER_ID])
        
        player_records = cursor.fetchall()
        
        if not player_records:
            print("❌ CRITICAL: No active player records found!")
            return
        
        print(f"✅ Found {len(player_records)} active player record(s)")
        for i, record in enumerate(player_records, 1):
            (player_id, first_name, last_name, tenniscores_id, is_active, team_id,
             league_id, league_name, club_name, series_name, team_name) = record
            
            print(f"\nRecord {i}: {first_name} {last_name}")
            print(f"  - Player DB ID: {player_id}")
            print(f"  - League: {league_name} ({league_id})")
            print(f"  - Club: {club_name}")
            print(f"  - Series: {series_name}")
            print(f"  - Team: {team_name} (ID: {team_id})")
            print(f"  - Active: {is_active}")
        
        # Test 2: User session context test
        print("\n\n2. USER SESSION CONTEXT TEST")
        print("-" * 50)
        
        cursor.execute("""
            SELECT u.id, u.first_name, u.last_name, u.email,
                   u.league_context,
                   l.league_id as context_league_id,
                   l.league_name as context_league_name,
                   upa.is_primary
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
            LEFT JOIN leagues l ON u.league_context = l.id
            WHERE upa.tenniscores_player_id = %s
        """, [PROBLEM_PLAYER_ID])
        
        user_data = cursor.fetchall()
        
        if not user_data:
            print("❌ CRITICAL: No user associations found!")
            return
        
        for user_record in user_data:
            (user_id, first_name, last_name, email, league_context,
             context_league_id, context_league_name, is_primary) = user_record
            
            print(f"User: {first_name} {last_name} ({email})")
            print(f"  - User ID: {user_id}")
            print(f"  - League Context: {context_league_name} ({context_league_id})")
            print(f"  - Primary Association: {is_primary}")
        
        # Test 3: Schedule access simulation
        print("\n\n3. SCHEDULE ACCESS SIMULATION")
        print("-" * 50)
        
        # Simulate the query that the availability page would use
        cursor.execute("""
            SELECT s.id, s.match_date, s.match_time, s.home_team, s.away_team,
                   s.location, l.league_name,
                   CASE 
                       WHEN s.home_team IN (
                           SELECT DISTINCT COALESCE(ms.home_team, ms.away_team)
                           FROM match_scores ms
                           WHERE ms.home_player_1_id = %s OR ms.home_player_2_id = %s 
                              OR ms.away_player_1_id = %s OR ms.away_player_2_id = %s
                       ) OR s.away_team IN (
                           SELECT DISTINCT COALESCE(ms.home_team, ms.away_team)
                           FROM match_scores ms
                           WHERE ms.home_player_1_id = %s OR ms.home_player_2_id = %s 
                              OR ms.away_player_1_id = %s OR ms.away_player_2_id = %s
                       ) THEN 'PLAYER_TEAM'
                       ELSE 'OTHER_TEAM'
                   END as team_relevance
            FROM schedule s
            JOIN leagues l ON s.league_id = l.id
            WHERE s.match_date >= CURRENT_DATE - INTERVAL '30 days'
            AND (
                s.home_team IN (
                    SELECT DISTINCT COALESCE(ms.home_team, ms.away_team)
                    FROM match_scores ms
                    WHERE ms.home_player_1_id = %s OR ms.home_player_2_id = %s 
                       OR ms.away_player_1_id = %s OR ms.away_player_2_id = %s
                ) OR s.away_team IN (
                    SELECT DISTINCT COALESCE(ms.home_team, ms.away_team)
                    FROM match_scores ms
                    WHERE ms.home_player_1_id = %s OR ms.home_player_2_id = %s 
                       OR ms.away_player_1_id = %s OR ms.away_player_2_id = %s
                )
            )
            ORDER BY s.match_date DESC
            LIMIT 10
        """, [PROBLEM_PLAYER_ID] * 16)
        
        schedule_data = cursor.fetchall()
        
        if not schedule_data:
            print("❌ CRITICAL: No schedule data found for player's teams!")
            print("\nDEBUG: Let's check what teams the player has played for...")
            
            cursor.execute("""
                SELECT DISTINCT 
                    CASE 
                        WHEN ms.home_player_1_id = %s OR ms.home_player_2_id = %s THEN ms.home_team
                        ELSE ms.away_team
                    END as player_team,
                    l.league_name
                FROM match_scores ms
                JOIN leagues l ON ms.league_id = l.id
                WHERE ms.home_player_1_id = %s OR ms.home_player_2_id = %s 
                   OR ms.away_player_1_id = %s OR ms.away_player_2_id = %s
            """, [PROBLEM_PLAYER_ID] * 6)
            
            player_teams = cursor.fetchall()
            
            print(f"Player has played for {len(player_teams)} teams:")
            for team_name, league_name in player_teams:
                print(f"  - {team_name} ({league_name})")
                
                # Check if this team has any schedule entries
                cursor.execute("""
                    SELECT COUNT(*) FROM schedule s
                    JOIN leagues l ON s.league_id = l.id
                    WHERE (s.home_team = %s OR s.away_team = %s)
                    AND l.league_name = %s
                """, [team_name, team_name, league_name])
                
                team_schedule_count = cursor.fetchone()[0]
                print(f"    Schedule entries: {team_schedule_count}")
        else:
            print(f"✅ Found {len(schedule_data)} relevant schedule entries:")
            for schedule in schedule_data:
                (sched_id, match_date, match_time, home_team, away_team,
                 location, league_name, team_relevance) = schedule
                
                print(f"  - {match_date} {match_time or 'TBD'}: {home_team} vs {away_team}")
                print(f"    League: {league_name}, Location: {location or 'TBD'}")
                print(f"    Relevance: {team_relevance}")
        
        # Test 4: Team stats access simulation
        print("\n\n4. TEAM STATS ACCESS SIMULATION")
        print("-" * 50)
        
        # Simulate team standings query
        cursor.execute("""
            SELECT ss.team, ss.series, ss.points, ss.matches_won, ss.matches_lost,
                   l.league_name, ss.team_id
            FROM series_stats ss
            JOIN leagues l ON ss.league_id = l.id
            WHERE ss.team IN (
                SELECT DISTINCT COALESCE(ms.home_team, ms.away_team)
                FROM match_scores ms
                WHERE ms.home_player_1_id = %s OR ms.home_player_2_id = %s 
                   OR ms.away_player_1_id = %s OR ms.away_player_2_id = %s
            )
            ORDER BY l.league_name, ss.series, ss.points DESC
        """, [PROBLEM_PLAYER_ID] * 4)
        
        team_stats = cursor.fetchall()
        
        if not team_stats:
            print("❌ CRITICAL: No team stats found for player's teams!")
        else:
            print(f"✅ Found {len(team_stats)} team stats records:")
            for stat in team_stats[:5]:  # Show first 5
                (team, series, points, wins, losses, league_name, team_id) = stat
                print(f"  - {team} ({series}): {wins}-{losses} ({points} pts)")
                print(f"    League: {league_name}, Team ID: {team_id}")
        
        # Test 5: Player's personal stats
        print("\n\n5. PLAYER PERSONAL STATS TEST")
        print("-" * 50)
        
        cursor.execute("""
            SELECT COUNT(*) as total_matches,
                   SUM(CASE 
                       WHEN (ms.home_player_1_id = %s OR ms.home_player_2_id = %s) AND ms.winner = 'home' THEN 1
                       WHEN (ms.away_player_1_id = %s OR ms.away_player_2_id = %s) AND ms.winner = 'away' THEN 1
                       ELSE 0
                   END) as wins,
                   SUM(CASE 
                       WHEN (ms.home_player_1_id = %s OR ms.home_player_2_id = %s) AND ms.winner = 'away' THEN 1
                       WHEN (ms.away_player_1_id = %s OR ms.away_player_2_id = %s) AND ms.winner = 'home' THEN 1
                       ELSE 0
                   END) as losses
            FROM match_scores ms
            WHERE ms.home_player_1_id = %s OR ms.home_player_2_id = %s 
               OR ms.away_player_1_id = %s OR ms.away_player_2_id = %s
        """, [PROBLEM_PLAYER_ID] * 12)
        
        personal_stats = cursor.fetchone()
        total_matches, wins, losses = personal_stats
        
        print(f"Personal match record: {wins}-{losses} ({total_matches} total matches)")
        
        if total_matches == 0:
            print("❌ CRITICAL: No match history found!")
        else:
            win_pct = (wins / total_matches * 100) if total_matches > 0 else 0
            print(f"Win percentage: {win_pct:.1f}%")
        
        # Test 6: Check current session data compatibility
        print("\n\n6. SESSION DATA COMPATIBILITY TEST")
        print("-" * 50)
        
        # Test what session data would be generated for this user
        cursor.execute("""
            SELECT u.id, u.first_name, u.last_name, u.email,
                   u.league_context,
                   p.tenniscores_player_id, p.team_id,
                   l.league_id, l.league_name,
                   c.name as club_name,
                   s.name as series_name,
                   t.team_name
            FROM users u
            JOIN user_player_associations upa ON u.id = upa.user_id
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            LEFT JOIN leagues l ON u.league_context = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE p.tenniscores_player_id = %s
            AND p.league_id = COALESCE(u.league_context, p.league_id)
            AND p.is_active = true
        """, [PROBLEM_PLAYER_ID])
        
        session_data = cursor.fetchall()
        
        if not session_data:
            print("❌ CRITICAL: Cannot generate valid session data!")
            print("   This means the user's league_context doesn't match any active player records")
            
            # Debug: Check all associations
            cursor.execute("""
                SELECT p.league_id, l.league_name, p.is_active,
                       u.league_context, ctx_l.league_name as context_league
                FROM users u
                JOIN user_player_associations upa ON u.id = upa.user_id
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                JOIN leagues l ON p.league_id = l.id
                LEFT JOIN leagues ctx_l ON u.league_context = ctx_l.id
                WHERE p.tenniscores_player_id = %s
            """, [PROBLEM_PLAYER_ID])
            
            debug_data = cursor.fetchall()
            print("\n   DEBUG - All player/user combinations:")
            for debug_record in debug_data:
                (player_league_id, player_league_name, is_active, 
                 user_context, context_league_name) = debug_record
                print(f"   - Player League: {player_league_name} (ID: {player_league_id}, Active: {is_active})")
                print(f"   - User Context: {context_league_name} (ID: {user_context})")
                match_status = "✅ MATCH" if player_league_id == user_context else "❌ MISMATCH"
                print(f"   - Status: {match_status}")
        else:
            print(f"✅ Can generate session data: {len(session_data)} record(s)")
            for session in session_data:
                (user_id, first_name, last_name, email, league_context,
                 tenniscores_id, team_id, league_id, league_name,
                 club_name, series_name, team_name) = session
                
                print(f"  - User: {first_name} {last_name}")
                print(f"  - League: {league_name} ({league_id})")
                print(f"  - Team: {team_name} (ID: {team_id})")
        
        print("\n" + "=" * 80)
        print("🧪 COMPREHENSIVE ACCESS TEST COMPLETE")
        print("=" * 80)


if __name__ == "__main__":
    test_player_application_access() 