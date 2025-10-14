#!/usr/bin/env python3
"""
Clean up duplicate (S) player records from the database.

This script will:
1. Identify all player records with (S) suffix
2. Find their corresponding regular player record (same tenniscores_player_id)
3. Update user_contexts to point to the regular player's team
4. Mark (S) records as inactive (is_active = false)
5. Generate report of changes made

Note: We mark as inactive instead of deleting to preserve data integrity
and allow for rollback if needed.
"""

import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

def cleanup_duplicates(db_url, dry_run=True):
    """
    Clean up duplicate (S) player records.
    
    Args:
        db_url: Database connection URL
        dry_run: If True, only report changes without applying them
    """
    
    print("=" * 80)
    print(f"SUBSTITUTE PLAYER CLEANUP - {'DRY RUN' if dry_run else 'LIVE RUN'}")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cleanup_stats = {
        'total_s_players': 0,
        'matched_pairs': 0,
        'unmatched_s_players': 0,
        'user_contexts_updated': 0,
        's_players_deactivated': 0,
        'errors': []
    }
    
    try:
        # Step 1: Find all (S) players
        print("STEP 1: Finding all (S) player records...")
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
            AND p.is_active = true
            ORDER BY p.tenniscores_player_id, p.id
        """)
        s_players = cursor.fetchall()
        
        cleanup_stats['total_s_players'] = len(s_players)
        print(f"✓ Found {len(s_players)} active (S) player records")
        print()
        
        # Step 2: Match (S) players with their regular counterparts
        print("STEP 2: Matching (S) players with regular players...")
        print("-" * 80)
        
        matched_pairs = []
        unmatched = []
        
        for s_player in s_players:
            # Find regular player with same tenniscores_player_id
            clean_first = s_player['first_name'].replace('(S)', '').strip()
            clean_last = s_player['last_name'].replace('(S)', '').strip()
            
            cursor.execute("""
                SELECT p.id, p.first_name, p.last_name, p.team_id,
                       s.name as series_name, t.team_name
                FROM players p
                LEFT JOIN series s ON p.series_id = s.id
                LEFT JOIN teams t ON p.team_id = t.id
                WHERE p.tenniscores_player_id = %s
                AND p.first_name NOT LIKE '%%(S)'
                AND p.last_name NOT LIKE '%%(S)'
                AND p.is_active = true
                LIMIT 1
            """, (s_player['tenniscores_player_id'],))
            
            regular_player = cursor.fetchone()
            
            if regular_player:
                matched_pairs.append({
                    's_player': s_player,
                    'regular_player': regular_player
                })
            else:
                unmatched.append(s_player)
        
        cleanup_stats['matched_pairs'] = len(matched_pairs)
        cleanup_stats['unmatched_s_players'] = len(unmatched)
        
        print(f"✓ Matched pairs: {len(matched_pairs)}")
        print(f"⚠ Unmatched (S) players: {len(unmatched)}")
        print()
        
        if unmatched:
            print("Unmatched (S) players (no regular counterpart found):")
            for u in unmatched[:5]:
                print(f"  • {u['first_name']} {u['last_name']} - {u['league_name']}, {u['series_name']}")
            if len(unmatched) > 5:
                print(f"  ... and {len(unmatched) - 5} more")
            print()
        
        # Step 3: Show sample of what will be changed
        print("STEP 3: Changes to be made (sample)...")
        print("-" * 80)
        
        for pair in matched_pairs[:5]:
            s = pair['s_player']
            r = pair['regular_player']
            print(f"\n{s['first_name']} {s['last_name']} (ID: {s['id']})")
            print(f"  League: {s['league_name']}")
            print(f"  (S) Record: {s['series_name']} - {s['team_name']} [Team ID: {s['team_id']}]")
            print(f"  Regular Record: {r['series_name']} - {r['team_name']} [Team ID: {r['team_id']}]")
            print(f"  Action: Deactivate (S) record, ensure users point to regular record")
        
        if len(matched_pairs) > 5:
            print(f"\n... and {len(matched_pairs) - 5} more pairs")
        print()
        
        if dry_run:
            print("=" * 80)
            print("DRY RUN COMPLETE - No changes made")
            print("=" * 80)
            print(f"\nSummary:")
            print(f"  Total (S) players found: {cleanup_stats['total_s_players']}")
            print(f"  Matched pairs: {cleanup_stats['matched_pairs']}")
            print(f"  Unmatched: {cleanup_stats['unmatched_s_players']}")
            print()
            print("To apply these changes, run with --live flag")
            return cleanup_stats
        
        # Step 4: Update user_contexts for affected users
        print("STEP 4: Updating user_contexts to point to regular players...")
        print("-" * 80)
        
        for pair in matched_pairs:
            s_player_id = pair['s_player']['id']
            s_team_id = pair['s_player']['team_id']
            regular_team_id = pair['regular_player']['team_id']
            
            # Find users who have user_contexts pointing to the (S) player's team
            cursor.execute("""
                UPDATE user_contexts
                SET team_id = %s
                WHERE team_id = %s
                AND user_id IN (
                    SELECT u.id FROM users u
                    JOIN user_player_associations upa ON u.id = upa.user_id
                    WHERE upa.tenniscores_player_id = %s
                )
            """, (regular_team_id, s_team_id, pair['s_player']['tenniscores_player_id']))
            
            updated = cursor.rowcount
            if updated > 0:
                cleanup_stats['user_contexts_updated'] += updated
                print(f"  Updated {updated} user_context(s) for {pair['s_player']['first_name']} {pair['s_player']['last_name']}")
        
        print(f"\n✓ Updated {cleanup_stats['user_contexts_updated']} user_contexts")
        print()
        
        # Step 5: Deactivate (S) player records
        print("STEP 5: Deactivating (S) player records...")
        print("-" * 80)
        
        s_player_ids = [pair['s_player']['id'] for pair in matched_pairs]
        
        if s_player_ids:
            cursor.execute("""
                UPDATE players
                SET is_active = false
                WHERE id = ANY(%s)
            """, (s_player_ids,))
            
            cleanup_stats['s_players_deactivated'] = cursor.rowcount
            print(f"✓ Deactivated {cleanup_stats['s_players_deactivated']} (S) player records")
        
        print()
        
        # Commit changes
        conn.commit()
        
        # Step 6: Verification
        print("STEP 6: Verification...")
        print("-" * 80)
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM players
            WHERE (first_name LIKE '%(S)' OR last_name LIKE '%(S)')
            AND is_active = true
        """)
        remaining = cursor.fetchone()
        
        print(f"Remaining active (S) players: {remaining['count']}")
        print()
        
        # Final summary
        print("=" * 80)
        print("CLEANUP COMPLETE")
        print("=" * 80)
        print(f"\nResults:")
        print(f"  Total (S) players found: {cleanup_stats['total_s_players']}")
        print(f"  Matched pairs: {cleanup_stats['matched_pairs']}")
        print(f"  User contexts updated: {cleanup_stats['user_contexts_updated']}")
        print(f"  (S) players deactivated: {cleanup_stats['s_players_deactivated']}")
        print(f"  Unmatched (S) players: {cleanup_stats['unmatched_s_players']}")
        print(f"  Remaining active (S) players: {remaining['count']}")
        print()
        
        if cleanup_stats['errors']:
            print("Errors encountered:")
            for error in cleanup_stats['errors']:
                print(f"  • {error}")
        else:
            print("✓ No errors")
        
        print("=" * 80)
        
        return cleanup_stats
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up duplicate (S) player records')
    parser.add_argument('--env', choices=['local', 'production'], default='local',
                      help='Environment to run against')
    parser.add_argument('--live', action='store_true',
                      help='Apply changes (default is dry-run)')
    
    args = parser.parse_args()
    
    if args.env == 'production':
        db_url = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"
        print("⚠️  WARNING: Running against PRODUCTION database")
    else:
        db_url = "postgresql://rossfreedman@localhost:5432/rally"
        print("Running against LOCAL database")
    
    print()
    
    if args.live:
        confirm = input(f"This will modify the {args.env.upper()} database. Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
    
    cleanup_duplicates(db_url, dry_run=not args.live)

