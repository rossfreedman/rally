#!/usr/bin/env python3

import os
import sys
import psycopg2
from urllib.parse import urlparse

# Railway staging database URL (from staging environment)
STAGING_DB_URL = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"

def execute_query_railway(query, params=None):
    """Execute query on Railway staging database"""
    try:
        parsed = urlparse(STAGING_DB_URL)
        conn_params = {
            "dbname": parsed.path[1:],
            "user": parsed.username,
            "password": parsed.password,
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "sslmode": "require",
            "connect_timeout": 30,
        }
        
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if query.strip().upper().startswith('SELECT'):
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            return results
        else:
            conn.commit()
            return cursor.rowcount
            
    except Exception as e:
        print(f"Database error: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def execute_query_one_railway(query, params=None):
    """Execute query and return single result on Railway staging database"""
    results = execute_query_railway(query, params)
    return results[0] if results else None

def debug_session_building():
    """Debug exactly what the session building query returns for the user"""
    
    user_email = "rossfreedman@gmail.com"
    
    print(f"🔍 Debugging session building for: {user_email}")
    print(f"🌐 Connecting to Railway STAGING database...")
    print("=" * 60)
    
    # 1. Check user's basic info and league_context
    print("1. User basic info and league_context...")
    user_query = """
        SELECT id, email, first_name, last_name, league_context
        FROM users 
        WHERE email = %s
    """
    user_info = execute_query_one_railway(user_query, [user_email])
    
    if not user_info:
        print(f"   ❌ User not found: {user_email}")
        return
    
    print(f"   ✅ User found:")
    print(f"      ID: {user_info['id']}")
    print(f"      Name: {user_info['first_name']} {user_info['last_name']}")
    print(f"      League Context: {user_info['league_context']}")
    
    # 2. Check all user_player_associations
    print(f"\n2. All user_player_associations for this user...")
    assoc_query = """
        SELECT user_id, tenniscores_player_id, created_at, is_primary
        FROM user_player_associations 
        WHERE user_id = %s
        ORDER BY created_at DESC
    """
    associations = execute_query_railway(assoc_query, [user_info['id']])
    
    if associations:
        print(f"   ✅ Found {len(associations)} association(s):")
        for i, assoc in enumerate(associations):
            print(f"      {i+1}. Player ID: {assoc['tenniscores_player_id']}")
            print(f"         Created: {assoc['created_at']}")
            print(f"         Is Primary: {assoc.get('is_primary', 'N/A')}")
    else:
        print(f"   ❌ No associations found")
        return
    
    # 3. Check what data each association would provide
    print(f"\n3. Player data for each association...")
    for i, assoc in enumerate(associations):
        player_id = assoc['tenniscores_player_id']
        print(f"\n   Association {i+1}: {player_id}")
        
        # Check player records for this ID
        player_query = """
            SELECT p.id, p.tenniscores_player_id, p.team_id, p.club_id, p.series_id, p.league_id, p.is_active,
                   c.name as club_name, s.name as series_name, l.league_name,
                   t.team_name
            FROM players p
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN leagues l ON p.league_id = l.id
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE p.tenniscores_player_id = %s
        """
        players = execute_query_railway(player_query, [player_id])
        
        if players:
            for j, player in enumerate(players):
                print(f"      Player Record {j+1}:")
                print(f"         Team ID: {player['team_id']}")
                print(f"         Club: {player['club_name']} (ID: {player['club_id']})")
                print(f"         Series: {player['series_name']} (ID: {player['series_id']})")
                print(f"         League: {player['league_name']} (ID: {player['league_id']})")
                print(f"         Team Name: {player['team_name']}")
                print(f"         Active: {player['is_active']}")
                
                # Check if this matches user's league_context
                matches_context = player['league_id'] == user_info['league_context']
                print(f"         Matches League Context: {matches_context}")
        else:
            print(f"      ❌ No player records found for ID: {player_id}")
    
    # 4. Run the EXACT session building query from session_service.py
    print(f"\n4. Running the EXACT session building query...")
    session_query = """
        SELECT 
            u.id,
            u.email, 
            u.first_name, 
            u.last_name,
            u.is_admin,
            u.ad_deuce_preference,
            u.dominant_hand,
            u.league_context,
            -- Player data from league_context with ALL required IDs
            p.tenniscores_player_id,
            p.team_id,
            p.club_id,
            p.series_id,
            c.name as club,
            c.logo_filename as club_logo,
            s.name as series,
            l.id as league_db_id,
            l.league_id as league_string_id,
            l.league_name
        FROM users u
        LEFT JOIN user_player_associations upa ON u.id = upa.user_id
        LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id 
            AND p.league_id = u.league_context 
            AND p.is_active = TRUE
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id
        LEFT JOIN leagues l ON p.league_id = l.id
        WHERE u.email = %s
        ORDER BY (CASE WHEN p.tenniscores_player_id IS NOT NULL THEN 1 ELSE 2 END)
        LIMIT 1
    """
    
    session_result = execute_query_one_railway(session_query, [user_email])
    
    if session_result:
        print(f"   ✅ Session query result:")
        print(f"      User ID: {session_result['id']}")
        print(f"      Email: {session_result['email']}")
        print(f"      League Context: {session_result['league_context']}")
        print(f"      Player ID: {session_result['tenniscores_player_id']}")
        print(f"      Team ID: {session_result['team_id']}")
        print(f"      Club: {session_result['club']}")
        print(f"      Series: {session_result['series']}")
        print(f"      League DB ID: {session_result['league_db_id']}")
        print(f"      League String ID: {session_result['league_string_id']}")
        print(f"      League Name: {session_result['league_name']}")
    else:
        print(f"   ❌ Session query returned no results!")
    
    # 5. Try the query without the league_context restriction to see what we get
    print(f"\n5. Running session query WITHOUT league_context restriction...")
    unrestricted_query = """
        SELECT 
            u.id,
            u.email, 
            u.first_name, 
            u.last_name,
            u.league_context,
            p.tenniscores_player_id,
            p.team_id,
            p.club_id,
            p.series_id,
            c.name as club,
            s.name as series,
            l.id as league_db_id,
            l.league_id as league_string_id,
            l.league_name,
            t.team_name
        FROM users u
        LEFT JOIN user_player_associations upa ON u.id = upa.user_id
        LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id 
            AND p.is_active = TRUE
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id
        LEFT JOIN leagues l ON p.league_id = l.id
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE u.email = %s
        ORDER BY p.league_id, p.team_id
    """
    
    unrestricted_results = execute_query_railway(unrestricted_query, [user_email])
    
    if unrestricted_results:
        print(f"   ✅ Found {len(unrestricted_results)} results without restriction:")
        for i, result in enumerate(unrestricted_results):
            print(f"      Result {i+1}:")
            print(f"         Player ID: {result['tenniscores_player_id']}")
            print(f"         Team ID: {result['team_id']}")
            print(f"         Club: {result['club']}")
            print(f"         Series: {result['series']}")
            print(f"         League: {result['league_name']} (ID: {result['league_db_id']})")
            print(f"         Team Name: {result['team_name']}")
            
            # Check match with context
            matches_context = result['league_db_id'] == user_info['league_context']
            print(f"         Matches League Context: {matches_context}")
    else:
        print(f"   ❌ No results even without restriction!")

if __name__ == "__main__":
    debug_session_building() 