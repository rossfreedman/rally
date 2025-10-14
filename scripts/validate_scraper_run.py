#!/usr/bin/env python3
"""
Validation script to verify scraper run didn't create new (S) duplicate records.
Run this AFTER the scraper completes.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database_utils import get_db_cursor
from datetime import datetime

def validate_scraper_run():
    """Validate that the scraper run didn't create new (S) records."""
    
    print("=" * 80)
    print("POST-SCRAPER VALIDATION")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    with get_db_cursor(commit=False) as cursor:
        
        # 1. Check for new (S) records created
        print("1. CHECKING FOR NEW (S) PLAYER RECORDS")
        print("-" * 80)
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM players
            WHERE (first_name LIKE '%(S)' OR last_name LIKE '%(S)')
            AND is_active = true
        """)
        active_s_records = cursor.fetchone()
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM players
            WHERE (first_name LIKE '%(S)' OR last_name LIKE '%(S)')
            AND is_active = false
        """)
        inactive_s_records = cursor.fetchone()
        
        print(f"Active (S) records: {active_s_records['count']}")
        print(f"Inactive (S) records: {inactive_s_records['count']}")
        print()
        
        # Expected: 170 active (unmatched), 99 inactive (cleaned up)
        if active_s_records['count'] > 170:
            print(f"⚠️  WARNING: More active (S) records than expected!")
            print(f"   Expected: ~170, Found: {active_s_records['count']}")
            print(f"   New (S) records may have been created!")
        else:
            print(f"✅ PASS: No new (S) records created")
        print()
        
        # 2. Check recently created players
        print("2. CHECKING RECENTLY CREATED PLAYERS")
        print("-" * 80)
        
        cursor.execute("""
            SELECT first_name, last_name, created_at, is_active
            FROM players
            WHERE created_at > NOW() - INTERVAL '2 hours'
            AND (first_name LIKE '%(S)' OR last_name LIKE '%(S)')
            ORDER BY created_at DESC
            LIMIT 10
        """)
        recent_s_players = cursor.fetchall()
        
        if recent_s_players:
            print(f"⚠️  Found {len(recent_s_players)} (S) player(s) created in last 2 hours:")
            for player in recent_s_players:
                print(f"  • {player['first_name']} {player['last_name']} - "
                      f"Active: {player['is_active']} - "
                      f"Created: {player['created_at']}")
            print()
            print("❌ FAIL: Scraper created new (S) records!")
        else:
            print("✅ PASS: No (S) players created in last 2 hours")
        print()
        
        # 3. Check Denise Siegel specifically
        print("3. DENISE SIEGEL VALIDATION")
        print("-" * 80)
        
        cursor.execute("""
            SELECT p.id, p.first_name, p.last_name, p.is_active,
                   s.name as series_name, t.team_name,
                   p.created_at
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE p.tenniscores_player_id = 'cnswpl_WkM2eHhybndqUT09'
            ORDER BY p.is_active DESC, p.id
        """)
        denise_records = cursor.fetchall()
        
        for record in denise_records:
            status = "ACTIVE" if record['is_active'] else "INACTIVE"
            print(f"{record['first_name']} {record['last_name']}: {status}")
            print(f"  Series: {record['series_name']}, Team: {record['team_name']}")
            print(f"  Created: {record['created_at']}")
        print()
        
        # Verify no new Denise Siegel(S) record
        denise_s_active = [r for r in denise_records if '(S)' in r['first_name'] and r['is_active']]
        if denise_s_active:
            print("❌ FAIL: Denise Siegel(S) is active again!")
        else:
            print("✅ PASS: Denise Siegel(S) remains inactive")
        print()
        
        # 4. Check match data integrity
        print("4. MATCH DATA INTEGRITY")
        print("-" * 80)
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM match_scores
            WHERE home_player_1_id LIKE '%%(S)%%'
               OR home_player_2_id LIKE '%%(S)%%'
               OR away_player_1_id LIKE '%%(S)%%'
               OR away_player_2_id LIKE '%%(S)%%'
        """)
        matches_with_s = cursor.fetchone()
        
        print(f"Matches with (S) in player IDs: {matches_with_s['count']}")
        
        if matches_with_s['count'] > 0:
            print("⚠️  Note: Some matches reference (S) in player ID strings")
            print("   This is expected if player IDs contain literal '(S)' characters")
        else:
            print("✅ PASS: No (S) in match player IDs")
        print()
        
        # 5. Check total player count
        print("5. PLAYER COUNT SUMMARY")
        print("-" * 80)
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN NOT is_active THEN 1 ELSE 0 END) as inactive
            FROM players
        """)
        counts = cursor.fetchone()
        
        print(f"Total players: {counts['total']}")
        print(f"  Active: {counts['active']}")
        print(f"  Inactive: {counts['inactive']}")
        print()
        
        # 6. Final summary
        print("=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        print()
        
        passed = True
        
        # Check 1: No new active (S) records
        if active_s_records['count'] <= 170:
            print("✅ Check 1: No new (S) records created")
        else:
            print(f"❌ Check 1: New (S) records detected ({active_s_records['count']} > 170)")
            passed = False
        
        # Check 2: No recently created (S) players
        if not recent_s_players:
            print("✅ Check 2: No recent (S) player creation")
        else:
            print(f"❌ Check 2: {len(recent_s_players)} (S) players created recently")
            passed = False
        
        # Check 3: Denise Siegel(S) remains inactive
        if not denise_s_active:
            print("✅ Check 3: Denise Siegel(S) remains inactive")
        else:
            print("❌ Check 3: Denise Siegel(S) is active")
            passed = False
        
        print()
        
        if passed:
            print("🎉 ALL VALIDATION CHECKS PASSED!")
            print()
            print("✅ Scraper successfully filtered (S) players")
            print("✅ No new duplicate records created")
            print("✅ Database cleanup preserved")
            print()
            print("Status: SCRAPER FIXES WORKING CORRECTLY")
        else:
            print("❌ SOME VALIDATION CHECKS FAILED")
            print()
            print("Review the failures above to identify issues.")
            print("The scraper may need additional debugging.")
        
        print("=" * 80)
        
        return passed

if __name__ == "__main__":
    success = validate_scraper_run()
    sys.exit(0 if success else 1)


