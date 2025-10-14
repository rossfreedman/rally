#!/usr/bin/env python3
"""
Direct database validation after scraper run.
Shows actual database state to confirm no new (S) records.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database_utils import get_db_cursor
from datetime import datetime, timedelta

def validate_database():
    print("=" * 80)
    print("DATABASE VALIDATION AFTER SCRAPER RUN")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    with get_db_cursor(commit=False) as cursor:
        
        # 1. Show (S) player counts - detailed breakdown
        print("1. DETAILED (S) PLAYER RECORD COUNTS")
        print("-" * 80)
        
        cursor.execute("""
            SELECT 
                is_active,
                COUNT(*) as count
            FROM players
            WHERE first_name LIKE '%(S)' OR last_name LIKE '%(S)'
            GROUP BY is_active
            ORDER BY is_active DESC
        """)
        s_counts = cursor.fetchall()
        
        total_s = 0
        for row in s_counts:
            status = "ACTIVE" if row['is_active'] else "INACTIVE"
            print(f"  {status}: {row['count']} records")
            total_s += row['count']
        
        print(f"  TOTAL: {total_s} (S) records")
        print()
        
        expected_active = 170
        expected_inactive = 106
        
        actual_active = next((r['count'] for r in s_counts if r['is_active']), 0)
        actual_inactive = next((r['count'] for r in s_counts if not r['is_active']), 0)
        
        if actual_active == expected_active and actual_inactive == expected_inactive:
            print(f"✅ VALIDATION: Counts match expected values")
            print(f"   Expected: {expected_active} active, {expected_inactive} inactive")
            print(f"   Actual:   {actual_active} active, {actual_inactive} inactive")
        else:
            print(f"⚠️  WARNING: Counts don't match!")
            print(f"   Expected: {expected_active} active, {expected_inactive} inactive")
            print(f"   Actual:   {actual_active} active, {actual_inactive} inactive")
            print(f"   Difference: {actual_active - expected_active} new active (S) records")
        print()
        
        # 2. Show recently created (S) players (last 4 hours to cover scraper run)
        print("2. RECENTLY CREATED (S) PLAYERS (Last 4 Hours)")
        print("-" * 80)
        
        cursor.execute("""
            SELECT id, first_name, last_name, created_at, is_active,
                   s.name as series_name, t.team_name
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE (p.first_name LIKE '%(S)' OR p.last_name LIKE '%(S)')
            AND p.created_at > NOW() - INTERVAL '4 hours'
            ORDER BY p.created_at DESC
        """)
        recent_s = cursor.fetchall()
        
        if recent_s:
            print(f"⚠️  FOUND {len(recent_s)} (S) player(s) created recently:")
            for player in recent_s:
                status = "ACTIVE" if player['is_active'] else "INACTIVE"
                print(f"\n  Player ID: {player['id']} [{status}]")
                print(f"    Name: {player['first_name']} {player['last_name']}")
                print(f"    Series: {player['series_name']}")
                print(f"    Team: {player['team_name']}")
                print(f"    Created: {player['created_at']}")
            print()
            print("❌ FAIL: New (S) records were created during scraper run!")
        else:
            print("✅ PASS: No (S) players created in last 4 hours")
            print("   The scraper successfully filtered out all (S) players!")
        print()
        
        # 3. Check Denise Siegel's records
        print("3. DENISE SIEGEL SPECIFIC VALIDATION")
        print("-" * 80)
        
        cursor.execute("""
            SELECT p.id, p.first_name, p.last_name, p.is_active,
                   s.name as series_name, t.team_name,
                   p.created_at, p.updated_at
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE p.tenniscores_player_id = 'cnswpl_WkM2eHhybndqUT09'
            ORDER BY p.is_active DESC, p.id
        """)
        denise_records = cursor.fetchall()
        
        print(f"Total Denise Siegel records: {len(denise_records)}")
        print()
        
        for record in denise_records:
            status = "ACTIVE ✓" if record['is_active'] else "INACTIVE"
            marker = "← PRIMARY" if record['is_active'] and '(S)' not in record['first_name'] else ""
            marker = marker or ("← DEACTIVATED SUB" if not record['is_active'] else "")
            
            print(f"  {record['first_name']} {record['last_name']} [{status}] {marker}")
            print(f"    DB ID: {record['id']}")
            print(f"    Series: {record['series_name']}, Team: {record['team_name']}")
            print(f"    Created: {record['created_at']}")
            print(f"    Updated: {record['updated_at']}")
            print()
        
        # Check if any new Denise records were created
        recent_denise = [r for r in denise_records if r['created_at'] > datetime.now(r['created_at'].tzinfo) - timedelta(hours=4)]
        
        if recent_denise:
            print(f"⚠️  {len(recent_denise)} Denise record(s) created in last 4 hours")
            if any('(S)' in r['first_name'] for r in recent_denise):
                print("❌ FAIL: New Denise Siegel(S) record created!")
        else:
            print("✅ PASS: No new Denise Siegel records created during scraper run")
        print()
        
        # 4. Show sample of players created during scraper run (non-S)
        print("4. RECENTLY CREATED NON-(S) PLAYERS (Sample)")
        print("-" * 80)
        
        cursor.execute("""
            SELECT first_name, last_name, s.name as series_name
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.created_at > NOW() - INTERVAL '4 hours'
            AND p.first_name NOT LIKE '%(S)'
            AND p.last_name NOT LIKE '%(S)'
            AND p.is_active = true
            ORDER BY p.created_at DESC
            LIMIT 10
        """)
        recent_regular = cursor.fetchall()
        
        if recent_regular:
            print(f"Found {len(recent_regular)} regular players created (showing 10):")
            for player in recent_regular:
                print(f"  • {player['first_name']} {player['last_name']} - {player['series_name']}")
            print()
            print("✅ Scraper is working - creating regular players only")
        else:
            print("No regular players created (may be all updates, no new players)")
        print()
        
        # 5. Final counts comparison
        print("5. BEFORE/AFTER COMPARISON")
        print("-" * 80)
        
        print("Expected after cleanup:")
        print(f"  Active (S): 170")
        print(f"  Inactive (S): 106")
        print()
        
        print("Actual after scraper run:")
        print(f"  Active (S): {actual_active}")
        print(f"  Inactive (S): {actual_inactive}")
        print()
        
        if actual_active == 170 and actual_inactive == 106:
            print("✅ PERFECT MATCH - Scraper fixes are working!")
        elif actual_active > 170:
            print(f"❌ PROBLEM: {actual_active - 170} new (S) records created!")
        else:
            print(f"⚠️  Unexpected: Fewer (S) records than expected")
        print()
        
        # 6. Simulate Denise's login one more time
        print("6. FINAL LOGIN SIMULATION FOR DENISE")
        print("-" * 80)
        
        cursor.execute("""
            SELECT DISTINCT ON (u.id)
                u.id, s.name as series, t.team_name, p.is_active
            FROM users u
            LEFT JOIN user_contexts uc ON u.id = uc.user_id
            LEFT JOIN user_player_associations upa ON u.id = upa.user_id
            LEFT JOIN players p ON upa.tenniscores_player_id = p.tenniscores_player_id AND p.is_active = true
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE u.email = 'siegeldenise@yahoo.com'
            ORDER BY u.id,
                     (CASE WHEN p.league_id = u.league_context THEN 1 ELSE 2 END),
                     (CASE WHEN p.team_id = uc.team_id THEN 1 ELSE 2 END),
                     (CASE WHEN p.team_id IS NOT NULL THEN 1 ELSE 2 END),
                     p.id DESC
            LIMIT 1
        """)
        login_sim = cursor.fetchone()
        
        if login_sim:
            print(f"Login would show:")
            print(f"  Series: {login_sim['series']}")
            print(f"  Team: {login_sim['team_name']}")
            print(f"  Player Active: {login_sim['is_active']}")
            print()
            
            if login_sim['series'] == 'Series I' and login_sim['team_name'] == 'Tennaqua I':
                print("✅ PERFECT: Denise will see Series I (Tennaqua I)")
            else:
                print(f"❌ PROBLEM: Denise will see {login_sim['series']} instead of Series I")
        else:
            print("❌ ERROR: Login simulation failed")
        print()
        
        # Final summary
        print("=" * 80)
        print("FINAL DATABASE VALIDATION")
        print("=" * 80)
        print()
        
        all_passed = (
            actual_active == 170 and
            actual_inactive == 106 and
            not recent_s and
            login_sim and
            login_sim['series'] == 'Series I'
        )
        
        if all_passed:
            print("🎉 ALL DATABASE VALIDATIONS PASSED!")
            print()
            print("Summary:")
            print("  ✅ No new (S) records created during scraper run")
            print("  ✅ Cleanup preserved (106 inactive, 170 active)")
            print("  ✅ Denise Siegel will see correct team (Series I)")
            print("  ✅ Scraper fixes are working in production")
            print()
            print("Status: READY FOR PRODUCTION DEPLOYMENT")
        else:
            print("⚠️  SOME VALIDATIONS FAILED")
            print("Review the details above for issues.")
        
        print("=" * 80)
        
        return all_passed

if __name__ == "__main__":
    success = validate_database()
    sys.exit(0 if success else 1)

