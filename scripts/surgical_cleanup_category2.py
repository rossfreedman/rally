#!/usr/bin/env python3
"""
Surgical Cleanup: Category 2 Multi-Club Ghost Records

This script removes ONLY Category 2 records:
- Players with records at multiple clubs (valid scenario)
- BUT one record has 0 actual matches AND 0 career data
- These are substitute roster entries where the player never actually played

Examples:
- Wes Maher at Winnetka 99 B (0 matches, 0 career) - REMOVE
- Wes Maher at Tennaqua 20 (1 match, 28-22 career) - KEEP

This is surgical - it only removes ghost records, preserving all legitimate data.

Usage:
    # Dry run (preview only)
    python3 scripts/surgical_cleanup_category2.py --dry-run
    
    # Execute cleanup
    python3 scripts/surgical_cleanup_category2.py --execute
    
    # Deactivate instead of delete
    python3 scripts/surgical_cleanup_category2.py --execute --deactivate
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


def identify_category2_records(cur):
    """Identify Category 2 ghost records to remove."""
    
    print("\n" + "="*80)
    print("IDENTIFYING CATEGORY 2: MULTI-CLUB GHOST RECORDS")
    print("="*80 + "\n")
    
    # Find multi-club players with ghost records
    cur.execute('''
        WITH player_records AS (
            SELECT 
                p.tenniscores_player_id,
                p.first_name,
                p.last_name,
                p.club_id,
                c.name as club_name,
                p.id as player_db_id,
                t.team_name,
                s.name as series_name,
                p.wins + p.losses as season_matches,
                COALESCE(p.career_wins, 0) + COALESCE(p.career_losses, 0) as career_matches,
                -- Count actual matches played for this specific team
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
            JOIN series s ON p.series_id = s.id
            WHERE p.is_active = true
              AND p.tenniscores_player_id IS NOT NULL
              AND p.league_id = 4783  -- APTA Chicago only
        ),
        multi_club_players AS (
            SELECT tenniscores_player_id
            FROM player_records
            GROUP BY tenniscores_player_id
            HAVING COUNT(DISTINCT club_id) > 1
        ),
        ghost_records AS (
            SELECT pr.*
            FROM player_records pr
            WHERE pr.tenniscores_player_id IN (SELECT tenniscores_player_id FROM multi_club_players)
              AND pr.actual_matches = 0
              AND pr.career_matches = 0
        )
        SELECT 
            tenniscores_player_id,
            first_name,
            last_name,
            club_id,
            club_name,
            player_db_id,
            team_name,
            series_name,
            actual_matches,
            season_matches,
            career_matches
        FROM ghost_records
        ORDER BY last_name, first_name, club_name
    ''')
    
    columns = [desc[0] for desc in cur.description]
    ghost_records = cur.fetchall()
    
    print(f"Found {len(ghost_records)} Category 2 ghost records to remove\n")
    
    return ghost_records


def preview_changes(ghost_records):
    """Show examples of what will be removed."""
    
    print("\n" + "="*80)
    print("PREVIEW OF CATEGORY 2 CLEANUP (First 15 Examples)")
    print("="*80 + "\n")
    
    # Group by player to show context
    from collections import defaultdict
    by_player = defaultdict(list)
    
    for record in ghost_records:
        key = (record[0], record[1], record[2])  # tenniscores_id, first, last
        by_player[key].append(record)
    
    # Show first 15 players
    for idx, (key, records) in enumerate(list(by_player.items())[:15], 1):
        tenniscores_id, first_name, last_name = key
        
        print(f"{idx}. {first_name} {last_name}")
        print(f"   Tenniscores ID: {tenniscores_id}")
        print(f"   Ghost records to remove:\n")
        
        for r in records:
            print(f"   ❌ DELETE - DB ID {r[5]}: {r[6]} at {r[4]}")
            print(f"            Series: {r[7]}, Matches: {r[8]} actual, {r[9]} season, {r[10]} career")
        print()
    
    if len(by_player) > 15:
        print(f"... and {len(by_player) - 15} more players with ghost records\n")


def execute_cleanup(cur, ghost_records, deactivate=False):
    """Execute the surgical cleanup."""
    
    print("\n" + "="*80)
    if deactivate:
        print("DEACTIVATING CATEGORY 2 GHOST RECORDS")
    else:
        print("DELETING CATEGORY 2 GHOST RECORDS")
    print("="*80 + "\n")
    
    delete_ids = [r[5] for r in ghost_records]  # player_db_id
    
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
    print(f"{'Deactivated' if deactivate else 'Deleted'} {affected} Category 2 ghost records")
    
    return affected


def verify_cleanup(cur):
    """Verify the cleanup was successful."""
    
    print("\n" + "="*80)
    print("VERIFICATION")
    print("="*80 + "\n")
    
    # Check if any Category 2 records remain
    cur.execute('''
        WITH player_records AS (
            SELECT 
                p.tenniscores_player_id,
                p.club_id,
                (SELECT COUNT(*) 
                 FROM match_scores ms
                 WHERE (ms.home_player_1_id = p.tenniscores_player_id OR 
                        ms.home_player_2_id = p.tenniscores_player_id OR
                        ms.away_player_1_id = p.tenniscores_player_id OR
                        ms.away_player_2_id = p.tenniscores_player_id)
                   AND (ms.home_team_id = p.team_id OR ms.away_team_id = p.team_id)
                ) as actual_matches,
                COALESCE(p.career_wins, 0) + COALESCE(p.career_losses, 0) as career_matches
            FROM players p
            WHERE p.is_active = true
              AND p.tenniscores_player_id IS NOT NULL
              AND p.league_id = 4783
        ),
        multi_club_players AS (
            SELECT tenniscores_player_id
            FROM player_records
            GROUP BY tenniscores_player_id
            HAVING COUNT(DISTINCT club_id) > 1
        )
        SELECT COUNT(*)
        FROM player_records pr
        WHERE pr.tenniscores_player_id IN (SELECT tenniscores_player_id FROM multi_club_players)
          AND pr.actual_matches = 0
          AND pr.career_matches = 0
    ''')
    
    remaining = cur.fetchone()[0]
    
    if remaining == 0:
        print("✅ SUCCESS: No Category 2 ghost records remain")
    else:
        print(f"⚠️  WARNING: {remaining} Category 2 ghost records still exist")
    
    # Show some examples of remaining multi-club players (should all be valid now)
    cur.execute('''
        WITH player_records AS (
            SELECT 
                p.tenniscores_player_id,
                p.first_name,
                p.last_name,
                p.club_id,
                c.name as club_name,
                t.team_name,
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
              AND p.league_id = 4783
        ),
        multi_club_players AS (
            SELECT tenniscores_player_id
            FROM player_records
            GROUP BY tenniscores_player_id
            HAVING COUNT(DISTINCT club_id) > 1
        )
        SELECT 
            pr.first_name,
            pr.last_name,
            pr.club_name,
            pr.team_name,
            pr.actual_matches
        FROM player_records pr
        WHERE pr.tenniscores_player_id IN (SELECT tenniscores_player_id FROM multi_club_players)
        ORDER BY pr.last_name, pr.first_name, pr.club_name
        LIMIT 10
    ''')
    
    remaining_multi_club = cur.fetchall()
    
    print(f"\nRemaining multi-club players (should all have match history):")
    for row in remaining_multi_club:
        first, last, club, team, matches = row
        print(f"  {first} {last} at {club} ({team}) - {matches} matches")


def main():
    parser = argparse.ArgumentParser(
        description="Surgical cleanup of Category 2 multi-club ghost records",
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
            
            # Identify Category 2 records
            ghost_records = identify_category2_records(cur)
            
            if len(ghost_records) == 0:
                print("✅ No Category 2 ghost records found - cleanup not needed")
                return
            
            # Preview changes
            preview_changes(ghost_records)
            
            if args.execute:
                # Confirm before executing
                print("\n" + "⚠️ "*20)
                print("\nWARNING: You are about to modify the database!")
                print(f"This will {'deactivate' if args.deactivate else 'DELETE'} {len(ghost_records)} Category 2 ghost records.")
                print("\nThese are multi-club players with 0 matches and 0 career data.")
                print("(e.g., Wes Maher at Winnetka 99 B)")
                print("\n" + "⚠️ "*20 + "\n")
                
                response = input("Type 'YES' to confirm: ")
                
                if response == 'YES':
                    execute_cleanup(cur, ghost_records, args.deactivate)
                    conn.commit()
                    print("\n✅ Category 2 cleanup completed successfully!")
                    
                    # Verify cleanup
                    verify_cleanup(cur)
                else:
                    print("\n❌ Cleanup cancelled")
                    return
            else:
                print("\n" + "="*80)
                print("DRY RUN - No changes made to database")
                print("="*80)
                print("\nTo execute cleanup, run with --execute flag:")
                print("  python3 scripts/surgical_cleanup_category2.py --execute --deactivate")
            
            cur.close()
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
