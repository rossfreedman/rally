#!/usr/bin/env python3
"""
Post-ETL Club Cleanup Script

This script runs after ETL imports to:
1. Detect duplicate clubs that were recreated
2. Automatically consolidate them into the correct club
3. Prevent data integrity issues from recurring

Usage:
    # Dry run (default)
    python3 data/etl/import/post_etl_club_cleanup.py
    
    # Apply changes
    python3 data/etl/import/post_etl_club_cleanup.py --live
    
    # Staging
    python3 data/etl/import/post_etl_club_cleanup.py --live --staging
    
    # Production
    python3 data/etl/import/post_etl_club_cleanup.py --live --production
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add project root to path (data/etl/import -> data/etl -> data -> project root)
project_root = os.path.join(os.path.dirname(__file__), '..', '..', '..')
sys.path.insert(0, project_root)

from database_utils import execute_query, execute_query_one, execute_update

# Staging database URL
STAGING_DB_URL = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"

# Production database URL
PRODUCTION_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

# Known club consolidation mappings
# Format: {source_club_name: target_club_name}
CLUB_CONSOLIDATION_MAPPINGS = {
    "Lifesport Lshire": "Lifesportlshire",
    # Add more mappings here as needed
    # "Winnetka I": "Winnetka",
    # "Winnetka II": "Winnetka",
}

def post_etl_club_cleanup(dry_run=True, staging=False, production=False):
    """
    Clean up duplicate clubs created by ETL imports
    
    Args:
        dry_run: If True, only show what would be changed without making updates
        staging: If True, connect to staging database
        production: If True, connect to production database
    """
    
    # Set database URL if requested
    if production:
        os.environ['DATABASE_URL'] = PRODUCTION_DB_URL
        print("⚠️  PRODUCTION MODE - Connecting to production database")
        print("=" * 80)
    elif staging:
        os.environ['DATABASE_URL'] = STAGING_DB_URL
        print("⚠️  STAGING MODE - Connecting to staging database")
        print("=" * 80)
    
    print("=" * 80)
    print("POST-ETL CLUB CLEANUP")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes will be made)' if dry_run else 'LIVE UPDATE'}")
    if production:
        print(f"Environment: PRODUCTION")
    elif staging:
        print(f"Environment: STAGING")
    print()
    
    consolidations_applied = 0
    total_records_updated = 0
    
    # Process each consolidation mapping
    for source_club_name, target_club_name in CLUB_CONSOLIDATION_MAPPINGS.items():
        print(f"Processing: '{source_club_name}' -> '{target_club_name}'")
        print("-" * 80)
        
        # Check if source club exists
        source_club = execute_query_one(
            "SELECT id, name FROM clubs WHERE name = %s", [source_club_name]
        )
        
        if not source_club:
            print(f"   ✅ No duplicate found - '{source_club_name}' does not exist")
            print()
            continue
        
        source_club_id = source_club['id']
        print(f"   ⚠️  Found duplicate club: '{source_club_name}' (ID: {source_club_id})")
        
        # Check if target club exists
        target_club = execute_query_one(
            "SELECT id, name FROM clubs WHERE name = %s", [target_club_name]
        )
        
        if not target_club:
            print(f"   ❌ ERROR: Target club '{target_club_name}' not found!")
            print(f"   Skipping consolidation for '{source_club_name}'")
            print()
            continue
        
        target_club_id = target_club['id']
        print(f"   ✅ Target club found: '{target_club_name}' (ID: {target_club_id})")
        print()
        
        # Count what needs to be moved
        print("   Analyzing data to be consolidated...")
        
        # Players
        player_count = execute_query_one(
            "SELECT COUNT(*) as count FROM players WHERE club_id = %s AND is_active = true",
            [source_club_id]
        )
        player_count_val = player_count['count'] if player_count else 0
        print(f"      Active players: {player_count_val}")
        
        # Teams
        team_count = execute_query_one(
            "SELECT COUNT(*) as count FROM teams WHERE club_id = %s",
            [source_club_id]
        )
        team_count_val = team_count['count'] if team_count else 0
        print(f"      Teams: {team_count_val}")
        
        # User contexts
        context_count = execute_query_one(
            "SELECT COUNT(*) as count FROM user_contexts WHERE club = %s",
            [source_club_name]
        )
        context_count_val = context_count['count'] if context_count else 0
        print(f"      User contexts: {context_count_val}")
        
        # Club-league associations
        club_league_count = execute_query_one(
            "SELECT COUNT(*) as count FROM club_leagues WHERE club_id = %s",
            [source_club_id]
        )
        club_league_count_val = club_league_count['count'] if club_league_count else 0
        print(f"      Club-league associations: {club_league_count_val}")
        print()
        
        if dry_run:
            print(f"   DRY RUN - Would consolidate {player_count_val + team_count_val + context_count_val} records")
            print()
            continue
        
        # Apply consolidation
        print("   Applying consolidation...")
        records_updated = 0
        
        # Update players
        if player_count_val > 0:
            update_players = "UPDATE players SET club_id = %s WHERE club_id = %s"
            execute_update(update_players, [target_club_id, source_club_id])
            records_updated += player_count_val
            print(f"      ✅ Updated {player_count_val} players")
        
        # Update teams
        if team_count_val > 0:
            update_teams = "UPDATE teams SET club_id = %s WHERE club_id = %s"
            execute_update(update_teams, [target_club_id, source_club_id])
            records_updated += team_count_val
            print(f"      ✅ Updated {team_count_val} teams")
        
        # Update user contexts
        if context_count_val > 0:
            update_contexts = "UPDATE user_contexts SET club = %s WHERE club = %s"
            execute_update(update_contexts, [target_club_name, source_club_name])
            records_updated += context_count_val
            print(f"      ✅ Updated {context_count_val} user contexts")
        
        # Handle club-league associations
        if club_league_count_val > 0:
            # Get existing associations for target club
            existing_associations = execute_query(
                "SELECT league_id FROM club_leagues WHERE club_id = %s",
                [target_club_id]
            )
            existing_league_ids = {a['league_id'] for a in existing_associations}
            
            # Get source club associations
            source_associations = execute_query(
                "SELECT league_id FROM club_leagues WHERE club_id = %s",
                [source_club_id]
            )
            
            # Move associations that don't already exist in target
            moved = 0
            for assoc in source_associations:
                if assoc['league_id'] not in existing_league_ids:
                    update_club_league = """
                        UPDATE club_leagues SET club_id = %s
                        WHERE club_id = %s AND league_id = %s
                    """
                    execute_update(update_club_league, [target_club_id, source_club_id, assoc['league_id']])
                    moved += 1
                else:
                    # Delete duplicate
                    delete_duplicate = """
                        DELETE FROM club_leagues WHERE club_id = %s AND league_id = %s
                    """
                    execute_update(delete_duplicate, [source_club_id, assoc['league_id']])
            
            records_updated += moved
            print(f"      ✅ Handled {club_league_count_val} club-league associations")
        
        # Delete source club
        delete_club = "DELETE FROM clubs WHERE id = %s"
        execute_update(delete_club, [source_club_id])
        print(f"      ✅ Deleted duplicate club (ID: {source_club_id})")
        
        consolidations_applied += 1
        total_records_updated += records_updated
        
        print()
        
        # Verify consolidation
        remaining_check = execute_query_one(
            """
            SELECT 
                (SELECT COUNT(*) FROM players WHERE club_id = %s) as players,
                (SELECT COUNT(*) FROM teams WHERE club_id = %s) as teams
            """,
            [source_club_id, source_club_id]
        )
        
        if remaining_check and remaining_check['players'] == 0 and remaining_check['teams'] == 0:
            print(f"   ✅ Verification: Consolidation successful for '{source_club_name}'")
        else:
            print(f"   ⚠️  Warning: Some records may still reference source club")
        print()
    
    print("=" * 80)
    if dry_run:
        print("DRY RUN COMPLETE - No changes made")
        print("=" * 80)
        print("To apply these changes, run with --live")
    else:
        print(f"CLEANUP COMPLETE")
        print(f"  Consolidations applied: {consolidations_applied}")
        print(f"  Total records updated: {total_records_updated}")
        print("=" * 80)
    
    return True

def detect_duplicate_clubs():
    """
    Detect potential duplicate clubs that might need consolidation
    Returns a list of potential duplicates
    """
    print("=" * 80)
    print("DETECTING POTENTIAL DUPLICATE CLUBS")
    print("=" * 80)
    print()
    
    # Find clubs with similar names (case-insensitive, with variations)
    potential_duplicates = []
    
    # Check for known patterns
    patterns = [
        ("lifesport", "lifesport"),
        ("winnetka", "winnetka"),
    ]
    
    for pattern, base_name in patterns:
        clubs = execute_query(f"""
            SELECT id, name, 
                   (SELECT COUNT(*) FROM players WHERE club_id = clubs.id AND is_active = true) as player_count,
                   (SELECT COUNT(*) FROM teams WHERE club_id = clubs.id) as team_count
            FROM clubs
            WHERE name ILIKE %s
            ORDER BY name
        """, [f'%{pattern}%'])
        
        if len(clubs) > 1:
            print(f"Potential duplicates for '{base_name}':")
            for club in clubs:
                print(f"  ID: {club['id']}, Name: '{club['name']}', Players: {club['player_count']}, Teams: {club['team_count']}")
            print()
    
    return potential_duplicates

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Post-ETL club cleanup script')
    parser.add_argument('--live', action='store_true', help='Apply changes (default is dry run)')
    parser.add_argument('--staging', action='store_true', help='Connect to staging database')
    parser.add_argument('--production', action='store_true', help='Connect to production database')
    parser.add_argument('--detect', action='store_true', help='Detect potential duplicate clubs')
    args = parser.parse_args()
    
    if args.detect:
        detect_duplicate_clubs()
    else:
        if args.production and args.live:
            print("⚠️  WARNING: You are about to make changes to PRODUCTION database!")
            print("⚠️  Make sure you have a backup before proceeding.")
            response = input("Type 'yes' to continue: ")
            if response.lower() != 'yes':
                print("Aborted.")
                sys.exit(0)
        elif args.staging and args.live:
            print("⚠️  WARNING: You are about to make changes to STAGING database!")
            response = input("Type 'yes' to continue: ")
            if response.lower() != 'yes':
                print("Aborted.")
                sys.exit(0)
        
        post_etl_club_cleanup(dry_run=not args.live, staging=args.staging, production=args.production)

