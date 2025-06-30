#!/usr/bin/env python3
"""
Fix Railway User Player Associations
Identifies and fixes missing user-player associations that cause my-club page failures
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

def execute_update(conn, query, params=None):
    """Execute update query and return affected rows"""
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            count = cursor.rowcount
            conn.commit()
            return count
    except Exception as e:
        print(f"   ❌ Update failed: {e}")
        conn.rollback()
        return 0

def diagnose_user_associations(conn):
    """Diagnose user-player association issues"""
    print("🔍 DIAGNOSING USER-PLAYER ASSOCIATIONS")
    print("=" * 60)
    
    # Check users without any associations
    users_without_associations = execute_query(conn, """
        SELECT u.id, u.email, u.first_name, u.last_name
        FROM users u
        LEFT JOIN user_player_associations upa ON u.id = upa.user_id
        WHERE upa.user_id IS NULL
        ORDER BY u.last_login DESC
    """)
    
    print(f"   👤 Users without ANY player associations: {len(users_without_associations)}")
    for user in users_without_associations[:5]:  # Show first 5
        print(f"      - {user['first_name']} {user['last_name']} ({user['email']})")
    if len(users_without_associations) > 5:
        print(f"      ... and {len(users_without_associations) - 5} more")
    
    # Check users without primary associations
    users_without_primary = execute_query(conn, """
        SELECT u.id, u.email, u.first_name, u.last_name,
               COUNT(upa.user_id) as total_associations,
               COUNT(CASE WHEN upa.is_primary = true THEN 1 END) as primary_associations
        FROM users u
        LEFT JOIN user_player_associations upa ON u.id = upa.user_id
        GROUP BY u.id, u.email, u.first_name, u.last_name
        HAVING COUNT(CASE WHEN upa.is_primary = true THEN 1 END) = 0
        ORDER BY u.last_login DESC
    """)
    
    print(f"   🎯 Users without PRIMARY player association: {len(users_without_primary)}")
    for user in users_without_primary[:5]:  # Show first 5
        print(f"      - {user['first_name']} {user['last_name']} ({user['total_associations']} associations, 0 primary)")
    if len(users_without_primary) > 5:
        print(f"      ... and {len(users_without_primary) - 5} more")
    
    # Check total association stats
    association_stats = execute_query_one(conn, """
        SELECT 
            COUNT(DISTINCT u.id) as total_users,
            COUNT(DISTINCT upa.user_id) as users_with_associations,
            COUNT(DISTINCT CASE WHEN upa.is_primary = true THEN upa.user_id END) as users_with_primary,
            COUNT(upa.user_id) as total_associations
        FROM users u
        LEFT JOIN user_player_associations upa ON u.id = upa.user_id
    """)
    
    print(f"\n📊 Association Statistics:")
    print(f"   Total users: {association_stats['total_users']}")
    print(f"   Users with associations: {association_stats['users_with_associations']}")
    print(f"   Users with primary associations: {association_stats['users_with_primary']}")
    print(f"   Total associations: {association_stats['total_associations']}")
    
    return users_without_associations, users_without_primary

def find_matching_players_for_users(conn, users_list):
    """Find matching players for users without associations"""
    print(f"\n🔍 FINDING MATCHING PLAYERS")
    print("=" * 60)
    
    potential_matches = []
    
    for user in users_list[:10]:  # Process first 10 for now
        print(f"\n   🔍 Looking for matches for {user['first_name']} {user['last_name']}...")
        
        # Try exact name match
        exact_matches = execute_query(conn, """
            SELECT id, first_name, last_name, tenniscores_player_id, 
                   c.name as club_name, s.name as series_name, l.league_name
            FROM players p
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id  
            LEFT JOIN leagues l ON p.league_id = l.id
            WHERE LOWER(p.first_name) = LOWER(%s) 
            AND LOWER(p.last_name) = LOWER(%s)
            AND p.is_active = true
            ORDER BY p.id DESC
            LIMIT 5
        """, [user['first_name'], user['last_name']])
        
        if exact_matches:
            print(f"      ✅ Found {len(exact_matches)} exact matches:")
            for match in exact_matches:
                print(f"         - {match['first_name']} {match['last_name']} at {match['club_name']} ({match['series_name']})")
                potential_matches.append({
                    'user': user,
                    'player': match,
                    'match_type': 'exact'
                })
        else:
            print(f"      ❌ No exact matches found")
    
    return potential_matches

def create_missing_associations(conn, potential_matches):
    """Create missing user-player associations"""
    print(f"\n🔧 CREATING MISSING ASSOCIATIONS")
    print("=" * 60)
    
    associations_created = 0
    
    for match in potential_matches:
        user = match['user']
        player = match['player']
        
        print(f"\n   🔗 Creating association: {user['first_name']} {user['last_name']} → Player ID {player['id']}")
        
        # Check if association already exists
        existing = execute_query_one(conn, """
            SELECT id FROM user_player_associations 
            WHERE user_id = %s AND tenniscores_player_id = %s
        """, [user['id'], player['tenniscores_player_id']])
        
        if existing:
            print(f"      ⚠️ Association already exists")
            continue
        
        # Create the association
        insert_result = execute_update(conn, """
            INSERT INTO user_player_associations (user_id, tenniscores_player_id, is_primary, created_at)
            VALUES (%s, %s, true, NOW())
        """, [user['id'], player['tenniscores_player_id']])
        
        if insert_result > 0:
            print(f"      ✅ Created primary association")
            associations_created += 1
        else:
            print(f"      ❌ Failed to create association")
    
    return associations_created

def test_my_club_functionality(conn):
    """Test if users can now access my-club functionality"""
    print(f"\n🧪 TESTING MY-CLUB FUNCTIONALITY")
    print("=" * 60)
    
    # Get users with primary associations
    test_users = execute_query(conn, """
        SELECT u.id, u.email, u.first_name, u.last_name,
               p.tenniscores_player_id,
               c.name as club_name,
               s.name as series_name,
               l.league_id, l.league_name
        FROM users u
        JOIN user_player_associations upa ON u.id = upa.user_id AND upa.is_primary = true
        JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN series s ON p.series_id = s.id
        LEFT JOIN leagues l ON p.league_id = l.id
        WHERE c.name IS NOT NULL AND s.name IS NOT NULL
        ORDER BY u.last_login DESC
        LIMIT 5
    """)
    
    print(f"   👥 Testing {len(test_users)} users with complete profile data...")
    
    working_count = 0
    
    for user in test_users:
        club_name = user['club_name']
        league_id = user['league_id']
        
        # Test match query (core my-club functionality)
        match_count = execute_query_one(conn, """
            SELECT COUNT(*) as count
            FROM match_scores ms
            WHERE ms.league_id = (SELECT id FROM leagues WHERE league_id = %s)
            AND (ms.home_team LIKE %s OR ms.away_team LIKE %s)
        """, [league_id, f"%{club_name}%", f"%{club_name}%"])
        
        matches = match_count['count'] if match_count else 0
        status = "✅" if matches > 0 else "❌"
        
        print(f"   {status} {user['first_name']} {user['last_name']} ({club_name}): {matches} matches")
        
        if matches > 0:
            working_count += 1
    
    print(f"\n📊 My-Club Test Results: {working_count}/{len(test_users)} users have working my-club functionality")
    return working_count, len(test_users)

def main():
    """Main function to fix user association issues"""
    print("🚀 RAILWAY USER ASSOCIATION FIX")
    print("=" * 50)
    print("Fixing missing user-player associations causing my-club page failures...")
    
    try:
        # Connect to Railway
        print("\n🔌 Connecting to Railway database...")
        conn = connect_to_railway()
        print("   ✅ Connected successfully")
        
        # Step 1: Diagnose issues
        users_without_associations, users_without_primary = diagnose_user_associations(conn)
        
        # Step 2: Find potential matches
        if users_without_associations:
            potential_matches = find_matching_players_for_users(conn, users_without_associations)
            
            if potential_matches:
                # Step 3: Create associations
                created_count = create_missing_associations(conn, potential_matches)
                print(f"\n✅ Created {created_count} new user-player associations")
            else:
                print(f"\n⚠️ No suitable player matches found")
        else:
            print(f"\n✅ All users already have player associations")
        
        # Step 4: Test functionality
        working_users, total_users = test_my_club_functionality(conn)
        
        print(f"\n🎉 SUMMARY:")
        print(f"   • Users without associations: {len(users_without_associations)}")
        print(f"   • Users without primary: {len(users_without_primary)}")
        if 'created_count' in locals():
            print(f"   • New associations created: {created_count}")
        print(f"   • Working my-club users: {working_users}/{total_users}")
        print(f"\n🚀 Railway my-club page should now work for more users!")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 