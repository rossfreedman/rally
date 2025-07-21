#!/usr/bin/env python3
"""
Session vs Database League Context Diagnostic
=============================================

This script checks the current Flask session data versus what's stored
in the database to debug league context issues after ETL.
"""

import sys
import os
from datetime import datetime

# Add project root to Python path
sys.path.append('.')

from database_config import get_db
import psycopg2
from psycopg2.extras import RealDictCursor

def check_session_vs_database(user_email="rossfreedman@gmail.com"):
    """Check session data versus database for a specific user"""
    print(f"🔍 Checking session vs database for: {user_email}")
    print("=" * 60)
    
    try:
        with get_db() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # 1. Check database user record
            print("📊 DATABASE USER RECORD:")
            cursor.execute("""
                SELECT u.first_name, u.last_name, u.email, u.league_context, 
                       l.league_name, l.league_id as league_string_id
                FROM users u
                LEFT JOIN leagues l ON u.league_context = l.id
                WHERE u.email = %s
            """, [user_email])
            
            db_user = cursor.fetchone()
            if db_user:
                print(f"   Name: {db_user['first_name']} {db_user['last_name']}")
                print(f"   Email: {db_user['email']}")
                print(f"   League Context (DB ID): {db_user['league_context']}")
                print(f"   League Name: {db_user['league_name']}")
                print(f"   League String ID: {db_user['league_string_id']}")
            else:
                print("   ❌ User not found in database!")
                return
                
            # 2. Check what session service would return
            print("\n🔄 SESSION SERVICE WOULD RETURN:")
            try:
                from app.services.session_service import get_session_data_for_user
                session_data = get_session_data_for_user(user_email)
                
                if session_data:
                    print(f"   Name: {session_data.get('first_name')} {session_data.get('last_name')}")
                    print(f"   League Context: {session_data.get('league_context')}")
                    print(f"   League ID: {session_data.get('league_id')}")
                    print(f"   League Name: {session_data.get('league_name')}")
                    print(f"   Club: {session_data.get('club')}")
                    print(f"   Series: {session_data.get('series')}")
                    print(f"   Player ID: {session_data.get('tenniscores_player_id')}")
                else:
                    print("   ❌ Session service returned None!")
            except Exception as e:
                print(f"   ❌ Session service error: {e}")
            
            # 3. Check all player associations
            print("\n👥 ALL PLAYER ASSOCIATIONS:")
            cursor.execute("""
                SELECT upa.tenniscores_player_id, p.first_name, p.last_name,
                       c.name as club, s.name as series, l.league_name,
                       p.league_id, p.team_id, p.is_active
                FROM user_player_associations upa
                JOIN users u ON upa.user_id = u.id
                LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                LEFT JOIN clubs c ON p.club_id = c.id
                LEFT JOIN series s ON p.series_id = s.id
                LEFT JOIN leagues l ON p.league_id = l.id
                WHERE u.email = %s
                ORDER BY p.league_id, p.is_active DESC
            """, [user_email])
            
            associations = cursor.fetchall()
            if associations:
                for i, assoc in enumerate(associations, 1):
                    print(f"   Association {i}:")
                    print(f"      Player ID: {assoc['tenniscores_player_id']}")
                    print(f"      Name: {assoc['first_name']} {assoc['last_name']}")
                    print(f"      Club: {assoc['club']}")
                    print(f"      Series: {assoc['series']}")
                    print(f"      League: {assoc['league_name']} (ID: {assoc['league_id']})")
                    print(f"      Team ID: {assoc['team_id']}")
                    print(f"      Active: {assoc['is_active']}")
                    print()
            else:
                print("   ❌ No player associations found!")
                
            # 4. Compare database vs expected session
            print("🔍 ANALYSIS:")
            if db_user and session_data:
                db_league_context = db_user['league_context']
                session_league_context = session_data.get('league_context')
                session_league_id = session_data.get('league_id')
                
                print(f"   Database league_context: {db_league_context}")
                print(f"   Session league_context: {session_league_context}")
                print(f"   Session league_id: {session_league_id}")
                
                if db_league_context == session_league_context:
                    print("   ✅ League contexts match!")
                else:
                    print("   ❌ League context MISMATCH!")
                    
                if session_data.get('club') and session_data.get('series'):
                    print("   ✅ Session has club and series data")
                else:
                    print("   ❌ Session missing club/series data")
                    
            # 5. Test priority logic
            print("\n🎯 PRIORITY LOGIC TEST:")
            cursor.execute("""
                SELECT DISTINCT
                    p.tenniscores_player_id,
                    p.first_name, p.last_name,
                    c.name as club, s.name as series,
                    l.league_name, p.league_id, p.team_id,
                    -- Priority scoring
                    (CASE WHEN p.league_id = %s THEN 1 ELSE 2 END) as league_priority,
                    (CASE WHEN p.team_id IS NOT NULL THEN 1 ELSE 2 END) as team_priority,
                    p.id as player_db_id
                FROM user_player_associations upa
                JOIN users u ON upa.user_id = u.id
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id AND p.is_active = true
                LEFT JOIN clubs c ON p.club_id = c.id
                LEFT JOIN series s ON p.series_id = s.id
                LEFT JOIN leagues l ON p.league_id = l.id
                WHERE u.email = %s
                ORDER BY 
                    (CASE WHEN p.league_id = %s THEN 1 ELSE 2 END),
                    (CASE WHEN p.team_id IS NOT NULL THEN 1 ELSE 2 END),
                    p.id DESC
            """, [db_user['league_context'], user_email, db_user['league_context']])
            
            priority_results = cursor.fetchall()
            if priority_results:
                print(f"   Priority-sorted players (league_context = {db_user['league_context']}):")
                for i, player in enumerate(priority_results, 1):
                    indicator = "👑" if i == 1 else f"  {i}."
                    print(f"   {indicator} {player['first_name']} {player['last_name']}")
                    print(f"      Club: {player['club']}, Series: {player['series']}")
                    print(f"      League: {player['league_name']} (ID: {player['league_id']})")
                    print(f"      Priority: League={player['league_priority']}, Team={player['team_priority']}")
                    print()
                    
                winning_player = priority_results[0]
                print(f"   🎯 SESSION SHOULD USE: {winning_player['club']} - {winning_player['series']}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_session_vs_database() 