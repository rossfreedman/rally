#!/usr/bin/env python3

import psycopg2
from urllib.parse import urlparse

# Railway staging database URL
STAGING_DB_URL = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"

def execute_query_one_railway(query, params=None):
    """Execute query and return single result on Railway staging database"""
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
        
        columns = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        result = dict(zip(columns, row)) if row else None
        
        return result
    except Exception as e:
        print(f"Database error: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def debug_session_issue():
    """Debug why session is still wrong on Railway"""
    
    user_email = "rossfreedman@gmail.com"
    
    print(f"🔍 Debugging session issue for: {user_email}")
    print("=" * 60)
    
    # 1. Check user's league_context
    print("1. Checking user's league_context...")
    user_query = """
        SELECT id, email, first_name, last_name, league_context
        FROM users 
        WHERE email = %s
    """
    user_info = execute_query_one_railway(user_query, [user_email])
    
    if user_info:
        print(f"   ✅ User: {user_info['first_name']} {user_info['last_name']}")
        print(f"   League Context: {user_info['league_context']}")
    else:
        print(f"   ❌ User not found")
        return
    
    # 2. Test the exact session building query that should be running
    print(f"\n2. Testing session building query...")
    session_query = """
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
        print(f"   ✅ Session query successful:")
        print(f"      Team ID: {session_result['team_id']}")
        print(f"      League DB ID: {session_result['league_db_id']}")
        print(f"      League String ID: {session_result['league_string_id']}")
        print(f"      Club: {session_result['club']}")
        print(f"      Series: {session_result['series']}")
        
        # Check if this matches what we expect
        if session_result['team_id'] == 30314 and session_result['league_db_id'] == 4611:
            print(f"   ✅ Session data looks CORRECT!")
        else:
            print(f"   ❌ Session data is WRONG!")
            print(f"      Expected: team_id=30314, league_id=4611") 
            print(f"      Got: team_id={session_result['team_id']}, league_id={session_result['league_db_id']}")
    else:
        print(f"   ❌ Session query returned no results!")
        
        # Try without league_context restriction
        print(f"\n   Trying query without league_context restriction...")
        unrestricted_query = """
            SELECT 
                u.id, u.email, u.league_context,
                p.tenniscores_player_id, p.team_id, p.league_id,
                c.name as club, s.name as series, l.league_name
            FROM users u
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id 
                AND p.is_active = TRUE
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN leagues l ON p.league_id = l.id
            WHERE u.email = %s
            ORDER BY p.league_id
        """
        
        unrestricted_result = execute_query_one_railway(unrestricted_query, [user_email])
        if unrestricted_result:
            print(f"      Found data without restriction:")
            print(f"         Team ID: {unrestricted_result['team_id']}")
            print(f"         League ID: {unrestricted_result['league_id']}")
            print(f"         User League Context: {unrestricted_result['league_context']}")
            
            if unrestricted_result['league_id'] != unrestricted_result['league_context']:
                print(f"      ❌ MISMATCH: Player league_id ({unrestricted_result['league_id']}) != User league_context ({unrestricted_result['league_context']})")

if __name__ == "__main__":
    debug_session_issue() 