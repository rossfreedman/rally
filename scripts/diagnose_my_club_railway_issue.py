#!/usr/bin/env python3
"""
Diagnose My Club Railway Issue
Compares data between local and Railway databases to identify differences
that cause the my-club page to fail on Railway but work locally.
"""

import psycopg2
from urllib.parse import urlparse
import os
from datetime import datetime

# Database connections
LOCAL_URL = "postgresql://postgres:postgres@localhost:5432/rally"
RAILWAY_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def connect_to_db(url):
    """Connect to database"""
    parsed = urlparse(url)
    conn_params = {
        "dbname": parsed.path[1:],
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port or 5432,
    }
    if "railway" in url:
        conn_params["sslmode"] = "require"
        conn_params["connect_timeout"] = 30
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

def test_sample_user_data(local_conn, railway_conn):
    """Test with a sample user that should exist in both databases"""
    print("🧪 TESTING SAMPLE USER DATA")
    print("=" * 60)
    
    # Get a sample user from both databases
    sample_user_query = """
        SELECT email, first_name, last_name, club, series, league_id, league_name
        FROM users 
        WHERE club IS NOT NULL AND series IS NOT NULL 
        ORDER BY last_login DESC 
        LIMIT 1
    """
    
    print("\n📊 Sample Users:")
    local_user = execute_query_one(local_conn, sample_user_query)
    railway_user = execute_query_one(railway_conn, sample_user_query)
    
    print(f"   Local: {local_user}")
    print(f"   Railway: {railway_user}")
    
    # Use the Railway user for testing (since that's where it's failing)
    test_user = railway_user if railway_user else local_user
    
    if not test_user:
        print("   ❌ No sample user found in either database")
        return None
        
    print(f"\n🎯 Testing with user: {test_user['first_name']} {test_user['last_name']} from {test_user['club']}")
    
    return test_user

def test_recent_matches_query(local_conn, railway_conn, user):
    """Test the get_recent_matches_for_user_club function queries"""
    print(f"\n🔍 TESTING RECENT MATCHES QUERIES")
    print("=" * 60)
    
    if not user:
        print("   ❌ No user provided")
        return
        
    club_name = user['club']
    user_league_id = user.get('league_id')
    
    print(f"   Club: '{club_name}', League ID: '{user_league_id}'")
    
    # Test league lookup
    if user_league_id:
        league_lookup_query = "SELECT id FROM leagues WHERE league_id = %s"
        print(f"\n   🔍 League lookup for '{user_league_id}':")
        
        local_league = execute_query_one(local_conn, league_lookup_query, [user_league_id])
        railway_league = execute_query_one(railway_conn, league_lookup_query, [user_league_id])
        
        print(f"      Local: {local_league}")
        print(f"      Railway: {railway_league}")
        
        user_league_db_id = railway_league['id'] if railway_league else None
    else:
        user_league_db_id = None
        print(f"   ⚠️ No league_id in user session")
    
    # Test match_scores query
    if user_league_db_id:
        matches_query = """
            SELECT COUNT(*) as total_matches,
                   COUNT(CASE WHEN home_team LIKE %s THEN 1 END) as home_matches,
                   COUNT(CASE WHEN away_team LIKE %s THEN 1 END) as away_matches
            FROM match_scores ms
            WHERE ms.league_id = %s 
            AND (ms.home_team LIKE %s OR ms.away_team LIKE %s)
        """
        club_pattern = f"%{club_name}%"
        
        print(f"\n   🔍 Match count for club '{club_name}' in league {user_league_db_id}:")
        
        local_matches = execute_query_one(local_conn, matches_query, 
                                        [club_pattern, club_pattern, user_league_db_id, club_pattern, club_pattern])
        railway_matches = execute_query_one(railway_conn, matches_query, 
                                          [club_pattern, club_pattern, user_league_db_id, club_pattern, club_pattern])
        
        print(f"      Local: {local_matches}")
        print(f"      Railway: {railway_matches}")
    else:
        print(f"   ⚠️ Skipping match query - no league DB ID")

def test_series_stats_query(local_conn, railway_conn, user):
    """Test the series_stats queries for standings"""
    print(f"\n🔍 TESTING SERIES STATS QUERIES")
    print("=" * 60)
    
    if not user:
        print("   ❌ No user provided")
        return
        
    club_name = user['club']
    user_league_id = user.get('league_id')
    
    # Get league DB ID
    user_league_db_id = None
    if user_league_id:
        league_lookup = execute_query_one(railway_conn, "SELECT id FROM leagues WHERE league_id = %s", [user_league_id])
        user_league_db_id = league_lookup['id'] if league_lookup else None
    
    # Test series_stats table
    series_stats_query = """
        SELECT COUNT(*) as total_teams,
               COUNT(CASE WHEN team LIKE %s THEN 1 END) as club_teams
        FROM series_stats ss
        WHERE (%s IS NULL OR ss.league_id = %s)
    """
    
    print(f"   🔍 Series stats for club '{club_name}' in league {user_league_db_id}:")
    
    club_pattern = f"{club_name}%"
    local_stats = execute_query_one(local_conn, series_stats_query, 
                                   [club_pattern, user_league_db_id, user_league_db_id])
    railway_stats = execute_query_one(railway_conn, series_stats_query, 
                                     [club_pattern, user_league_db_id, user_league_db_id])
    
    print(f"      Local: {local_stats}")
    print(f"      Railway: {railway_stats}")

def test_player_streaks_data(local_conn, railway_conn, user):
    """Test player streaks calculation data"""
    print(f"\n🔍 TESTING PLAYER STREAKS DATA")
    print("=" * 60)
    
    if not user:
        print("   ❌ No user provided")
        return
        
    club_name = user['club']
    
    # Test match_scores table for player streaks
    player_streaks_query = """
        SELECT COUNT(*) as total_matches,
               COUNT(CASE WHEN home_team LIKE %s OR away_team LIKE %s THEN 1 END) as club_matches
        FROM match_scores ms
    """
    
    print(f"   🔍 Match data for player streaks (club '{club_name}'):")
    
    club_pattern = f"{club_name}%"
    local_streaks = execute_query_one(local_conn, player_streaks_query, 
                                     [club_pattern, club_pattern])
    railway_streaks = execute_query_one(railway_conn, player_streaks_query, 
                                       [club_pattern, club_pattern])
    
    print(f"      Local: {local_streaks}")
    print(f"      Railway: {railway_streaks}")

def test_general_data_availability(local_conn, railway_conn):
    """Test general data availability between databases"""
    print(f"\n🔍 TESTING GENERAL DATA AVAILABILITY")
    print("=" * 60)
    
    tables_to_check = [
        "users",
        "leagues", 
        "match_scores",
        "series_stats",
        "teams",
        "players"
    ]
    
    for table in tables_to_check:
        count_query = f"SELECT COUNT(*) as count FROM {table}"
        
        local_count = execute_query_one(local_conn, count_query)
        railway_count = execute_query_one(railway_conn, count_query)
        
        local_num = local_count['count'] if local_count else 0
        railway_num = railway_count['count'] if railway_count else 0
        
        status = "✅" if railway_num > 0 else "❌"
        ratio = f"({railway_num}/{local_num})" if local_num > 0 else ""
        
        print(f"   {status} {table}: Railway={railway_num}, Local={local_num} {ratio}")

def test_user_session_data(local_conn, railway_conn):
    """Test user session data quality"""
    print(f"\n🔍 TESTING USER SESSION DATA QUALITY")
    print("=" * 60)
    
    # Check users with complete profile data
    complete_users_query = """
        SELECT COUNT(*) as total_users,
               COUNT(CASE WHEN club IS NOT NULL AND club != '' THEN 1 END) as users_with_club,
               COUNT(CASE WHEN series IS NOT NULL AND series != '' THEN 1 END) as users_with_series,
               COUNT(CASE WHEN league_id IS NOT NULL AND league_id != '' THEN 1 END) as users_with_league_id
        FROM users
    """
    
    print(f"   🔍 User profile completeness:")
    
    local_users = execute_query_one(local_conn, complete_users_query)
    railway_users = execute_query_one(railway_conn, complete_users_query)
    
    print(f"      Local: {local_users}")
    print(f"      Railway: {railway_users}")

def main():
    """Main diagnostic function"""
    print("🚀 MY CLUB RAILWAY DIAGNOSTIC")
    print("=" * 50)
    print(f"Comparing local vs Railway data to identify my-club page failures...")
    
    try:
        # Connect to both databases
        print("\n🔌 Connecting to databases...")
        local_conn = connect_to_db(LOCAL_URL)
        railway_conn = connect_to_db(RAILWAY_URL)
        print("   ✅ Connected to both local and Railway databases")
        
        # Test general data availability
        test_general_data_availability(local_conn, railway_conn)
        
        # Test user session data quality
        test_user_session_data(local_conn, railway_conn)
        
        # Get a sample user for testing
        test_user = test_sample_user_data(local_conn, railway_conn)
        
        if test_user:
            # Test specific my-club data queries
            test_recent_matches_query(local_conn, railway_conn, test_user)
            test_series_stats_query(local_conn, railway_conn, test_user)
            test_player_streaks_data(local_conn, railway_conn, test_user)
        
        print(f"\n🎉 DIAGNOSTIC COMPLETE")
        print(f"Check the output above to identify data differences between local and Railway.")
        
        # Close connections
        local_conn.close()
        railway_conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 