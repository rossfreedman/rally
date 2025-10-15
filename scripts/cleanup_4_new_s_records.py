#!/usr/bin/env python3
"""
Clean up the 4 new (S) records created during production scraper run.
These are: Claire Hamilton(S), Grace Kim(S), Brooke Haller(S), Jillian McKenna(S)
"""

import psycopg2
from psycopg2.extras import RealDictCursor

PROD_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def cleanup_new_s_records():
    print("=" * 80)
    print("CLEANING UP 4 NEW (S) RECORDS FROM PRODUCTION")
    print("=" * 80)
    print()
    
    # The 4 player IDs from the validation report
    player_ids_to_deactivate = [972679, 973159, 972678, 974163]
    
    conn = psycopg2.connect(PROD_DB_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Show what we're going to deactivate
        print("Players to deactivate:")
        print("-" * 80)
        
        cursor.execute("""
            SELECT p.id, p.first_name, p.last_name, p.is_active,
                   s.name as series_name, t.team_name
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE p.id = ANY(%s)
            ORDER BY p.id
        """, (player_ids_to_deactivate,))
        
        players = cursor.fetchall()
        
        for p in players:
            status = "ACTIVE" if p['is_active'] else "INACTIVE"
            print(f"  ID {p['id']}: {p['first_name']} {p['last_name']} [{status}]")
            print(f"    Series: {p['series_name']}, Team: {p['team_name']}")
        print()
        
        # Deactivate them
        print("Deactivating records...")
        print("-" * 80)
        
        cursor.execute("""
            UPDATE players
            SET is_active = false
            WHERE id = ANY(%s)
            AND is_active = true
        """, (player_ids_to_deactivate,))
        
        deactivated_count = cursor.rowcount
        conn.commit()
        
        print(f"✅ Deactivated {deactivated_count} player record(s)")
        print()
        
        # Verify
        print("Verification:")
        print("-" * 80)
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM players
            WHERE first_name LIKE '%(S)' OR last_name LIKE '%(S)'
            AND is_active = true
        """)
        active_count = cursor.fetchone()
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM players
            WHERE first_name LIKE '%(S)' OR last_name LIKE '%(S)'
            AND is_active = false
        """)
        inactive_count = cursor.fetchone()
        
        print(f"Active (S) records: {active_count['count']}")
        print(f"Inactive (S) records: {inactive_count['count']}")
        print()
        
        # Check against expected
        expected_active = 170
        expected_inactive = 110  # 106 original + 4 new ones we just deactivated
        
        if active_count['count'] == expected_active:
            print(f"✅ Active (S) count back to baseline: {expected_active}")
        else:
            print(f"⚠️  Active (S) count: {active_count['count']} (expected: {expected_active})")
        
        if inactive_count['count'] == expected_inactive:
            print(f"✅ Inactive (S) count: {expected_inactive} (106 original + 4 new)")
        else:
            print(f"ℹ️  Inactive (S) count: {inactive_count['count']} (expected: ~{expected_inactive})")
        print()
        
        print("=" * 80)
        print("CLEANUP COMPLETE")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Deploy scraper code fixes to production")
        print("2. Validate next cron run creates 0 (S) records")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    confirm = input("This will deactivate 4 (S) records in PRODUCTION. Continue? (yes/no): ")
    if confirm.lower() == 'yes':
        cleanup_new_s_records()
    else:
        print("Aborted.")

