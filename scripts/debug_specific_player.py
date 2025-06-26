#!/usr/bin/env python3
"""
Debug Specific Player Data
Analyzes why a specific player shows sparse data on Railway but works locally
"""

import psycopg2
from urllib.parse import urlparse
import base64

LOCAL_URL = "postgresql://postgres:postgres@localhost:5432/rally"
RAILWAY_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

# The specific player ID reported as having issues
PROBLEM_PLAYER_ID = "nndz-WkMrK3didjlnUT09"

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

def decode_player_id(encoded_id):
    """Try to decode the player ID"""
    try:
        decoded = base64.b64decode(encoded_id + '==').decode('utf-8')
        print(f"   🔍 Decoded player ID: '{encoded_id}' → '{decoded}'")
        return decoded
    except Exception as e:
        print(f"   ⚠️ Could not decode player ID: {e}")
        return None

def analyze_player_records(conn, db_name, player_id):
    """Analyze player records for the given ID"""
    print(f"\n📊 PLAYER RECORDS - {db_name}")
    print("=" * 60)
    
    # Try to find player by tenniscores_player_id (both encoded and decoded)
    decoded_id = decode_player_id(player_id)
    
    search_ids = [player_id]
    if decoded_id:
        search_ids.append(decoded_id)
    
    for search_id in search_ids:
        print(f"\n   🔍 Searching for player ID: '{search_id}'")
        
        players = execute_query(conn, """
            SELECT p.id, p.first_name, p.last_name, p.tenniscores_player_id,
                   p.league_id, p.club_id, p.series_id, p.is_active,
                   l.league_id as league_string, l.league_name,
                   c.name as club_name, s.name as series_name
            FROM players p
            LEFT JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.tenniscores_player_id = %s
            ORDER BY p.id DESC
        """, [search_id])
        
        if players:
            print(f"      ✅ Found {len(players)} player record(s):")
            for player in players:
                print(f"         - DB ID {player['id']}: {player['first_name']} {player['last_name']}")
                print(f"           League: {player['league_id']} ({player['league_string']}) - {player['league_name']}")
                print(f"           Club: {player['club_name']}, Series: {player['series_name']}")
                print(f"           Active: {player['is_active']}")
            return players
        else:
            print(f"      ❌ No player records found")
    
    return []

def analyze_user_associations(conn, db_name, player_id):
    """Analyze user associations for the player"""
    print(f"\n📊 USER ASSOCIATIONS - {db_name}")
    print("=" * 60)
    
    decoded_id = decode_player_id(player_id)
    search_ids = [player_id]
    if decoded_id:
        search_ids.append(decoded_id)
    
    for search_id in search_ids:
        print(f"\n   🔍 Searching for user associations with player ID: '{search_id}'")
        
        associations = execute_query(conn, """
            SELECT u.id, u.email, u.first_name, u.last_name,
                   upa.is_primary, upa.created_at,
                   p.id as player_db_id
            FROM user_player_associations upa
            JOIN users u ON upa.user_id = u.id
            JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
            WHERE upa.tenniscores_player_id = %s
            ORDER BY upa.is_primary DESC, upa.created_at DESC
        """, [search_id])
        
        if associations:
            print(f"      ✅ Found {len(associations)} user association(s):")
            for assoc in associations:
                primary_text = "PRIMARY" if assoc['is_primary'] else "Secondary"
                print(f"         - User: {assoc['first_name']} {assoc['last_name']} ({assoc['email']})")
                print(f"           Association: {primary_text}, Created: {assoc['created_at']}")
                print(f"           Player DB ID: {assoc['player_db_id']}")
            return associations
        else:
            print(f"      ❌ No user associations found")
    
    return []

def test_match_data_access(conn, db_name, player_records):
    """Test match data access for the player"""
    print(f"\n📊 MATCH DATA ACCESS - {db_name}")
    print("=" * 60)
    
    if not player_records:
        print("   ❌ No player records to test")
        return
    
    for player in player_records:
        print(f"\n   🔍 Testing match access for {player['first_name']} {player['last_name']}:")
        print(f"      League: {player['league_id']}, Club: {player['club_name']}")
        
        if not player['club_name'] or not player['league_id']:
            print("      ⚠️ Missing club or league data")
            continue
        
        # Test match filtering (same logic as my-club page)
        match_count = execute_query_one(conn, """
            SELECT COUNT(*) as count
            FROM match_scores ms
            WHERE ms.league_id = %s
            AND (ms.home_team LIKE %s OR ms.away_team LIKE %s)
        """, [player['league_id'], f"%{player['club_name']}%", f"%{player['club_name']}%"])
        
        # Test total club matches (no league filter)
        total_matches = execute_query_one(conn, """
            SELECT COUNT(*) as count
            FROM match_scores ms
            WHERE (ms.home_team LIKE %s OR ms.away_team LIKE %s)
        """, [f"%{player['club_name']}%", f"%{player['club_name']}%"])
        
        print(f"      📊 League-filtered matches: {match_count['count']}")
        print(f"      📊 Total club matches: {total_matches['count']}")
        
        if match_count['count'] == 0 and total_matches['count'] > 0:
            print("      🚨 ISSUE: League filtering is blocking access to match data!")
        elif match_count['count'] > 0:
            print("      ✅ Match data access looks good")

def compare_session_data_creation(local_conn, railway_conn, player_id):
    """Compare what session data would be created for this player"""
    print(f"\n📊 SESSION DATA COMPARISON")
    print("=" * 60)
    
    decoded_id = decode_player_id(player_id)
    search_ids = [player_id]
    if decoded_id:
        search_ids.append(decoded_id)
    
    for search_id in search_ids:
        print(f"\n   🔍 Comparing session data creation for player ID: '{search_id}'")
        
        for conn, db_name in [(local_conn, "LOCAL"), (railway_conn, "RAILWAY")]:
            print(f"\n   📊 {db_name} session data:")
            
            # Simulate session data creation
            session_query = """
                SELECT u.email, u.first_name, u.last_name,
                       l.id as league_db_id, l.league_id, l.league_name,
                       c.name as club_name, s.name as series_name,
                       p.tenniscores_player_id
                FROM users u
                JOIN user_player_associations upa ON u.id = upa.user_id AND upa.is_primary = true
                JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
                JOIN leagues l ON p.league_id = l.id
                JOIN clubs c ON p.club_id = c.id
                JOIN series s ON p.series_id = s.id
                WHERE p.tenniscores_player_id = %s
                LIMIT 1
            """
            
            session_data = execute_query_one(conn, session_query, [search_id])
            
            if session_data:
                print(f"      ✅ Would create session:")
                print(f"         club: '{session_data['club_name']}'")
                print(f"         series: '{session_data['series_name']}'") 
                print(f"         league_id: {session_data['league_db_id']}")
                print(f"         league_name: '{session_data['league_name']}'")
            else:
                print(f"      ❌ No session data could be created")

def main():
    """Main debugging function"""
    print("🚀 SPECIFIC PLAYER DEBUG")
    print("=" * 50)
    print(f"Debugging player ID: {PROBLEM_PLAYER_ID}")
    
    try:
        # Connect to both databases
        print("\n🔌 Connecting to databases...")
        local_conn = connect_to_db(LOCAL_URL)
        railway_conn = connect_to_db(RAILWAY_URL)
        print("   ✅ Connected to both local and Railway databases")
        
        # Analyze player records
        local_players = analyze_player_records(local_conn, "LOCAL", PROBLEM_PLAYER_ID)
        railway_players = analyze_player_records(railway_conn, "RAILWAY", PROBLEM_PLAYER_ID)
        
        # Analyze user associations
        local_associations = analyze_user_associations(local_conn, "LOCAL", PROBLEM_PLAYER_ID)
        railway_associations = analyze_user_associations(railway_conn, "RAILWAY", PROBLEM_PLAYER_ID)
        
        # Test match data access
        test_match_data_access(local_conn, "LOCAL", local_players)
        test_match_data_access(railway_conn, "RAILWAY", railway_players)
        
        # Compare session data creation
        compare_session_data_creation(local_conn, railway_conn, PROBLEM_PLAYER_ID)
        
        # Summary
        print(f"\n🎯 DIAGNOSIS SUMMARY")
        print("=" * 60)
        print(f"   📊 Player records:")
        print(f"      Local: {len(local_players)} records")
        print(f"      Railway: {len(railway_players)} records")
        
        print(f"   📊 User associations:")
        print(f"      Local: {len(local_associations)} associations")
        print(f"      Railway: {len(railway_associations)} associations")
        
        # Close connections
        local_conn.close()
        railway_conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 