#!/usr/bin/env python3
"""
Production validation script to verify no new (S) records are created.
Run this AFTER the next production cron scraper run.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Production database URL
PROD_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def validate_production():
    print("=" * 80)
    print("PRODUCTION VALIDATION - POST CRON RUN")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    conn = psycopg2.connect(PROD_DB_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Expected baseline (after complete cleanup - October 14, 2025)
        # All (S) records should be inactive now - there should be NO active (S) records
        EXPECTED_ACTIVE_S = 0
        EXPECTED_INACTIVE_S = 276
        
        # Query 1: Count (S) players by status
        print("1. (S) PLAYER RECORD COUNTS")
        print("-" * 80)
        
        cursor.execute("""
            SELECT is_active, COUNT(*) as count
            FROM players
            WHERE first_name LIKE '%(S)' OR last_name LIKE '%(S)'
            GROUP BY is_active
            ORDER BY is_active DESC
        """)
        s_counts = cursor.fetchall()
        
        actual_active = 0
        actual_inactive = 0
        
        for row in s_counts:
            status = "ACTIVE" if row['is_active'] else "INACTIVE"
            count = row['count']
            print(f"  {status}: {count} records")
            
            if row['is_active']:
                actual_active = count
            else:
                actual_inactive = count
        print()
        
        # Validation
        print("Comparison:")
        print(f"  Expected Active (S):   {EXPECTED_ACTIVE_S}")
        print(f"  Actual Active (S):     {actual_active}")
        print(f"  Difference:            {actual_active - EXPECTED_ACTIVE_S:+d}")
        print()
        print(f"  Expected Inactive (S): {EXPECTED_INACTIVE_S}")
        print(f"  Actual Inactive (S):   {actual_inactive}")
        print(f"  Difference:            {actual_inactive - EXPECTED_INACTIVE_S:+d}")
        print()
        
        if actual_active == EXPECTED_ACTIVE_S and actual_inactive == EXPECTED_INACTIVE_S:
            print("✅ PASS: No new (S) records created")
        elif actual_active > EXPECTED_ACTIVE_S:
            print(f"❌ FAIL: {actual_active - EXPECTED_ACTIVE_S} new (S) records created!")
        else:
            print(f"⚠️  Unexpected: Fewer (S) records than baseline")
        print()
        
        # Query 2: Recently created (S) players
        print("2. RECENTLY CREATED (S) PLAYERS (Last 24 Hours)")
        print("-" * 80)
        
        cursor.execute("""
            SELECT p.id, p.first_name, p.last_name, p.created_at, p.is_active,
                   s.name as series_name
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            WHERE (p.first_name LIKE '%(S)' OR p.last_name LIKE '%(S)')
            AND p.created_at > NOW() - INTERVAL '24 hours'
            ORDER BY p.created_at DESC
        """)
        recent_s = cursor.fetchall()
        
        if recent_s:
            print(f"⚠️  Found {len(recent_s)} (S) player(s) created in last 24 hours:")
            for player in recent_s:
                status = "ACTIVE" if player['is_active'] else "INACTIVE"
                print(f"  • {player['first_name']} {player['last_name']} [{status}]")
                print(f"    Series: {player['series_name']}")
                print(f"    Created: {player['created_at']}")
            print()
            print("❌ FAIL: Scraper created new (S) records - fixes not deployed!")
        else:
            print("✅ PASS: No (S) players created in last 24 hours")
            print("   Scraper fixes are working correctly!")
        print()
        
        # Query 3: Denise Siegel status
        print("3. DENISE SIEGEL STATUS")
        print("-" * 80)
        
        cursor.execute("""
            SELECT p.id, p.first_name, p.last_name, p.is_active
            FROM players p
            WHERE p.tenniscores_player_id = 'cnswpl_WkM2eHhybndqUT09'
            ORDER BY p.id
        """)
        denise_records = cursor.fetchall()
        
        for record in denise_records:
            status = "ACTIVE" if record['is_active'] else "INACTIVE"
            marker = ""
            if record['is_active'] and '(S)' not in record['first_name']:
                marker = " ← CORRECT PRIMARY"
            elif not record['is_active'] and '(S)' in record['first_name']:
                marker = " ← CORRECT DEACTIVATED"
            
            print(f"  ID {record['id']}: {record['first_name']} {record['last_name']} - {status}{marker}")
        print()
        
        denise_s_active = any(r for r in denise_records if '(S)' in r['first_name'] and r['is_active'])
        denise_regular_active = any(r for r in denise_records if '(S)' not in r['first_name'] and r['is_active'])
        
        if denise_regular_active and not denise_s_active:
            print("✅ PASS: Denise Siegel correct, Denise Siegel(S) inactive")
        else:
            print("❌ FAIL: Denise's records are not in expected state")
        print()
        
        # Final summary
        print("=" * 80)
        print("FINAL VALIDATION SUMMARY")
        print("=" * 80)
        print()
        
        all_passed = (
            actual_active == EXPECTED_ACTIVE_S and
            actual_inactive == EXPECTED_INACTIVE_S and
            not recent_s and
            denise_regular_active and
            not denise_s_active
        )
        
        if all_passed:
            print("🎉 ALL VALIDATIONS PASSED!")
            print()
            print("✅ Database cleanup preserved")
            print("✅ No new (S) records created") 
            print("✅ Scraper fixes working correctly")
            print("✅ Production is clean and stable")
        else:
            print("❌ SOME VALIDATIONS FAILED")
            print()
            if actual_active > EXPECTED_ACTIVE_S:
                print(f"⚠️  {actual_active - EXPECTED_ACTIVE_S} new (S) records detected")
                print("   → Scraper code may not be deployed")
            if recent_s:
                print(f"⚠️  {len(recent_s)} (S) records created recently")
                print("   → Scraper fixes not working")
        
        print("=" * 80)
        
        return all_passed
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import sys
    success = validate_production()
    sys.exit(0 if success else 1)

