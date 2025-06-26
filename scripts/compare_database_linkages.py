#!/usr/bin/env python3
"""
Compare Database Linkages: Local vs Railway
Diagnoses broken ID relationships causing my-club and my-series page failures
"""

import psycopg2
from urllib.parse import urlparse

# Database connection strings
LOCAL_URL = "postgresql://postgres:postgres@localhost:5432/rally"
RAILWAY_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def connect_to_database(url, name):
    """Connect to database"""
    try:
        parsed = urlparse(url)
        conn_params = {
            "dbname": parsed.path[1:],
            "user": parsed.username,
            "password": parsed.password,
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "sslmode": "require" if "railway" in url else "prefer",
            "connect_timeout": 30,
        }
        conn = psycopg2.connect(**conn_params)
        print(f"✅ Connected to {name} database")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to {name}: {e}")
        return None

def execute_query(conn, query, params=None):
    """Execute query and return results"""
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or [])
        return cursor.fetchall()
    except Exception as e:
        print(f"❌ Query error: {e}")
        return []

def execute_query_one(conn, query, params=None):
    """Execute query and return single result"""
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or [])
        result = cursor.fetchone()
        return result
    except Exception as e:
        print(f"❌ Query error: {e}")
        return None

def compare_table_counts(local_conn, railway_conn):
    """Compare basic table counts between environments"""
    print(f"\n🔍 COMPARING TABLE COUNTS")
    print("=" * 60)
    
    tables = ["users", "user_player_associations", "players", "teams", "series", "clubs", "leagues", "match_scores", "series_stats"]
    
    for table in tables:
        local_count = execute_query_one(local_conn, f"SELECT COUNT(*) FROM {table}")
        railway_count = execute_query_one(railway_conn, f"SELECT COUNT(*) FROM {table}")
        
        local_count = local_count[0] if local_count else 0
        railway_count = railway_count[0] if railway_count else 0
        
        status = "✅" if local_count == railway_count else "❌"
        print(f"   {status} {table}: Local={local_count}, Railway={railway_count}")

def compare_user_associations(local_conn, railway_conn):
    """Compare user-player associations"""
    print(f"\n🔍 COMPARING USER-PLAYER ASSOCIATIONS")
    print("=" * 60)
    
    # Count users with primary associations
    local_primary = execute_query_one(local_conn, """
        SELECT COUNT(DISTINCT u.id) 
        FROM users u 
        JOIN user_player_associations upa ON u.id = upa.user_id AND upa.is_primary = true
    """)
    
    railway_primary = execute_query_one(railway_conn, """
        SELECT COUNT(DISTINCT u.id) 
        FROM users u 
        JOIN user_player_associations upa ON u.id = upa.user_id AND upa.is_primary = true
    """)
    
    local_primary = local_primary[0] if local_primary else 0
    railway_primary = railway_primary[0] if railway_primary else 0
    
    print(f"   Users with primary associations: Local={local_primary}, Railway={railway_primary}")
    
    # Sample user associations
    sample_users = execute_query(railway_conn, """
        SELECT u.email, u.first_name, u.last_name, 
               upa.tenniscores_player_id, upa.is_primary
        FROM users u 
        JOIN user_player_associations upa ON u.id = upa.user_id
        ORDER BY u.last_login DESC
        LIMIT 5
    """)
    
    print(f"\n   Sample Railway user associations:")
    for user in sample_users:
        email, fname, lname, player_id, is_primary = user
        print(f"      {fname} {lname} ({email}): {player_id} {'(PRIMARY)' if is_primary else ''}")

def compare_player_linkages(local_conn, railway_conn):
    """Compare player-to-team/series/club linkages"""
    print(f"\n🔍 COMPARING PLAYER LINKAGES")
    print("=" * 60)
    
    # Players with complete linkages (team, series, club, league)
    complete_linkage_query = """
        SELECT COUNT(*) as complete_players
        FROM players p
        WHERE p.team_id IS NOT NULL 
        AND p.series_id IS NOT NULL 
        AND p.club_id IS NOT NULL 
        AND p.league_id IS NOT NULL
    """
    
    local_complete = execute_query_one(local_conn, complete_linkage_query)
    railway_complete = execute_query_one(railway_conn, complete_linkage_query)
    
    local_complete = local_complete[0] if local_complete else 0
    railway_complete = railway_complete[0] if railway_complete else 0
    
    print(f"   Players with complete linkages: Local={local_complete}, Railway={railway_complete}")
    
    # Broken linkages
    broken_linkages = [
        ("Missing team_id", "p.team_id IS NULL"),
        ("Missing series_id", "p.series_id IS NULL"), 
        ("Missing club_id", "p.club_id IS NULL"),
        ("Missing league_id", "p.league_id IS NULL")
    ]
    
    for desc, condition in broken_linkages:
        local_broken = execute_query_one(local_conn, f"SELECT COUNT(*) FROM players p WHERE {condition}")
        railway_broken = execute_query_one(railway_conn, f"SELECT COUNT(*) FROM players p WHERE {condition}")
        
        local_broken = local_broken[0] if local_broken else 0
        railway_broken = railway_broken[0] if railway_broken else 0
        
        status = "❌" if railway_broken > local_broken else "✅"
        print(f"   {status} {desc}: Local={local_broken}, Railway={railway_broken}")

def compare_team_assignments(local_conn, railway_conn):
    """Compare team assignments"""
    print(f"\n🔍 COMPARING TEAM ASSIGNMENTS")
    print("=" * 60)
    
    # Teams with players
    teams_with_players_query = """
        SELECT COUNT(DISTINCT t.id) as teams_with_players
        FROM teams t
        WHERE EXISTS (SELECT 1 FROM players p WHERE p.team_id = t.id)
    """
    
    local_teams = execute_query_one(local_conn, teams_with_players_query)
    railway_teams = execute_query_one(railway_conn, teams_with_players_query)
    
    local_teams = local_teams[0] if local_teams else 0
    railway_teams = railway_teams[0] if railway_teams else 0
    
    print(f"   Teams with players: Local={local_teams}, Railway={railway_teams}")
    
    # Sample team composition for Tennaqua
    sample_teams = execute_query(railway_conn, """
        SELECT t.team_name, t.id, COUNT(p.id) as player_count,
               c.name as club_name, s.name as series_name, l.league_name
        FROM teams t
        LEFT JOIN players p ON t.id = p.team_id
        LEFT JOIN clubs c ON t.club_id = c.id
        LEFT JOIN series s ON t.series_id = s.id
        LEFT JOIN leagues l ON t.league_id = l.id
        WHERE c.name = 'Tennaqua'
        GROUP BY t.id, t.team_name, c.name, s.name, l.league_name
        ORDER BY player_count DESC
        LIMIT 5
    """)
    
    print(f"\n   Sample Tennaqua teams on Railway:")
    for team in sample_teams:
        team_name, team_id, player_count, club, series, league = team
        print(f"      {team_name} (ID: {team_id}): {player_count} players, {series} in {league}")

def test_session_data_creation(local_conn, railway_conn, test_email="ross@rossfreedman.com"):
    """Test what session data would be created for a specific user"""
    print(f"\n🔍 TESTING SESSION DATA CREATION")
    print("=" * 60)
    
    session_query = """
        SELECT u.id, u.email, u.first_name, u.last_name,
               l.id as league_db_id, l.league_id, l.league_name,
               c.name as club_name, s.name as series_name,
               t.id as team_id, t.team_name,
               p.tenniscores_player_id
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id AND upa.is_primary = true
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        LEFT JOIN leagues l ON p.league_id = l.id
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE u.email = %s
        LIMIT 1
    """
    
    print(f"   Testing session creation for: {test_email}")
    
    for conn, db_name in [(local_conn, "LOCAL"), (railway_conn, "RAILWAY")]:
        session_data = execute_query_one(conn, session_query, [test_email])
        
        print(f"\n   {db_name} session would be:")
        if session_data:
            user_id, email, fname, lname, league_db_id, league_id, league_name, club, series, team_id, team_name, player_id = session_data
            print(f"      ✅ user_id: {user_id}")
            print(f"      ✅ league_id: {league_db_id} ('{league_id}' - {league_name})")
            print(f"      ✅ club: '{club}'")
            print(f"      ✅ series: '{series}'")
            print(f"      ✅ team_id: {team_id} ('{team_name}')")
            print(f"      ✅ player_id: '{player_id}'")
        else:
            print(f"      ❌ Could not create session - broken linkages")

def test_my_club_queries(local_conn, railway_conn):
    """Test the actual queries used by my-club page"""
    print(f"\n🔍 TESTING MY-CLUB QUERIES")
    print("=" * 60)
    
    # Test with Tennaqua club and known league
    test_club = "Tennaqua"
    
    # Get a valid league ID from Railway
    league_info = execute_query_one(railway_conn, "SELECT id, league_name FROM leagues LIMIT 1")
    if not league_info:
        print("   ❌ No leagues found in Railway")
        return
        
    test_league_id = league_info[0]
    league_name = league_info[1]
    
    print(f"   Testing with club='{test_club}', league_id={test_league_id} ({league_name})")
    
    # Test series_stats query (for standings)
    series_stats_query = """
        SELECT COUNT(*) as tennaqua_teams
        FROM series_stats ss
        WHERE ss.team LIKE %s 
        AND ss.league_id = %s
    """
    
    for conn, db_name in [(local_conn, "LOCAL"), (railway_conn, "RAILWAY")]:
        result = execute_query_one(conn, series_stats_query, [f"{test_club}%", test_league_id])
        count = result[0] if result else 0
        status = "✅" if count > 0 else "❌"
        print(f"   {status} {db_name} series_stats teams: {count}")
    
    # Test match_scores query (for recent matches)
    match_scores_query = """
        SELECT COUNT(*) as tennaqua_matches
        FROM match_scores ms
        WHERE ms.league_id = %s 
        AND (ms.home_team LIKE %s OR ms.away_team LIKE %s)
    """
    
    club_pattern = f"%{test_club}%"
    for conn, db_name in [(local_conn, "LOCAL"), (railway_conn, "RAILWAY")]:
        result = execute_query_one(conn, match_scores_query, [test_league_id, club_pattern, club_pattern])
        count = result[0] if result else 0
        status = "✅" if count > 0 else "❌"
        print(f"   {status} {db_name} match_scores matches: {count}")

def main():
    """Main diagnostic function"""
    print("🚀 DATABASE LINKAGE COMPARISON")
    print("=" * 50)
    print("Comparing Local vs Railway database relationships...")
    
    # Connect to both databases
    local_conn = connect_to_database(LOCAL_URL, "Local")
    railway_conn = connect_to_database(RAILWAY_URL, "Railway")
    
    if not local_conn or not railway_conn:
        print("❌ Failed to connect to databases")
        return
    
    try:
        # Run all comparisons
        compare_table_counts(local_conn, railway_conn)
        compare_user_associations(local_conn, railway_conn)
        compare_player_linkages(local_conn, railway_conn)
        compare_team_assignments(local_conn, railway_conn)
        test_session_data_creation(local_conn, railway_conn)
        test_my_club_queries(local_conn, railway_conn)
        
        print(f"\n🎯 LIKELY ISSUES:")
        print(f"   • Check if players have valid team_id references")
        print(f"   • Check if series_stats has data for Railway leagues")
        print(f"   • Check if match_scores references correct league_ids")
        print(f"   • Check if user_player_associations are complete")
        
    finally:
        local_conn.close()
        railway_conn.close()

if __name__ == "__main__":
    main() 