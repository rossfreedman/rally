#!/usr/bin/env python3
"""
Diagnose League ID Mismatch Issue
Checks for format mismatches between user session data and database tables
that could cause my-club page to fail after match_scores updates
"""

import psycopg2
from urllib.parse import urlparse

RAILWAY_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def connect_to_railway():
    """Connect to Railway database"""
    parsed = urlparse(RAILWAY_URL)
    conn_params = {
        "dbname": parsed.path[1:],
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "sslmode": "require",
        "connect_timeout": 30,
    }
    return psycopg2.connect(**conn_params)

def execute_query(conn, query, params=None):
    """Execute query and return results"""
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        return []

def execute_query_one(conn, query, params=None):
    """Execute query and return one result"""
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                row = cursor.fetchone()
                return dict(zip(columns, row)) if row else None
            return None
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        return None

def check_league_id_formats(conn):
    """Check the format of league_ids across different tables"""
    print("🔍 CHECKING LEAGUE_ID FORMATS ACROSS TABLES")
    print("=" * 60)
    
    # Check leagues table structure
    leagues_sample = execute_query(conn, """
        SELECT id, league_id, league_name 
        FROM leagues 
        ORDER BY id 
        LIMIT 5
    """)
    
    print(f"   📊 Leagues table format:")
    print(f"      Columns: id (PRIMARY KEY), league_id (UNIQUE), league_name")
    for league in leagues_sample:
        print(f"      - ID {league['id']}: league_id='{league['league_id']}', name='{league['league_name']}'")
    
    # Check match_scores league_id format
    match_scores_sample = execute_query(conn, """
        SELECT DISTINCT league_id, COUNT(*) as match_count
        FROM match_scores 
        WHERE league_id IS NOT NULL
        GROUP BY league_id
        ORDER BY league_id
    """)
    
    print(f"\n   📊 Match_scores league_id values:")
    for item in match_scores_sample:
        print(f"      - league_id: {item['league_id']} ({type(item['league_id']).__name__}) → {item['match_count']} matches")
    
    # Check if there's a format mismatch
    league_ids_in_leagues = [str(l['league_id']) for l in leagues_sample]
    league_ids_in_matches = [str(m['league_id']) for m in match_scores_sample]
    
    print(f"\n   🔍 Format Analysis:")
    print(f"      Leagues.league_id format: {[type(l['league_id']).__name__ for l in leagues_sample]}")
    print(f"      Match_scores.league_id format: {[type(m['league_id']).__name__ for m in match_scores_sample]}")
    
    return leagues_sample, match_scores_sample

def test_user_session_simulation(conn, leagues_sample):
    """Simulate what happens when users try to filter by league_id"""
    print(f"\n🧪 TESTING USER SESSION FILTERING")
    print("=" * 60)
    
    # Get a sample user with primary player association
    test_user = execute_query_one(conn, """
        SELECT u.email, u.first_name, u.last_name,
               p.tenniscores_player_id,
               c.name as club_name,
               s.name as series_name,
               l.id as league_db_id,
               l.league_id as league_string_id,
               l.league_name
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id AND upa.is_primary = true
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        JOIN clubs c ON p.club_id = c.id
        JOIN series s ON p.series_id = s.id
        JOIN leagues l ON p.league_id = l.id
        ORDER BY u.last_login DESC
        LIMIT 1
    """)
    
    if not test_user:
        print("   ❌ No test user found with complete associations")
        return
    
    print(f"   👤 Testing with user: {test_user['first_name']} {test_user['last_name']}")
    print(f"      Club: {test_user['club_name']}")
    print(f"      League DB ID: {test_user['league_db_id']} (integer)")
    print(f"      League String ID: '{test_user['league_string_id']}' (string)")
    print(f"      League Name: {test_user['league_name']}")
    
    # Test different filtering approaches
    club_pattern = f"%{test_user['club_name']}%"
    
    # Method 1: Filter by integer league_id (current system)
    matches_by_int = execute_query_one(conn, """
        SELECT COUNT(*) as count
        FROM match_scores ms
        WHERE ms.league_id = %s
        AND (ms.home_team LIKE %s OR ms.away_team LIKE %s)
    """, [test_user['league_db_id'], club_pattern, club_pattern])
    
    # Method 2: Filter by string league_id (old system)
    matches_by_string = execute_query_one(conn, """
        SELECT COUNT(*) as count
        FROM match_scores ms
        JOIN leagues l ON ms.league_id = l.id
        WHERE l.league_id = %s
        AND (ms.home_team LIKE %s OR ms.away_team LIKE %s)
    """, [test_user['league_string_id'], club_pattern, club_pattern])
    
    # Method 3: No league filtering (should show all club matches)
    matches_no_filter = execute_query_one(conn, """
        SELECT COUNT(*) as count
        FROM match_scores ms
        WHERE (ms.home_team LIKE %s OR ms.away_team LIKE %s)
    """, [club_pattern, club_pattern])
    
    print(f"\n   🔍 Match Query Results:")
    print(f"      Method 1 (integer league_id = {test_user['league_db_id']}): {matches_by_int['count']} matches")
    print(f"      Method 2 (string league_id = '{test_user['league_string_id']}'): {matches_by_string['count']} matches")
    print(f"      Method 3 (no league filter): {matches_no_filter['count']} matches")
    
    # Diagnose the issue
    if matches_by_int['count'] == 0 and matches_no_filter['count'] > 0:
        print(f"\n   🚨 ISSUE FOUND: League filtering is broken!")
        print(f"      - User's club has {matches_no_filter['count']} total matches")
        print(f"      - But league filtering returns 0 matches")
        print(f"      - This suggests league_id mismatch in filtering logic")
    elif matches_by_int['count'] > 0:
        print(f"\n   ✅ League filtering appears to work correctly")
    else:
        print(f"\n   ⚠️ No matches found for this club at all")
    
    return test_user

def check_session_data_creation(conn):
    """Check how session data is created for users"""
    print(f"\n🔍 CHECKING SESSION DATA CREATION")
    print("=" * 60)
    
    # Check what data would be in user sessions
    session_data_sample = execute_query(conn, """
        SELECT u.email,
               l.id as league_db_id,
               l.league_id as league_string_id,
               l.league_name,
               c.name as club_name,
               s.name as series_name
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id AND upa.is_primary = true
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        JOIN leagues l ON p.league_id = l.id
        JOIN clubs c ON p.club_id = c.id
        JOIN series s ON p.series_id = s.id
        ORDER BY u.last_login DESC
        LIMIT 5
    """)
    
    print(f"   📊 Sample user session data that would be created:")
    for user in session_data_sample:
        print(f"      - {user['email']}:")
        print(f"        club: '{user['club_name']}'")
        print(f"        series: '{user['series_name']}'")
        print(f"        league_id: {user['league_db_id']} (integer in new system)")
        print(f"        league_name: '{user['league_name']}'")
    
    return session_data_sample

def main():
    """Main diagnostic function"""
    print("🚀 LEAGUE_ID MISMATCH DIAGNOSTIC")
    print("=" * 50)
    print("Checking for league_id format issues causing my-club page failures...")
    
    try:
        # Connect to Railway
        print("\n🔌 Connecting to Railway database...")
        conn = connect_to_railway()
        print("   ✅ Connected successfully")
        
        # Step 1: Check league_id formats
        leagues_sample, match_scores_sample = check_league_id_formats(conn)
        
        # Step 2: Check session data creation
        session_data_sample = check_session_data_creation(conn)
        
        # Step 3: Test filtering with real user
        if session_data_sample:
            test_user = test_user_session_simulation(conn, leagues_sample)
        
        print(f"\n🎉 SUMMARY:")
        print(f"   • Leagues table uses integer primary keys with string league_id values")
        print(f"   • Match_scores uses integer league_id foreign keys")
        print(f"   • User sessions should contain integer league_id for proper filtering")
        print(f"   • If my-club page is failing, check the filtering logic in get_mobile_club_data()")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 