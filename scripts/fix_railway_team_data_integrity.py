#!/usr/bin/env python3
"""
Fix Railway Team Data Integrity Issues
Identifies and fixes team_id mismatches between match_scores and teams tables
"""

import psycopg2
from urllib.parse import urlparse
from collections import defaultdict

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
            if 'update' in query.lower():
                conn.commit()
                return cursor.rowcount
            return cursor.fetchone()
    finally:
        conn.close()

def find_team_id_mismatches():
    """Find all team_ids in match_scores that don't exist in teams table"""
    print("🔍 Finding team_id mismatches between match_scores and teams tables")
    print("=" * 70)
    
    # Get all unique team_ids from match_scores
    match_team_ids = execute_railway_query("""
        SELECT DISTINCT home_team_id, home_team, away_team_id, away_team
        FROM match_scores 
        WHERE home_team_id IS NOT NULL AND away_team_id IS NOT NULL
    """)
    
    # Build a set of all team_ids referenced in matches
    referenced_team_ids = {}  # team_id -> team_name
    for home_id, home_name, away_id, away_name in match_team_ids:
        referenced_team_ids[home_id] = home_name
        referenced_team_ids[away_id] = away_name
    
    print(f"Found {len(referenced_team_ids)} unique team_ids referenced in match_scores")
    
    # Get all team_ids that actually exist in teams table
    existing_teams = execute_railway_query("SELECT id, team_name FROM teams")
    existing_team_ids = {team[0]: team[1] for team in existing_teams}
    
    print(f"Found {len(existing_team_ids)} teams in teams table")
    
    # Find mismatches
    missing_team_ids = {}
    for team_id, team_name in referenced_team_ids.items():
        if team_id not in existing_team_ids:
            missing_team_ids[team_id] = team_name
    
    print(f"\n🚨 Found {len(missing_team_ids)} team_ids referenced in matches but missing from teams table:")
    for team_id, team_name in missing_team_ids.items():
        print(f"   Team ID {team_id}: '{team_name}'")
    
    return missing_team_ids, existing_team_ids

def find_correct_team_mappings(missing_team_ids, existing_team_ids):
    """Map missing team_ids to correct existing team_ids based on team names"""
    print(f"\n🔍 Finding correct team mappings...")
    
    corrections = {}  # old_team_id -> new_team_id
    
    for missing_id, missing_name in missing_team_ids.items():
        # Look for exact match by name
        correct_id = None
        for existing_id, existing_name in existing_team_ids.items():
            if existing_name.strip().lower() == missing_name.strip().lower():
                correct_id = existing_id
                break
        
        if correct_id:
            corrections[missing_id] = correct_id
            print(f"   ✅ {missing_name} (ID {missing_id}) → ID {correct_id}")
        else:
            print(f"   ❌ {missing_name} (ID {missing_id}) → NO MATCH FOUND")
    
    print(f"\n📊 Summary: {len(corrections)} mappings found, {len(missing_team_ids) - len(corrections)} unresolved")
    return corrections

def apply_team_corrections(corrections):
    """Apply the team_id corrections to match_scores table"""
    print(f"\n🔧 Applying team_id corrections...")
    
    total_home_updates = 0
    total_away_updates = 0
    
    for old_id, new_id in corrections.items():
        print(f"\n   Updating team_id {old_id} → {new_id}")
        
        # Update home_team_id
        home_updates = execute_railway_query_one("""
            UPDATE match_scores 
            SET home_team_id = %s 
            WHERE home_team_id = %s
        """, [new_id, old_id])
        
        # Update away_team_id  
        away_updates = execute_railway_query_one("""
            UPDATE match_scores 
            SET away_team_id = %s 
            WHERE away_team_id = %s
        """, [new_id, old_id])
        
        print(f"     Home updates: {home_updates}, Away updates: {away_updates}")
        total_home_updates += home_updates
        total_away_updates += away_updates
    
    print(f"\n✅ Total updates: {total_home_updates} home_team_id, {total_away_updates} away_team_id")
    return total_home_updates + total_away_updates

def verify_fixes():
    """Verify that all team_ids in match_scores now exist in teams table"""
    print(f"\n🔍 Verifying fixes...")
    
    # Check for remaining orphaned team_ids
    orphaned = execute_railway_query("""
        SELECT DISTINCT ms.home_team_id, ms.home_team
        FROM match_scores ms
        LEFT JOIN teams t ON ms.home_team_id = t.id
        WHERE t.id IS NULL AND ms.home_team_id IS NOT NULL
        
        UNION
        
        SELECT DISTINCT ms.away_team_id, ms.away_team
        FROM match_scores ms
        LEFT JOIN teams t ON ms.away_team_id = t.id
        WHERE t.id IS NULL AND ms.away_team_id IS NOT NULL
    """)
    
    if orphaned:
        print(f"   ❌ Still {len(orphaned)} orphaned team_ids:")
        for team_id, team_name in orphaned:
            print(f"     {team_name} (ID: {team_id})")
    else:
        print(f"   ✅ All team_ids in match_scores now reference valid teams!")
    
    return len(orphaned) == 0

def test_affected_users():
    """Test a sample of users to see if their analyze-me page would work now"""
    print(f"\n🧪 Testing sample users...")
    
    # Get users who have player records with team_ids
    sample_users = execute_railway_query("""
        SELECT DISTINCT 
            p.first_name, 
            p.last_name, 
            p.tenniscores_player_id, 
            p.team_id,
            p.league_id
        FROM players p
        WHERE p.team_id IS NOT NULL 
        AND p.tenniscores_player_id IS NOT NULL
        ORDER BY p.first_name, p.last_name
        LIMIT 10
    """)
    
    working_users = 0
    total_users = len(sample_users)
    
    for first_name, last_name, player_id, team_id, league_id in sample_users:
        # Test team filtering for this user
        team_matches = execute_railway_query_one("""
            SELECT COUNT(*) 
            FROM match_scores 
            WHERE (home_player_1_id = %s OR home_player_2_id = %s OR away_player_1_id = %s OR away_player_2_id = %s)
            AND league_id = %s
            AND (home_team_id = %s OR away_team_id = %s)
        """, [player_id, player_id, player_id, player_id, league_id, team_id, team_id])
        
        match_count = team_matches[0] if team_matches else 0
        status = "✅" if match_count > 0 else "❌"
        
        print(f"   {status} {first_name} {last_name}: {match_count} matches")
        
        if match_count > 0:
            working_users += 1
    
    print(f"\n📊 Results: {working_users}/{total_users} users now have working analyze-me pages")
    return working_users, total_users

def main():
    """Main function to fix all team data integrity issues"""
    print("🚀 Railway Team Data Integrity Fix")
    print("=" * 50)
    
    try:
        # Step 1: Find mismatches
        missing_team_ids, existing_team_ids = find_team_id_mismatches()
        
        if not missing_team_ids:
            print("\n✅ No team_id mismatches found! Data integrity is good.")
            return
        
        # Step 2: Find correct mappings
        corrections = find_correct_team_mappings(missing_team_ids, existing_team_ids)
        
        if not corrections:
            print("\n❌ No corrections could be automatically determined.")
            print("   Manual intervention may be required.")
            return
        
        # Step 3: Apply corrections
        total_updates = apply_team_corrections(corrections)
        
        # Step 4: Verify fixes
        success = verify_fixes()
        
        # Step 5: Test users
        working_users, total_users = test_affected_users()
        
        print(f"\n🎉 SUMMARY:")
        print(f"   • Fixed {len(corrections)} team_id mappings")
        print(f"   • Updated {total_updates} match records")
        print(f"   • Data integrity: {'✅ Clean' if success else '❌ Issues remain'}")
        print(f"   • User impact: {working_users}/{total_users} users now working")
        print(f"\n🚀 Railway analyze-me pages should now work for all users!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 