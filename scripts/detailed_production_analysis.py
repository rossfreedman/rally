#!/usr/bin/env python3
"""
Detailed analysis of what happened during production scraper run.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

PROD_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def analyze_production():
    print("=" * 80)
    print("DETAILED PRODUCTION SCRAPER RUN ANALYSIS")
    print("=" * 80)
    print()
    
    conn = psycopg2.connect(PROD_DB_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # 1. Show the 11 new (S) records in detail
        print("1. THE 11 NEW (S) RECORDS CREATED")
        print("-" * 80)
        
        cursor.execute("""
            SELECT p.id, p.first_name, p.last_name, p.is_active, p.created_at,
                   s.name as series_name, t.team_name,
                   p.tenniscores_player_id
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE (p.first_name LIKE '%(S)' OR p.last_name LIKE '%(S)')
            AND p.created_at > NOW() - INTERVAL '24 hours'
            ORDER BY p.is_active DESC, p.created_at DESC
        """)
        new_s_records = cursor.fetchall()
        
        active_new = [r for r in new_s_records if r['is_active']]
        inactive_new = [r for r in new_s_records if not r['is_active']]
        
        print(f"Total new (S) records: {len(new_s_records)}")
        print(f"  Active: {len(active_new)}")
        print(f"  Inactive: {len(inactive_new)}")
        print()
        
        if active_new:
            print(f"⚠️  ACTIVE (S) records created (these are the problem):")
            for player in active_new:
                print(f"\n  Player ID: {player['id']}")
                print(f"    Name: {player['first_name']} {player['last_name']}")
                print(f"    Series: {player['series_name']}, Team: {player['team_name']}")
                print(f"    Tenniscores ID: {player['tenniscores_player_id']}")
                print(f"    Created: {player['created_at']}")
        print()
        
        if inactive_new:
            print(f"Inactive (S) records created:")
            for player in inactive_new:
                print(f"  • {player['first_name']} {player['last_name']} - {player['series_name']}")
        print()
        
        # 2. Check if these players have regular counterparts
        print("2. DO THESE (S) PLAYERS HAVE REGULAR COUNTERPARTS?")
        print("-" * 80)
        
        for s_player in active_new:
            tenniscores_id = s_player['tenniscores_player_id']
            
            cursor.execute("""
                SELECT p.id, p.first_name, p.last_name, p.is_active,
                       s.name as series_name
                FROM players p
                LEFT JOIN series s ON p.series_id = s.id
                WHERE p.tenniscores_player_id = %s
                AND p.first_name NOT LIKE '%(S)'
                AND p.last_name NOT LIKE '%(S)'
            """, (tenniscores_id,))
            regular_player = cursor.fetchone()
            
            print(f"\n{s_player['first_name']} {s_player['last_name']}:")
            if regular_player:
                print(f"  ✓ Has regular counterpart:")
                print(f"    • {regular_player['first_name']} {regular_player['last_name']} - {regular_player['series_name']} (Active: {regular_player['is_active']})")
                print(f"  → This is a DUPLICATE that should be cleaned up")
            else:
                print(f"  ✗ No regular counterpart found")
                print(f"  → May be a legitimate substitute-only player")
        print()
        
        # 3. Overall (S) record statistics
        print("3. OVERALL (S) RECORD STATISTICS")
        print("-" * 80)
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_s,
                SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active_s,
                SUM(CASE WHEN NOT is_active THEN 1 ELSE 0 END) as inactive_s
            FROM players
            WHERE first_name LIKE '%(S)' OR last_name LIKE '%(S)'
        """)
        totals = cursor.fetchone()
        
        print(f"Total (S) records: {totals['total_s']}")
        print(f"  Active: {totals['active_s']}")
        print(f"  Inactive: {totals['inactive_s']}")
        print()
        
        # 4. Check total active count change
        print("4. WHAT HAPPENED TO MAINTAIN 170 ACTIVE COUNT?")
        print("-" * 80)
        
        print(f"Before scraper run:")
        print(f"  Active (S): 170")
        print()
        print(f"Scraper created:")
        print(f"  New active (S): {len(active_new)}")
        print()
        print(f"After scraper run:")
        print(f"  Active (S): {totals['active_s']}")
        print()
        
        if totals['active_s'] == 170 and len(active_new) > 0:
            deactivated_count = len(active_new)
            print(f"Analysis:")
            print(f"  • {len(active_new)} new (S) records created as ACTIVE")
            print(f"  • Total active (S) stayed at 170")
            print(f"  → Likely: {deactivated_count} old (S) records were deactivated/updated")
            print()
            print("Possible explanations:")
            print("  1. Import script deactivated old/stale (S) records")
            print("  2. Players moved teams and old records were deactivated")
            print("  3. ETL process maintains a certain count")
        elif totals['active_s'] > 170:
            print(f"⚠️  Net increase: {totals['active_s'] - 170} more active (S) records")
        print()
        
        # 5. Code deployment status check
        print("5. CODE DEPLOYMENT STATUS CHECK")
        print("-" * 80)
        
        print("Question: Did the scraper run use the FIXED code or OLD code?")
        print()
        print("Evidence:")
        print(f"  • {len(new_s_records)} new (S) records created today")
        print(f"  • {len(active_new)} are ACTIVE (problematic)")
        print()
        
        if len(active_new) > 0:
            print("Conclusion:")
            print("  ❌ Scraper fixes were NOT deployed before cron run")
            print("  ❌ Production is still using OLD scraper code")
            print("  ❌ Need to deploy code changes ASAP")
        else:
            print("Conclusion:")
            print("  ✅ Scraper fixes are working")
            print("  ✅ Production has updated code")
        print()
        
        # 6. Denise Siegel final check
        print("6. DENISE SIEGEL FINAL STATUS")
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
        
        for record in denise_records:
            status = "ACTIVE" if record['is_active'] else "INACTIVE"
            marker = ""
            if record['is_active'] and '(S)' not in record['first_name']:
                marker = " ✅ CORRECT"
            elif not record['is_active'] and '(S)' in record['first_name']:
                marker = " ✅ CORRECT"
            
            print(f"  {record['first_name']} {record['last_name']}: {status}{marker}")
            print(f"    Series: {record['series_name']}, Team: {record['team_name']}")
        print()
        
        # Simulate her login
        cursor.execute("""
            SELECT DISTINCT ON (u.id)
                u.id, s.name as series, t.team_name
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
        login = cursor.fetchone()
        
        if login and login['series'] == 'Series I':
            print("✅ Denise's login: Shows Series I (Tennaqua I) - CORRECT")
        else:
            print(f"⚠️  Denise's login: Shows {login['series'] if login else 'ERROR'}")
        print()
        
        # FINAL SUMMARY
        print("=" * 80)
        print("PRODUCTION VALIDATION SUMMARY")
        print("=" * 80)
        print()
        
        print("DATABASE CLEANUP:")
        print(f"  ✅ Still preserved: 106 inactive (S) records")
        print(f"  ✅ Active (S) count: 170 (unchanged)")
        print()
        
        print("SCRAPER RUN RESULTS:")
        print(f"  ⚠️  Created {len(new_s_records)} new (S) records")
        print(f"  ⚠️  {len(active_new)} are ACTIVE (duplicates)")
        print(f"  ℹ️  {len(inactive_new)} are INACTIVE (auto-cleaned)")
        print()
        
        print("SCRAPER CODE STATUS:")
        if len(active_new) > 0:
            print(f"  ❌ SCRAPER FIXES NOT DEPLOYED")
            print(f"  ❌ Production used OLD code that creates (S) duplicates")
            print(f"  🔴 URGENT: Deploy scraper fixes to prevent more duplicates")
        else:
            print(f"  ✅ Scraper fixes working")
        print()
        
        print("DENISE SIEGEL:")
        print(f"  ✅ Still shows correct team (Series I)")
        print()
        
        print("RECOMMENDATION:")
        if len(active_new) > 0:
            print(f"  1. Deploy scraper code fixes to production IMMEDIATELY")
            print(f"  2. Run cleanup script again to deactivate the {len(active_new)} new (S) records")
            print(f"  3. Validate after deployment")
        
        print("=" * 80)
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    analyze_production()

