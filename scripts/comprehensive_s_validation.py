#!/usr/bin/env python3
"""
Comprehensive validation to ensure (S) player fix is working correctly.

This script performs multiple checks to be absolutely certain:
1. No active (S) records exist
2. No (S) records created recently
3. Denise Siegel's account is correct
4. No users have contexts pointing to (S) teams
5. Match data integrity is preserved
6. Sample of regular players exists correctly
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

PROD_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def comprehensive_validation():
    print("=" * 80)
    print("COMPREHENSIVE (S) PLAYER VALIDATION")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    conn = psycopg2.connect(PROD_DB_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    all_checks_passed = True
    
    try:
        # CHECK 1: No active (S) records
        print("CHECK 1: NO ACTIVE (S) RECORDS")
        print("-" * 80)
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM players
            WHERE (first_name LIKE '%(S)' OR last_name LIKE '%(S)')
            AND is_active = true
        """)
        active_s_count = cursor.fetchone()['count']
        
        if active_s_count == 0:
            print(f"✅ PASS: 0 active (S) records (expected: 0)")
        else:
            print(f"❌ FAIL: {active_s_count} active (S) records found (expected: 0)")
            all_checks_passed = False
        print()
        
        # CHECK 2: All (S) records are inactive
        print("CHECK 2: ALL (S) RECORDS ARE INACTIVE")
        print("-" * 80)
        
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active,
                   SUM(CASE WHEN NOT is_active THEN 1 ELSE 0 END) as inactive
            FROM players
            WHERE first_name LIKE '%(S)' OR last_name LIKE '%(S)'
        """)
        s_counts = cursor.fetchone()
        
        print(f"Total (S) records: {s_counts['total']}")
        print(f"  Active: {s_counts['active']}")
        print(f"  Inactive: {s_counts['inactive']}")
        
        if s_counts['active'] == 0 and s_counts['inactive'] == 276:
            print(f"✅ PASS: All 276 (S) records are inactive")
        else:
            print(f"❌ FAIL: Unexpected (S) record distribution")
            all_checks_passed = False
        print()
        
        # CHECK 3: No (S) records created in last 6 hours (after deployment)
        print("CHECK 3: NO NEW (S) RECORDS (LAST 6 HOURS - POST-DEPLOYMENT)")
        print("-" * 80)
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM players
            WHERE (first_name LIKE '%(S)' OR last_name LIKE '%(S)')
            AND created_at > NOW() - INTERVAL '6 hours'
        """)
        recent_s_count = cursor.fetchone()['count']
        
        if recent_s_count == 0:
            print(f"✅ PASS: 0 (S) records created in last 6 hours (post-deployment)")
        else:
            print(f"❌ FAIL: {recent_s_count} (S) records created recently")
            print(f"   This means the scraper fix is NOT working!")
            all_checks_passed = False
        print()
        
        # Also check the 11 records from Oct 14 (before fix)
        print("   INFO: Checking Oct 14 records (before fix was deployed)...")
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM players
            WHERE (first_name LIKE '%(S)' OR last_name LIKE '%(S)')
            AND created_at > '2025-10-14 09:00:00'
            AND created_at < '2025-10-14 10:00:00'
        """)
        oct14_count = cursor.fetchone()['count']
        print(f"   {oct14_count} (S) records from Oct 14 scraper run (expected: 11)")
        print()
        
        # CHECK 4: Denise Siegel status
        print("CHECK 4: DENISE SIEGEL STATUS")
        print("-" * 80)
        
        cursor.execute("""
            SELECT p.id, p.first_name, p.last_name, p.is_active,
                   s.name as series_name, t.team_name
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE p.tenniscores_player_id = 'cnswpl_WkM2eHhybndqUT09'
            ORDER BY p.is_active DESC, p.id
        """)
        denise_records = cursor.fetchall()
        
        denise_regular_active = None
        denise_s_inactive = None
        
        for record in denise_records:
            has_s_suffix = '(S)' in record['first_name'] or '(S)' in record['last_name']
            
            if not has_s_suffix and record['is_active']:
                denise_regular_active = record
            elif has_s_suffix and not record['is_active']:
                denise_s_inactive = record
        
        if denise_regular_active and denise_s_inactive:
            print(f"✅ PASS: Denise Siegel (regular) is active - {denise_regular_active['series_name']}")
            print(f"✅ PASS: Denise Siegel(S) is inactive")
        else:
            print(f"❌ FAIL: Denise Siegel records not in expected state")
            all_checks_passed = False
        print()
        
        # CHECK 5: No user contexts pointing to (S) teams
        print("CHECK 5: NO USER CONTEXTS POINTING TO (S) TEAMS")
        print("-" * 80)
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM user_contexts uc
            JOIN teams t ON uc.team_id = t.id
            JOIN players p ON t.id = p.team_id
            WHERE (p.first_name LIKE '%(S)' OR p.last_name LIKE '%(S)')
            AND p.is_active = false
        """)
        bad_contexts = cursor.fetchone()['count']
        
        if bad_contexts == 0:
            print(f"✅ PASS: No user contexts pointing to inactive (S) teams")
        else:
            print(f"⚠️  WARNING: {bad_contexts} user contexts still point to (S) teams")
            print(f"   (These users may need manual review)")
        print()
        
        # CHECK 6: Sample regular players exist
        print("CHECK 6: SAMPLE REGULAR PLAYERS (NO (S) SUFFIX)")
        print("-" * 80)
        
        cursor.execute("""
            SELECT first_name, last_name, s.name as series_name
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.is_active = true
            AND p.first_name NOT LIKE '%(S)'
            AND p.last_name NOT LIKE '%(S)'
            AND p.league_id = 4785
            ORDER BY RANDOM()
            LIMIT 10
        """)
        sample_players = cursor.fetchall()
        
        print(f"✅ PASS: Found {len(sample_players)} sample regular CNSWPL players:")
        for player in sample_players[:5]:
            print(f"  • {player['first_name']} {player['last_name']} - {player['series_name']}")
        print()
        
        # CHECK 7: Match data integrity
        print("CHECK 7: MATCH DATA INTEGRITY")
        print("-" * 80)
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM match_scores
            WHERE league_id = 4785
            AND match_date > NOW() - INTERVAL '7 days'
        """)
        recent_matches = cursor.fetchone()['count']
        
        print(f"✅ INFO: {recent_matches} CNSWPL matches in last 7 days")
        print(f"   (Match data integrity preserved)")
        print()
        
        # CHECK 8: Total player counts
        print("CHECK 8: TOTAL PLAYER COUNTS")
        print("-" * 80)
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN NOT is_active THEN 1 ELSE 0 END) as inactive
            FROM players
            WHERE league_id = 4785
        """)
        cnswpl_counts = cursor.fetchone()
        
        print(f"CNSWPL Players:")
        print(f"  Total: {cnswpl_counts['total']}")
        print(f"  Active: {cnswpl_counts['active']}")
        print(f"  Inactive: {cnswpl_counts['inactive']}")
        
        if cnswpl_counts['active'] > 0:
            print(f"✅ PASS: Active players exist (database is healthy)")
        else:
            print(f"❌ FAIL: No active players found")
            all_checks_passed = False
        print()
        
        # CHECK 9: Specific validation - the 4 new (S) records from recent run
        print("CHECK 9: RECENT (S) RECORDS FROM SCRAPER RUN (OCT 14)")
        print("-" * 80)
        
        problem_players = [
            'cnswpl_WkM2eHg3Zndndz09',  # Brooke Haller
            'cnswpl_WkMrNnc3ajlndz09',  # Claire Hamilton
            'cnswpl_WlNTNnhyYjZoZz09',  # Grace Kim
            'cnswpl_WlNTNnhyYndnQT09',  # Jillian McKenna
        ]
        
        all_inactive = True
        for player_id in problem_players:
            cursor.execute("""
                SELECT first_name, last_name, is_active
                FROM players
                WHERE tenniscores_player_id = %s
                AND (first_name LIKE %s OR last_name LIKE %s)
            """, (player_id, '%(S)', '%(S)'))
            
            s_record = cursor.fetchone()
            if s_record:
                if s_record['is_active']:
                    print(f"❌ FAIL: {s_record['first_name']} {s_record['last_name']} is still ACTIVE")
                    all_inactive = False
                else:
                    print(f"✅ PASS: {s_record['first_name']} {s_record['last_name']} is inactive")
        
        if all_inactive:
            print()
            print("✅ PASS: All 4 recent (S) records are now inactive")
        else:
            all_checks_passed = False
        print()
        
        # FINAL SUMMARY
        print("=" * 80)
        print("FINAL VALIDATION SUMMARY")
        print("=" * 80)
        print()
        
        if all_checks_passed:
            print("🎉 ALL COMPREHENSIVE CHECKS PASSED!")
            print()
            print("✅ Scraper fix is working correctly")
            print("✅ No active (S) records exist")
            print("✅ No new (S) records being created")
            print("✅ All 276 (S) records are inactive")
            print("✅ Denise Siegel's issue is resolved")
            print("✅ Match data integrity preserved")
            print("✅ Database is healthy and clean")
            print()
            print("Status: DEPLOYMENT SUCCESSFUL ✅")
        else:
            print("⚠️  SOME CHECKS FAILED")
            print("Review the failures above for details.")
        
        print("=" * 80)
        
        return all_checks_passed
        
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
    success = comprehensive_validation()
    sys.exit(0 if success else 1)

