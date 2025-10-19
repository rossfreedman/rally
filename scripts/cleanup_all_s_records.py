#!/usr/bin/env python3
"""
Clean up ALL (S) player records from the database.

You are correct - there should be NO (S) players in the database at all.
The (S) suffix should be stripped during scraping, and all players should be 
stored with their clean names.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Production database URL
PROD_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

def cleanup_all_s_records(dry_run=True):
    """
    Deactivate ALL (S) player records.
    
    Args:
        dry_run: If True, only report changes without applying them
    """
    
    print("=" * 80)
    print(f"CLEANUP ALL (S) PLAYER RECORDS - {'DRY RUN' if dry_run else 'LIVE RUN'}")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    print("You are correct - there should be NO (S) players in the database.")
    print("All players should be stored with clean names, not (S) suffixes.")
    print()
    
    conn = psycopg2.connect(PROD_DB_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Step 1: Find ALL (S) players (both active and inactive)
        print("STEP 1: Finding ALL (S) player records...")
        print("-" * 80)
        
        cursor.execute("""
            SELECT p.id, p.first_name, p.last_name, p.tenniscores_player_id,
                   p.team_id, p.is_active,
                   s.name as series_name, t.team_name,
                   l.league_name, c.name as club_name
            FROM players p
            LEFT JOIN series s ON p.series_id = s.id
            LEFT JOIN teams t ON p.team_id = t.id
            LEFT JOIN leagues l ON p.league_id = l.id
            LEFT JOIN clubs c ON p.club_id = c.id
            WHERE (p.first_name LIKE '%(S)' OR p.last_name LIKE '%(S)')
            ORDER BY p.is_active DESC, p.tenniscores_player_id, p.id
        """)
        all_s_players = cursor.fetchall()
        
        active_s = [p for p in all_s_players if p['is_active']]
        inactive_s = [p for p in all_s_players if not p['is_active']]
        
        print(f"✓ Found {len(all_s_players)} total (S) player records:")
        print(f"  Active: {len(active_s)}")
        print(f"  Inactive: {len(inactive_s)}")
        print()
        
        if not active_s:
            print("✅ No active (S) records to clean up!")
            return
        
        # Step 2: Show active (S) players that will be deactivated
        print("STEP 2: Active (S) players that will be deactivated...")
        print("-" * 80)
        
        for player in active_s:
            print(f"Player ID: {player['id']}")
            print(f"  Name: {player['first_name']} {player['last_name']}")
            print(f"  Tenniscores ID: {player['tenniscores_player_id']}")
            print(f"  Series: {player['series_name']}")
            print(f"  Team: {player['team_name']}")
            print(f"  Club: {player['club_name']}")
            print(f"  League: {player['league_name']}")
            print()
        
        # Step 3: Check for user contexts that might be affected
        print("STEP 3: Checking for affected user contexts...")
        print("-" * 80)
        
        team_ids = [p['team_id'] for p in active_s if p['team_id']]
        
        if team_ids:
            cursor.execute("""
                SELECT uc.user_id, uc.team_id, t.team_name, s.name as series_name,
                       u.email, u.first_name, u.last_name
                FROM user_contexts uc
                JOIN teams t ON uc.team_id = t.id
                JOIN series s ON t.series_id = s.id
                JOIN users u ON uc.user_id = u.id
                WHERE uc.team_id = ANY(%s)
            """, (team_ids,))
            
            affected_contexts = cursor.fetchall()
            
            if affected_contexts:
                print(f"⚠️  Found {len(affected_contexts)} user contexts pointing to (S) teams:")
                for context in affected_contexts:
                    print(f"  User: {context['first_name']} {context['last_name']} ({context['email']})")
                    print(f"    Team: {context['team_name']} - {context['series_name']}")
                print()
                print("⚠️  WARNING: These users will need their contexts updated!")
            else:
                print("✅ No user contexts pointing to (S) teams")
        else:
            print("✅ No team IDs found in (S) records")
        
        print()
        
        # Step 4: Execute cleanup if not dry run
        if dry_run:
            print("STEP 4: DRY RUN - No changes made")
            print("-" * 80)
            print("To execute the cleanup, run:")
            print("  python3 scripts/cleanup_all_s_records.py --live")
            print()
        else:
            print("STEP 4: Deactivating (S) player records...")
            print("-" * 80)
            
            # Deactivate all (S) players
            cursor.execute("""
                UPDATE players
                SET is_active = false
                WHERE first_name LIKE '%(S)' OR last_name LIKE '%(S)'
            """)
            
            affected_rows = cursor.rowcount
            print(f"✓ Deactivated {affected_rows} (S) player records")
            
            # Commit changes
            conn.commit()
            print("✓ Changes committed to database")
            print()
        
        # Step 5: Summary
        print("=" * 80)
        print("CLEANUP SUMMARY")
        print("=" * 80)
        print(f"Total (S) records found: {len(all_s_players)}")
        print(f"Active (S) records: {len(active_s)}")
        print(f"Inactive (S) records: {len(inactive_s)}")
        
        if dry_run:
            print()
            print("🔴 DRY RUN COMPLETE - No changes made")
            print("Run with --live to execute the cleanup")
        else:
            print()
            print("✅ CLEANUP COMPLETE - All (S) records deactivated")
            print()
            print("Next steps:")
            print("1. Deploy the fixed scraper code")
            print("2. Monitor next scraper run to ensure no new (S) records")
            print("3. Consider permanently deleting inactive (S) records later")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"✗ ERROR: {e}")
        if not dry_run:
            conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import sys
    
    dry_run = "--live" not in sys.argv
    
    if dry_run:
        print("🔴 DRY RUN MODE - No changes will be made")
        print("Add --live to execute the cleanup")
        print()
    
    cleanup_all_s_records(dry_run=dry_run)
