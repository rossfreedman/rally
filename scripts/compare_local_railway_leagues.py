#!/usr/bin/env python3
"""
Compare Local vs Railway League Mappings
Analyze how league_ids are mapped in the working local database vs broken Railway database
"""

import psycopg2
from urllib.parse import urlparse

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

def analyze_leagues_table(conn, db_name):
    """Analyze the leagues table structure and data"""
    print(f"\n📊 LEAGUES TABLE - {db_name}")
    print("=" * 60)
    
    leagues = execute_query(conn, """
        SELECT id, league_id, league_name 
        FROM leagues 
        ORDER BY id
    """)
    
    if leagues:
        print(f"   Found {len(leagues)} leagues:")
        for league in leagues:
            print(f"      - ID {league['id']}: '{league['league_id']}' ({league['league_name']})")
    else:
        print(f"   ❌ No leagues found or table doesn't exist")
    
    return leagues

def analyze_match_scores_leagues(conn, db_name):
    """Analyze which league_ids are actually used in match_scores"""
    print(f"\n📊 MATCH_SCORES LEAGUE_IDS - {db_name}")
    print("=" * 60)
    
    match_leagues = execute_query(conn, """
        SELECT league_id, COUNT(*) as match_count,
               MIN(match_date) as earliest_match,
               MAX(match_date) as latest_match
        FROM match_scores 
        WHERE league_id IS NOT NULL
        GROUP BY league_id
        ORDER BY league_id
    """)
    
    if match_leagues:
        print(f"   Found match data with {len(match_leagues)} different league_ids:")
        for item in match_leagues:
            print(f"      - League ID {item['league_id']}: {item['match_count']} matches ({item['earliest_match']} to {item['latest_match']})")
    else:
        print(f"   ❌ No match data found or table doesn't exist")
    
    return match_leagues

def analyze_sample_teams(conn, db_name, league_ids):
    """Analyze sample team names for each league_id"""
    print(f"\n📊 SAMPLE TEAMS BY LEAGUE - {db_name}")
    print("=" * 60)
    
    for league_id in league_ids[:3]:  # Check top 3 league_ids
        print(f"\n   🔍 League ID {league_id}:")
        
        sample_teams = execute_query(conn, """
            SELECT home_team, away_team
            FROM match_scores 
            WHERE league_id = %s
            ORDER BY match_date DESC
            LIMIT 10
        """, [league_id])
        
        team_names = set()
        for match in sample_teams:
            if match['home_team']:
                team_names.add(match['home_team'])
            if match['away_team']:
                team_names.add(match['away_team'])
        
        for team in sorted(list(team_names))[:5]:
            print(f"         - {team}")

def analyze_user_associations(conn, db_name):
    """Analyze how users are associated with leagues"""
    print(f"\n📊 USER-LEAGUE ASSOCIATIONS - {db_name}")
    print("=" * 60)
    
    # Check if we have the new association structure
    associations = execute_query(conn, """
        SELECT u.email, u.first_name, u.last_name,
               l.id as league_db_id, l.league_id, l.league_name,
               c.name as club_name, s.name as series_name
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id AND upa.is_primary = true
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        JOIN leagues l ON p.league_id = l.id
        JOIN clubs c ON p.club_id = c.id
        JOIN series s ON p.series_id = s.id
        ORDER BY u.last_login DESC
        LIMIT 5
    """)
    
    if associations:
        print(f"   Found {len(associations)} users with primary league associations:")
        for user in associations:
            print(f"      - {user['first_name']} {user['last_name']} ({user['email']})")
            print(f"        → League: {user['league_db_id']} ({user['league_id']}) - {user['league_name']}")
            print(f"        → Club: {user['club_name']}, Series: {user['series_name']}")
    else:
        print(f"   ⚠️ No user-league associations found (may use old schema)")
        
        # Try the old direct user schema
        old_users = execute_query(conn, """
            SELECT email, first_name, last_name, club_id, series_id, league_id
            FROM users
            WHERE club_id IS NOT NULL OR series_id IS NOT NULL OR league_id IS NOT NULL
            LIMIT 5
        """)
        
        if old_users:
            print(f"   Found {len(old_users)} users with direct league/club data (old schema):")
            for user in old_users:
                print(f"      - {user['first_name']} {user['last_name']}: league_id={user['league_id']}, club_id={user['club_id']}")

def test_my_club_functionality(conn, db_name):
    """Test the my-club page functionality"""
    print(f"\n🧪 MY-CLUB FUNCTIONALITY TEST - {db_name}")
    print("=" * 60)
    
    # Test with a known club (Tennaqua)
    test_club = "Tennaqua"
    
    # Method 1: Count all matches for this club (no league filter)
    total_matches = execute_query_one(conn, """
        SELECT COUNT(*) as count
        FROM match_scores
        WHERE home_team LIKE %s OR away_team LIKE %s
    """, [f"%{test_club}%", f"%{test_club}%"])
    
    print(f"   📊 {test_club} total matches (no league filter): {total_matches['count']}")
    
    # Method 2: Test league filtering for each league_id
    league_ids = execute_query(conn, """
        SELECT DISTINCT league_id, COUNT(*) as count
        FROM match_scores 
        WHERE league_id IS NOT NULL
        AND (home_team LIKE %s OR away_team LIKE %s)
        GROUP BY league_id
        ORDER BY count DESC
    """, [f"%{test_club}%", f"%{test_club}%"])
    
    if league_ids:
        print(f"   📊 {test_club} matches by league_id:")
        for item in league_ids:
            print(f"      - League {item['league_id']}: {item['count']} matches")
    else:
        print(f"   ❌ No league-filtered matches found for {test_club}")

def main():
    """Main comparison function"""
    print("🚀 LOCAL vs RAILWAY LEAGUE MAPPING COMPARISON")
    print("=" * 70)
    print("Comparing working local database with broken Railway database...")
    
    try:
        # Connect to both databases
        print("\n🔌 Connecting to databases...")
        local_conn = connect_to_db(LOCAL_URL)
        railway_conn = connect_to_db(RAILWAY_URL)
        print("   ✅ Connected to both local and Railway databases")
        
        # Analyze leagues table in both
        local_leagues = analyze_leagues_table(local_conn, "LOCAL")
        railway_leagues = analyze_leagues_table(railway_conn, "RAILWAY")
        
        # Analyze match_scores league usage
        local_match_leagues = analyze_match_scores_leagues(local_conn, "LOCAL")
        railway_match_leagues = analyze_match_scores_leagues(railway_conn, "RAILWAY")
        
        # Get league_ids for sampling
        local_league_ids = [item['league_id'] for item in local_match_leagues] if local_match_leagues else []
        railway_league_ids = [item['league_id'] for item in railway_match_leagues] if railway_match_leagues else []
        
        # Analyze sample teams
        if local_league_ids:
            analyze_sample_teams(local_conn, "LOCAL", local_league_ids)
        
        if railway_league_ids:
            analyze_sample_teams(railway_conn, "RAILWAY", railway_league_ids)
        
        # Analyze user associations
        analyze_user_associations(local_conn, "LOCAL")
        analyze_user_associations(railway_conn, "RAILWAY")
        
        # Test my-club functionality
        test_my_club_functionality(local_conn, "LOCAL")
        test_my_club_functionality(railway_conn, "RAILWAY")
        
        # Summary comparison
        print(f"\n🎯 COMPARISON SUMMARY")
        print("=" * 60)
        print(f"   📊 Leagues table:")
        print(f"      Local: {len(local_leagues) if local_leagues else 0} leagues")
        print(f"      Railway: {len(railway_leagues) if railway_leagues else 0} leagues")
        
        print(f"   📊 Match data league_ids:")
        print(f"      Local: {local_league_ids if local_league_ids else 'None'}")
        print(f"      Railway: {railway_league_ids if railway_league_ids else 'None'}")
        
        # Close connections
        local_conn.close()
        railway_conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 