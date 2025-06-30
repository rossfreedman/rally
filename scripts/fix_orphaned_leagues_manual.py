#!/usr/bin/env python3
"""
Manual Fix for Orphaned League IDs
Maps all orphaned league_ids to APTA_CHICAGO based on team analysis
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

def main():
    """Fix orphaned league IDs by mapping to APTA_CHICAGO"""
    print("🚀 MANUAL ORPHANED LEAGUE ID FIX")
    print("=" * 50)
    print("Mapping all orphaned league_ids to APTA_CHICAGO...")
    
    try:
        # Connect to Railway
        print("\n🔌 Connecting to Railway database...")
        conn = connect_to_railway()
        print("   ✅ Connected successfully")
        
        # Define mappings based on analysis
        orphaned_leagues = [4543, 4544, 4545, 4546]
        target_league_id = 4489  # APTA_CHICAGO
        
        print(f"\n📋 MAPPING PLAN:")
        print(f"   All orphaned leagues → {target_league_id} (APTA_CHICAGO)")
        
        # Show current state
        for orphaned_id in orphaned_leagues:
            count = execute_query_one(conn, """
                SELECT COUNT(*) as count FROM match_scores WHERE league_id = %s
            """, [orphaned_id])
            
            print(f"   - {orphaned_id}: {count['count']} matches → {target_league_id}")
        
        # Confirm
        print(f"\n❓ This will update all orphaned match data to APTA_CHICAGO.")
        print(f"   Based on team analysis, all appear to be Chicago-area clubs.")
        response = input("   Type 'yes' to proceed: ")
        
        if response.lower() != 'yes':
            print("   ⏹️ Operation cancelled.")
            return
        
        # Apply mappings
        print(f"\n🔧 APPLYING MAPPINGS...")
        total_updated = 0
        
        for orphaned_id in orphaned_leagues:
            print(f"   🔄 Updating {orphaned_id} → {target_league_id}...")
            
            updated_count = execute_update(conn, """
                UPDATE match_scores 
                SET league_id = %s 
                WHERE league_id = %s
            """, [target_league_id, orphaned_id])
            
            print(f"      ✅ Updated {updated_count} matches")
            total_updated += updated_count
        
        # Verify
        print(f"\n🧪 VERIFYING FIX...")
        
        # Check for remaining orphans
        remaining_orphans = execute_query_one(conn, """
            SELECT COUNT(*) as count
            FROM match_scores ms
            LEFT JOIN leagues l ON ms.league_id = l.id
            WHERE l.id IS NULL AND ms.league_id IS NOT NULL
        """)
        
        # Check APTA_CHICAGO total
        apta_total = execute_query_one(conn, """
            SELECT COUNT(*) as count
            FROM match_scores ms
            WHERE ms.league_id = %s
        """, [target_league_id])
        
        # Test sample user
        sample_test = execute_query_one(conn, """
            SELECT COUNT(*) as count
            FROM match_scores ms
            WHERE ms.league_id = %s
            AND (ms.home_team LIKE '%Tennaqua%' OR ms.away_team LIKE '%Tennaqua%')
        """, [target_league_id])
        
        print(f"   ✅ Remaining orphaned matches: {remaining_orphans['count']}")
        print(f"   ✅ Total APTA_CHICAGO matches: {apta_total['count']}")
        print(f"   ✅ Sample Tennaqua matches: {sample_test['count']}")
        
        success = remaining_orphans['count'] == 0
        
        print(f"\n🎉 SUMMARY:")
        print(f"   • Orphaned leagues fixed: {len(orphaned_leagues)}")
        print(f"   • Total matches updated: {total_updated}")
        print(f"   • Fix successful: {'✅ Yes' if success else '❌ No'}")
        print(f"   • Tennaqua now has {sample_test['count']} matches (vs 12 before)")
        print(f"\n🚀 Railway my-club page should now work with full data!")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 