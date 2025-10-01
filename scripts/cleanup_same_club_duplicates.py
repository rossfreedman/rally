#!/usr/bin/env python3
"""
Cleanup Same-Club Duplicate Player Records

This script identifies and removes invalid duplicate player records where the same
player appears on multiple teams at the SAME club.

VALID multi-team scenario: Brett Pierson playing at Valley Lo AND Tennaqua (different clubs)
INVALID duplicate: Christopher Bechtel with 3 records at Skokie (same club)

The script keeps the "best" record for each player at each club based on:
1. Most actual match history
2. Most season matches (if tied)
3. Most career matches (if tied)
4. Most recent created_at (if still tied)

Usage:
    # Dry run (preview only)
    python3 scripts/cleanup_same_club_duplicates.py --dry-run
    
    # Execute cleanup
    python3 scripts/cleanup_same_club_duplicates.py --execute
    
    # Deactivate instead of delete
    python3 scripts/cleanup_same_club_duplicates.py --execute --deactivate
"""

import sys
import os
from pathlib import Path

# Add project root to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from database import get_db
import argparse
from datetime import datetime


def analyze_duplicates(cur):
    """Identify which records to keep and which to remove."""
    
    print("\n" + "="*80)
    print("ANALYZING SAME-CLUB DUPLICATE PLAYER RECORDS")
    print("="*80 + "\n")
    
    # Find all same-club duplicates and rank them
    cur.execute('''
        WITH same_club_dupes AS (
            SELECT 
                p.tenniscores_player_id,
                p.first_name,
                p.last_name,
                p.club_id,
                c.name as club_name,
                p.id as player_db_id,
                p.team_id,
                t.team_name,
                p.wins + p.losses as season_matches,
                p.career_wins + p.career_losses as career_matches,
                p.created_at,
                -- Count matches this player actually played for this team
                (SELECT COUNT(*) 
                 FROM match_scores ms
                 WHERE (ms.home_player_1_id = p.tenniscores_player_id OR 
                        ms.home_player_2_id = p.tenniscores_player_id OR
                        ms.away_player_1_id = p.tenniscores_player_id OR
                        ms.away_player_2_id = p.tenniscores_player_id)
                   AND (ms.home_team_id = p.team_id OR ms.away_team_id = p.team_id)
                ) as actual_matches
            FROM players p
            JOIN teams t ON p.team_id = t.id
            JOIN clubs c ON p.club_id = c.id
            WHERE p.is_active = true
              AND p.tenniscores_player_id IS NOT NULL
              AND p.league_id = 4783  -- APTA Chicago
        ),
        duplicates AS (
            SELECT *,
                   COUNT(*) OVER (PARTITION BY tenniscores_player_id, club_id) as dup_count,
                   ROW_NUMBER() OVER (
                       PARTITION BY tenniscores_player_id, club_id 
                       ORDER BY actual_matches DESC, season_matches DESC, 
                                career_matches DESC, created_at DESC
                   ) as keep_rank
            FROM same_club_dupes
        )
        SELECT 
            tenniscores_player_id,
            first_name,
            last_name,
            club_id,
            club_name,
            player_db_id,
            team_name,
            actual_matches,
            season_matches,
            career_matches,
            dup_count,
            keep_rank
        FROM duplicates
        WHERE dup_count > 1
        ORDER BY dup_count DESC, last_name, keep_rank
    ''')
    
    columns = [desc[0] for desc in cur.description]
    all_records = cur.fetchall()
    
    # Separate into keep and delete
    keep_records = [r for r in all_records if r[11] == 1]  # keep_rank = 1
    delete_records = [r for r in all_records if r[11] > 1]  # keep_rank > 1
    
    print(f"Found {len(all_records)} duplicate records affecting {len(keep_records)} players\n")
    print(f"  KEEP:   {len(keep_records)} records (primary record for each player at each club)")
    print(f"  DELETE: {len(delete_records)} records (duplicates at same club)\n")
    
    return keep_records, delete_records


def preview_changes(keep_records, delete_records):
    """Show examples of what will be kept and deleted."""
    
    print("\n" + "="*80)
    print("PREVIEW OF CHANGES (First 10 Examples)")
    print("="*80 + "\n")
    
    # Group by player
    from collections import defaultdict
    by_player = defaultdict(list)
    
    for record in keep_records + delete_records:
        key = (record[0], record[1], record[2], record[3])  # tenniscores_id, first, last, club_id
        by_player[key].append(record)
    
    # Show first 10
    for idx, (key, records) in enumerate(list(by_player.items())[:10], 1):
        tenniscores_id, first_name, last_name, club_id = key
        club_name = records[0][4]
        
        print(f"{idx}. {first_name} {last_name} at {club_name}")
        print(f"   Tenniscores ID: {tenniscores_id}")
        print(f"   {len(records)} records at same club:\n")
        
        for r in sorted(records, key=lambda x: x[11]):  # Sort by keep_rank
            action = "✅ KEEP  " if r[11] == 1 else "❌ DELETE"
            print(f"   {action} - DB ID {r[5]}: {r[6]}")
            print(f"            Matches: {r[7]} actual, {r[8]} season, {r[9]} career")
        print()


def execute_cleanup(cur, delete_records, deactivate=False):
    """Execute the cleanup - either deactivate or delete records."""
    
    print("\n" + "="*80)
    if deactivate:
        print("DEACTIVATING DUPLICATE RECORDS")
    else:
        print("DELETING DUPLICATE RECORDS")
    print("="*80 + "\n")
    
    delete_ids = [r[5] for r in delete_records]  # player_db_id
    
    if deactivate:
        # Deactivate records
        cur.execute('''
            UPDATE players 
            SET is_active = false,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ANY(%s)
            RETURNING id, first_name, last_name
        ''', (delete_ids,))
    else:
        # Delete records
        cur.execute('''
            DELETE FROM players 
            WHERE id = ANY(%s)
            RETURNING id, first_name, last_name
        ''', (delete_ids,))
    
    affected = cur.rowcount
    print(f"{'Deactivated' if deactivate else 'Deleted'} {affected} duplicate player records")
    
    return affected


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup same-club duplicate player records",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without executing (default)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute the cleanup (deactivate or delete records)'
    )
    parser.add_argument(
        '--deactivate',
        action='store_true',
        help='Deactivate records instead of deleting them'
    )
    
    args = parser.parse_args()
    
    # If no arguments, default to dry-run
    if not args.execute:
        args.dry_run = True
    
    try:
        with get_db() as conn:
            cur = conn.cursor()
            
            # Analyze duplicates
            keep_records, delete_records = analyze_duplicates(cur)
            
            # Preview changes
            preview_changes(keep_records, delete_records)
            
            if args.execute:
                # Confirm before executing
                print("\n" + "⚠️ "*20)
                print("\nWARNING: You are about to modify the database!")
                print(f"This will {'deactivate' if args.deactivate else 'DELETE'} {len(delete_records)} player records.")
                print("\n" + "⚠️ "*20 + "\n")
                
                response = input("Type 'YES' to confirm: ")
                
                if response == 'YES':
                    execute_cleanup(cur, delete_records, args.deactivate)
                    conn.commit()
                    print("\n✅ Cleanup completed successfully!")
                else:
                    print("\n❌ Cleanup cancelled")
                    return
            else:
                print("\n" + "="*80)
                print("DRY RUN - No changes made to database")
                print("="*80)
                print("\nTo execute cleanup, run with --execute flag:")
                print("  python3 scripts/cleanup_same_club_duplicates.py --execute --deactivate")
            
            cur.close()
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
