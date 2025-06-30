#!/usr/bin/env python3
"""
Fix Orphaned League IDs in Match_Scores
Maps orphaned league_id references to correct existing leagues
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

def identify_orphaned_leagues(conn):
    """Identify orphaned league_ids in match_scores"""
    print("🔍 IDENTIFYING ORPHANED LEAGUE IDS")
    print("=" * 60)
    
    # Get valid league IDs
    valid_leagues = execute_query(conn, """
        SELECT id, league_id, league_name 
        FROM leagues 
        ORDER BY id
    """)
    
    valid_league_ids = {league['id']: league for league in valid_leagues}
    
    print(f"   ✅ Valid leagues in system:")
    for league in valid_leagues:
        print(f"      - {league['id']}: {league['league_id']} ({league['league_name']})")
    
    # Get league IDs actually used in match_scores
    match_leagues = execute_query(conn, """
        SELECT league_id, COUNT(*) as match_count,
               MIN(match_date) as earliest_match,
               MAX(match_date) as latest_match
        FROM match_scores 
        WHERE league_id IS NOT NULL
        GROUP BY league_id
        ORDER BY league_id
    """)
    
    print(f"\n   📊 League IDs in match_scores:")
    orphaned_leagues = []
    valid_match_data = []
    
    for item in match_leagues:
        league_id = item['league_id']
        if league_id in valid_league_ids:
            print(f"      ✅ {league_id}: {item['match_count']} matches (VALID - {valid_league_ids[league_id]['league_id']})")
            valid_match_data.append(item)
        else:
            print(f"      ❌ {league_id}: {item['match_count']} matches (ORPHANED - no league exists)")
            orphaned_leagues.append(item)
    
    total_orphaned_matches = sum(item['match_count'] for item in orphaned_leagues)
    total_valid_matches = sum(item['match_count'] for item in valid_match_data)
    
    print(f"\n   📊 Summary:")
    print(f"      Valid match data: {total_valid_matches} matches")
    print(f"      Orphaned match data: {total_orphaned_matches} matches")
    print(f"      Orphaned percentage: {(total_orphaned_matches / (total_orphaned_matches + total_valid_matches)) * 100:.1f}%")
    
    return valid_leagues, orphaned_leagues

def analyze_orphaned_data(conn, orphaned_leagues):
    """Analyze orphaned league data to determine correct mappings"""
    print(f"\n🔍 ANALYZING ORPHANED DATA FOR MAPPING CLUES")
    print("=" * 60)
    
    mappings = {}
    
    for orphaned in orphaned_leagues:
        orphaned_id = orphaned['league_id']
        match_count = orphaned['match_count']
        
        print(f"\n   🔍 Analyzing orphaned league_id {orphaned_id} ({match_count} matches)...")
        
        # Sample team names from this orphaned league
        sample_teams = execute_query(conn, """
            SELECT home_team, away_team
            FROM match_scores 
            WHERE league_id = %s
            ORDER BY match_date DESC
            LIMIT 20
        """, [orphaned_id])
        
        print(f"      Sample teams:")
        team_names = set()
        for match in sample_teams:
            if match['home_team']:
                team_names.add(match['home_team'])
            if match['away_team']:
                team_names.add(match['away_team'])
        
        # Show first 5 unique teams
        for team in sorted(list(team_names))[:5]:
            print(f"         - {team}")
        
        # Try to guess the league based on team patterns
        chicago_indicators = ['chicago', 'apta', 'cpta']
        cita_indicators = ['cita']
        womens_indicators = ['womens', 'women', 'ladies']
        
        team_text = ' '.join(team_names).lower()
        
        if any(indicator in team_text for indicator in chicago_indicators):
            suggested_league = "APTA_CHICAGO"
        elif any(indicator in team_text for indicator in cita_indicators):
            suggested_league = "CITA"
        elif any(indicator in team_text for indicator in womens_indicators):
            suggested_league = "CNSWPL"
        else:
            suggested_league = "UNKNOWN"
        
        print(f"      💡 Suggested mapping: {orphaned_id} → {suggested_league}")
        mappings[orphaned_id] = suggested_league
    
    return mappings

def create_mapping_plan(conn, mappings, valid_leagues):
    """Create a mapping plan from orphaned IDs to valid IDs"""
    print(f"\n🗺️ CREATING MAPPING PLAN")
    print("=" * 60)
    
    # Create lookup for league_id string to database ID
    league_string_to_id = {league['league_id']: league['id'] for league in valid_leagues}
    
    final_mappings = {}
    
    for orphaned_id, suggested_league_string in mappings.items():
        if suggested_league_string in league_string_to_id:
            target_id = league_string_to_id[suggested_league_string]
            final_mappings[orphaned_id] = target_id
            print(f"   ✅ {orphaned_id} → {target_id} ({suggested_league_string})")
        else:
            print(f"   ❌ {orphaned_id} → {suggested_league_string} (CANNOT MAP - league not found)")
    
    return final_mappings

def apply_mappings(conn, final_mappings):
    """Apply the league ID mappings to match_scores"""
    print(f"\n🔧 APPLYING MAPPINGS")
    print("=" * 60)
    
    total_updated = 0
    
    for orphaned_id, target_id in final_mappings.items():
        print(f"\n   🔄 Updating league_id {orphaned_id} → {target_id}...")
        
        # Count matches to be updated
        count_query = execute_query_one(conn, """
            SELECT COUNT(*) as count 
            FROM match_scores 
            WHERE league_id = %s
        """, [orphaned_id])
        
        matches_to_update = count_query['count'] if count_query else 0
        print(f"      Matches to update: {matches_to_update}")
        
        # Apply the update
        updated_count = execute_update(conn, """
            UPDATE match_scores 
            SET league_id = %s 
            WHERE league_id = %s
        """, [target_id, orphaned_id])
        
        print(f"      ✅ Updated {updated_count} matches")
        total_updated += updated_count
    
    return total_updated

def verify_fix(conn):
    """Verify that the mappings worked correctly"""
    print(f"\n🧪 VERIFYING FIX")
    print("=" * 60)
    
    # Check for remaining orphaned leagues
    remaining_orphans = execute_query(conn, """
        SELECT ms.league_id, COUNT(*) as match_count
        FROM match_scores ms
        LEFT JOIN leagues l ON ms.league_id = l.id
        WHERE l.id IS NULL AND ms.league_id IS NOT NULL
        GROUP BY ms.league_id
        ORDER BY ms.league_id
    """)
    
    if remaining_orphans:
        print(f"   ⚠️ Still {len(remaining_orphans)} orphaned league IDs:")
        for orphan in remaining_orphans:
            print(f"      - {orphan['league_id']}: {orphan['match_count']} matches")
    else:
        print(f"   ✅ No orphaned league IDs remaining!")
    
    # Test a sample user again
    test_user_matches = execute_query_one(conn, """
        SELECT COUNT(*) as count
        FROM match_scores ms
        WHERE ms.league_id = 4489  -- APTA_CHICAGO
        AND (ms.home_team LIKE '%Tennaqua%' OR ms.away_team LIKE '%Tennaqua%')
    """)
    
    print(f"   🧪 Sample test - Tennaqua APTA_CHICAGO matches: {test_user_matches['count']}")
    
    return len(remaining_orphans) == 0

def main():
    """Main function to fix orphaned league IDs"""
    print("🚀 ORPHANED LEAGUE ID FIX")
    print("=" * 50)
    print("Fixing orphaned league_id references in match_scores...")
    
    try:
        # Connect to Railway
        print("\n🔌 Connecting to Railway database...")
        conn = connect_to_railway()
        print("   ✅ Connected successfully")
        
        # Step 1: Identify orphaned leagues
        valid_leagues, orphaned_leagues = identify_orphaned_leagues(conn)
        
        if not orphaned_leagues:
            print("\n✅ No orphaned leagues found! Data is clean.")
            return
        
        # Step 2: Analyze orphaned data
        mappings = analyze_orphaned_data(conn, orphaned_leagues)
        
        # Step 3: Create mapping plan
        final_mappings = create_mapping_plan(conn, mappings, valid_leagues)
        
        if not final_mappings:
            print("\n❌ No mappings could be determined. Manual intervention required.")
            return
        
        # Confirm before applying
        print(f"\n❓ Ready to apply {len(final_mappings)} mappings?")
        print("   This will update match_scores table permanently.")
        response = input("   Type 'yes' to proceed: ")
        
        if response.lower() != 'yes':
            print("   ⏹️ Operation cancelled.")
            return
        
        # Step 4: Apply mappings
        total_updated = apply_mappings(conn, final_mappings)
        
        # Step 5: Verify fix
        success = verify_fix(conn)
        
        print(f"\n🎉 SUMMARY:")
        print(f"   • Orphaned leagues found: {len(orphaned_leagues)}")
        print(f"   • Mappings applied: {len(final_mappings)}")
        print(f"   • Matches updated: {total_updated}")
        print(f"   • Fix successful: {'✅ Yes' if success else '❌ No'}")
        print(f"\n🚀 Railway my-club page should now show all match data!")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 