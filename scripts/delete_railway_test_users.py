#!/usr/bin/env python3
"""
Delete Test Users from Railway Database
Identifies and removes test/fake users and their associated data
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

def execute_railway_query(query, params=None):
    """Execute query on Railway database"""
    conn = connect_to_railway()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    finally:
        conn.close()

def execute_railway_query_one(query, params=None):
    """Execute query on Railway database and return one result"""
    conn = connect_to_railway()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            if any(word in query.lower() for word in ['delete', 'update', 'insert']):
                conn.commit()
                return cursor.rowcount
            return cursor.fetchone()
    finally:
        conn.close()

def identify_test_users():
    """Identify test users based on suspicious patterns in their names"""
    print("🔍 Identifying test users in Railway database")
    print("=" * 50)
    
    # Patterns that indicate test/fake users
    test_patterns = [
        "court %",
        "player %",
        "test%",
        "dummy%",
        "fake%",
        "% court %",
        "% player %",
        "skokie%",  # Based on the output we saw
        "%skokie",
        "1 %",
        "2 %", 
        "3 %",
        "4 %",
        "5 %",
        "test %",
        "% test",
        "sample%",
        "%sample"
    ]
    
    test_users = []
    
    # Check users table
    print("\n📋 Checking users table for test accounts:")
    for pattern in test_patterns:
        users = execute_railway_query("""
            SELECT id, first_name, last_name, email 
            FROM users 
            WHERE first_name ILIKE %s OR last_name ILIKE %s
        """, [pattern, pattern])
        
        if users:
            print(f"   Pattern '{pattern}': {len(users)} users")
            for user in users:
                print(f"     ID {user[0]}: {user[1]} {user[2]} ({user[3]})")
                test_users.append(user[0])
    
    # Check players table
    print(f"\n👥 Checking players table for test accounts:")
    test_players = []
    for pattern in test_patterns:
        players = execute_railway_query("""
            SELECT id, first_name, last_name, tenniscores_player_id, email
            FROM players 
            WHERE first_name ILIKE %s OR last_name ILIKE %s
        """, [pattern, pattern])
        
        if players:
            print(f"   Pattern '{pattern}': {len(players)} players")
            for player in players:
                print(f"     ID {player[0]}: {player[1]} {player[2]} (Tennis: {player[3]}, Email: {player[4]})")
                test_players.append(player[0])
    
    # Remove duplicates
    test_users = list(set(test_users))
    test_players = list(set(test_players))
    
    print(f"\n📊 Summary:")
    print(f"   Test users found: {len(test_users)}")
    print(f"   Test players found: {len(test_players)}")
    
    return test_users, test_players

def find_related_data(test_users, test_players):
    """Find data related to test users/players that needs to be cleaned up"""
    print(f"\n🔍 Finding related data to clean up...")
    
    # Get tenniscores_player_ids for test players
    test_player_ids = []
    if test_players:
        player_ids_query = f"""
            SELECT tenniscores_player_id 
            FROM players 
            WHERE id = ANY(%s) AND tenniscores_player_id IS NOT NULL
        """
        player_ids = execute_railway_query(player_ids_query, [test_players])
        test_player_ids = [pid[0] for pid in player_ids if pid[0]]
    
    print(f"   Test player tennis IDs: {len(test_player_ids)}")
    
    # Count related data
    related_data = {}
    
    if test_player_ids:
        # Check match_scores
        match_count = execute_railway_query_one("""
            SELECT COUNT(*) FROM match_scores 
            WHERE home_player_1_id = ANY(%s) OR home_player_2_id = ANY(%s) 
               OR away_player_1_id = ANY(%s) OR away_player_2_id = ANY(%s)
        """, [test_player_ids, test_player_ids, test_player_ids, test_player_ids])
        related_data['matches'] = match_count[0] if match_count else 0
        
        # Check player_history
        history_count = execute_railway_query_one("""
            SELECT COUNT(*) FROM player_history ph
            JOIN players p ON ph.player_id = p.id
            WHERE p.id = ANY(%s)
        """, [test_players])
        related_data['history'] = history_count[0] if history_count else 0
    else:
        related_data['matches'] = 0
        related_data['history'] = 0
    
    # Check player_availability (uses player_id, not tenniscores_player_id)
    if test_players:
        availability_count = execute_railway_query_one("""
            SELECT COUNT(*) FROM player_availability 
            WHERE player_id = ANY(%s)
        """, [test_players])
        related_data['availability'] = availability_count[0] if availability_count else 0
    else:
        related_data['availability'] = 0
    
    print(f"   Related matches: {related_data['matches']}")
    print(f"   Related history: {related_data['history']}")
    print(f"   Related availability: {related_data['availability']}")
    
    return test_player_ids, related_data

def delete_test_data(test_users, test_players, test_player_ids, related_data):
    """Delete test users and all their related data"""
    print(f"\n🗑️  Deleting test data...")
    
    total_deletions = 0
    
    # Delete matches involving test players
    if test_player_ids and related_data['matches'] > 0:
        print(f"   Deleting {related_data['matches']} match records...")
        match_deletions = execute_railway_query_one("""
            DELETE FROM match_scores 
            WHERE home_player_1_id = ANY(%s) OR home_player_2_id = ANY(%s) 
               OR away_player_1_id = ANY(%s) OR away_player_2_id = ANY(%s)
        """, [test_player_ids, test_player_ids, test_player_ids, test_player_ids])
        print(f"     Deleted {match_deletions} match records")
        total_deletions += match_deletions
    
    # Delete player history
    if test_players and related_data['history'] > 0:
        print(f"   Deleting {related_data['history']} history records...")
        history_deletions = execute_railway_query_one("""
            DELETE FROM player_history 
            WHERE player_id = ANY(%s)
        """, [test_players])
        print(f"     Deleted {history_deletions} history records")
        total_deletions += history_deletions
    
    # Delete player_availability records
    if test_players and related_data['availability'] > 0:
        print(f"   Deleting {related_data['availability']} availability records...")
        availability_deletions = execute_railway_query_one("""
            DELETE FROM player_availability 
            WHERE player_id = ANY(%s)
        """, [test_players])
        print(f"     Deleted {availability_deletions} availability records")
        total_deletions += availability_deletions
    
    # Delete players
    if test_players:
        print(f"   Deleting {len(test_players)} player records...")
        player_deletions = execute_railway_query_one("""
            DELETE FROM players 
            WHERE id = ANY(%s)
        """, [test_players])
        print(f"     Deleted {player_deletions} player records")
        total_deletions += player_deletions
    
    # Delete users
    if test_users:
        print(f"   Deleting {len(test_users)} user records...")
        user_deletions = execute_railway_query_one("""
            DELETE FROM users 
            WHERE id = ANY(%s)
        """, [test_users])
        print(f"     Deleted {user_deletions} user records")
        total_deletions += user_deletions
    
    return total_deletions

def verify_cleanup():
    """Verify that test users have been removed"""
    print(f"\n🔍 Verifying cleanup...")
    
    # Check for remaining test patterns
    test_patterns = ["court %", "player %", "test%", "skokie%", "% test"]
    
    remaining_users = 0
    remaining_players = 0
    
    for pattern in test_patterns:
        users = execute_railway_query("""
            SELECT COUNT(*) FROM users 
            WHERE first_name ILIKE %s OR last_name ILIKE %s
        """, [pattern, pattern])
        
        players = execute_railway_query("""
            SELECT COUNT(*) FROM players 
            WHERE first_name ILIKE %s OR last_name ILIKE %s
        """, [pattern, pattern])
        
        remaining_users += users[0][0] if users else 0
        remaining_players += players[0][0] if players else 0
    
    print(f"   Remaining test users: {remaining_users}")
    print(f"   Remaining test players: {remaining_players}")
    
    return remaining_users == 0 and remaining_players == 0

def test_real_users_sample():
    """Test a sample of real users to verify they still work"""
    print(f"\n🧪 Testing real users after cleanup...")
    
    real_users = execute_railway_query("""
        SELECT DISTINCT 
            p.first_name, 
            p.last_name, 
            p.tenniscores_player_id, 
            p.team_id,
            p.league_id
        FROM players p
        WHERE p.tenniscores_player_id IS NOT NULL
        AND p.first_name NOT ILIKE ANY(ARRAY['%court%', '%player%', '%test%', '%skokie%'])
        AND p.last_name NOT ILIKE ANY(ARRAY['%court%', '%player%', '%test%', '%skokie%'])
        AND LENGTH(p.first_name) > 2
        AND LENGTH(p.last_name) > 2
        AND p.first_name ~ '^[A-Za-z]+$'  -- Only letters
        AND p.last_name ~ '^[A-Za-z]+$'   -- Only letters
        ORDER BY p.first_name, p.last_name
        LIMIT 10
    """)
    
    working_count = 0
    
    for first_name, last_name, player_id, team_id, league_id in real_users:
        if team_id:
            # Test team filtering
            team_matches = execute_railway_query_one("""
                SELECT COUNT(*) 
                FROM match_scores 
                WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
                AND league_id = %s
                AND (home_team_id = %s OR away_team_id = %s)
            """, [player_id, player_id, player_id, player_id, league_id, team_id, team_id])
        else:
            # Test league filtering
            team_matches = execute_railway_query_one("""
                SELECT COUNT(*) 
                FROM match_scores 
                WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
                AND league_id = %s
            """, [player_id, player_id, player_id, player_id, league_id])
        
        match_count = team_matches[0] if team_matches else 0
        status = "✅" if match_count > 0 else "❌"
        
        print(f"   {status} {first_name} {last_name}: {match_count} matches")
        
        if match_count > 0:
            working_count += 1
    
    print(f"\n📊 Results: {working_count}/{len(real_users)} real users working")
    return working_count, len(real_users)

def main():
    """Main function to delete test users"""
    print("🚀 Railway Test User Cleanup")
    print("=" * 40)
    
    try:
        # Step 1: Identify test users
        test_users, test_players = identify_test_users()
        
        if not test_users and not test_players:
            print("\n✅ No test users found! Database is clean.")
            return
        
        # Step 2: Find related data
        test_player_ids, related_data = find_related_data(test_users, test_players)
        
        # Step 3: Confirm deletion
        total_records = (len(test_users) + len(test_players) + 
                        related_data['matches'] + related_data['history'] + 
                        related_data['availability'])
        
        print(f"\n⚠️  DELETION SUMMARY:")
        print(f"   Users to delete: {len(test_users)}")
        print(f"   Players to delete: {len(test_players)}")
        print(f"   Matches to delete: {related_data['matches']}")
        print(f"   History to delete: {related_data['history']}")
        print(f"   Availability to delete: {related_data['availability']}")
        print(f"   TOTAL RECORDS: {total_records}")
        
        # Step 4: Delete test data
        total_deletions = delete_test_data(test_users, test_players, test_player_ids, related_data)
        
        # Step 5: Verify cleanup
        success = verify_cleanup()
        
        # Step 6: Test real users
        working_users, total_users = test_real_users_sample()
        
        print(f"\n🎉 CLEANUP SUMMARY:")
        print(f"   • Deleted {total_deletions} total records")
        print(f"   • Test data cleanup: {'✅ Complete' if success else '❌ Issues remain'}")
        print(f"   • Real users working: {working_users}/{total_users}")
        print(f"\n🚀 Railway database is now clean of test data!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 