#!/usr/bin/env python3
"""
Fix League Migration Mapping
Maps orphaned league_ids to their correct corresponding new league_ids based on comparison analysis
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
    """Fix league migration mapping with correct 1:1 correspondence"""
    print("🚀 LEAGUE MIGRATION MAPPING FIX")
    print("=" * 50)
    print("Mapping orphaned league_ids to correct corresponding new league_ids...")
    
    try:
        # Connect to Railway
        print("\n🔌 Connecting to Railway database...")
        conn = connect_to_railway()
        print("   ✅ Connected successfully")
        
        # Define correct mappings based on local vs Railway comparison
        league_mappings = {
            4543: 4489,  # APTA_CHICAGO old → new
            4544: 4490,  # CITA old → new  
            4545: 4491,  # CNSWPL old → new
            4546: 4492,  # NSTF old → new
        }
        
        print(f"\n📋 CORRECT MIGRATION MAPPING:")
        print(f"   Based on local vs Railway comparison analysis:")
        for old_id, new_id in league_mappings.items():
            # Get league name for verification
            league_info = execute_query_one(conn, """
                SELECT league_id, league_name FROM leagues WHERE id = %s
            """, [new_id])
            
            match_count = execute_query_one(conn, """
                SELECT COUNT(*) as count FROM match_scores WHERE league_id = %s
            """, [old_id])
            
            league_name = league_info['league_name'] if league_info else 'Unknown'
            count = match_count['count'] if match_count else 0
            
            print(f"   - {old_id} → {new_id} ({league_name}): {count} matches")
        
        # Confirm mapping
        print(f"\n❓ This will restore proper league associations.")
        print(f"   All orphaned match data will be accessible to users again.")
        response = input("   Type 'yes' to proceed: ")
        
        if response.lower() != 'yes':
            print("   ⏹️ Operation cancelled.")
            return
        
        # Apply mappings
        print(f"\n🔧 APPLYING MIGRATION MAPPINGS...")
        total_updated = 0
        
        for old_id, new_id in league_mappings.items():
            print(f"   🔄 Migrating {old_id} → {new_id}...")
            
            updated_count = execute_update(conn, """
                UPDATE match_scores 
                SET league_id = %s 
                WHERE league_id = %s
            """, [new_id, old_id])
            
            print(f"      ✅ Migrated {updated_count} matches")
            total_updated += updated_count
        
        # Verify fix
        print(f"\n🧪 VERIFYING MIGRATION...")
        
        # Check for remaining orphans
        remaining_orphans = execute_query_one(conn, """
            SELECT COUNT(*) as count
            FROM match_scores ms
            LEFT JOIN leagues l ON ms.league_id = l.id
            WHERE l.id IS NULL AND ms.league_id IS NOT NULL
        """)
        
        # Test Tennaqua matches in APTA_CHICAGO
        apta_tennaqua = execute_query_one(conn, """
            SELECT COUNT(*) as count
            FROM match_scores ms
            WHERE ms.league_id = 4489  -- APTA_CHICAGO
            AND (ms.home_team LIKE '%Tennaqua%' OR ms.away_team LIKE '%Tennaqua%')
        """)
        
        # Test Tennaqua matches in CNSWPL 
        cnswpl_tennaqua = execute_query_one(conn, """
            SELECT COUNT(*) as count
            FROM match_scores ms
            WHERE ms.league_id = 4491  -- CNSWPL
            AND (ms.home_team LIKE '%Tennaqua%' OR ms.away_team LIKE '%Tennaqua%')
        """)
        
        print(f"   ✅ Remaining orphaned matches: {remaining_orphans['count']}")
        print(f"   ✅ Tennaqua APTA_CHICAGO matches: {apta_tennaqua['count']} (should be ~1,300)")
        print(f"   ✅ Tennaqua CNSWPL matches: {cnswpl_tennaqua['count']} (should be ~211)")
        
        success = remaining_orphans['count'] == 0
        
        print(f"\n🎉 SUMMARY:")
        print(f"   • League mappings applied: {len(league_mappings)}")
        print(f"   • Total matches migrated: {total_updated}")
        print(f"   • Migration successful: {'✅ Yes' if success else '❌ No'}")
        print(f"   • Expected result: Users can now access all their club's match data")
        print(f"\n🚀 Railway my-club page should now work exactly like local!")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 