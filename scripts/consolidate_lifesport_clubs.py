#!/usr/bin/env python3
"""
Consolidate Lifesport club variations - Merge "Lifesport Lshire" into "Lifesportlshire"

This script safely consolidates club ID 8711 ("Lifesport Lshire") into club ID 14202 ("Lifesportlshire")
by updating all foreign key references without losing any data.

Usage:
    # Dry run (default)
    python3 scripts/consolidate_lifesport_clubs.py
    
    # Apply changes
    python3 scripts/consolidate_lifesport_clubs.py --live
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one, execute_update

# Staging database URL (from repo rules)
STAGING_DB_URL = "postgresql://postgres:SNDcbFXgqCOkjBRzAzqGbdRvyhftepsY@switchback.proxy.rlwy.net:28473/railway"

# Production database URL (from repo rules)
PRODUCTION_DB_URL = "postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway"

# Club consolidation mapping
SOURCE_CLUB_ID = 8711  # "Lifesport Lshire" - to be merged
TARGET_CLUB_ID = 14202  # "Lifesportlshire" - the correct one

def consolidate_lifesport_clubs(dry_run=True, staging=False, production=False):
    """
    Consolidate "Lifesport Lshire" (8711) into "Lifesportlshire" (14202)
    
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
    print("CONSOLIDATING LIFESPORT CLUBS")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes will be made)' if dry_run else 'LIVE UPDATE'}")
    if production:
        print(f"Environment: PRODUCTION")
    elif staging:
        print(f"Environment: STAGING")
    print()
    print(f"Source Club: ID {SOURCE_CLUB_ID} ('Lifesport Lshire')")
    print(f"Target Club: ID {TARGET_CLUB_ID} ('Lifesportlshire')")
    print()
    
    # Verify clubs exist
    print("1. Verifying clubs exist...")
    source_club = execute_query_one("SELECT id, name, logo_filename FROM clubs WHERE id = %s", [SOURCE_CLUB_ID])
    target_club = execute_query_one("SELECT id, name, logo_filename FROM clubs WHERE id = %s", [TARGET_CLUB_ID])
    
    if not source_club:
        print(f"❌ ERROR: Source club (ID {SOURCE_CLUB_ID}) not found!")
        return False
    
    if not target_club:
        print(f"❌ ERROR: Target club (ID {TARGET_CLUB_ID}) not found!")
        return False
    
    print(f"✅ Source club: '{source_club['name']}' (ID: {source_club['id']})")
    print(f"✅ Target club: '{target_club['name']}' (ID: {target_club['id']})")
    print()
    
    # Check what needs to be updated
    print("2. Analyzing data to be consolidated...")
    
    # Players
    players_query = """
        SELECT COUNT(*) as count
        FROM players
        WHERE club_id = %s AND is_active = true
    """
    player_count = execute_query_one(players_query, [SOURCE_CLUB_ID])
    print(f"   Active players: {player_count['count']}")
    
    # Teams
    teams_query = """
        SELECT COUNT(*) as count
        FROM teams
        WHERE club_id = %s
    """
    team_count = execute_query_one(teams_query, [SOURCE_CLUB_ID])
    print(f"   Teams: {team_count['count']}")
    
    # User contexts (if any)
    contexts_query = """
        SELECT COUNT(*) as count
        FROM user_contexts
        WHERE club = %s
    """
    context_count = execute_query_one(contexts_query, [source_club['name']])
    print(f"   User contexts: {context_count['count']}")
    
    # Club leagues (if any)
    club_leagues_query = """
        SELECT COUNT(*) as count
        FROM club_leagues
        WHERE club_id = %s
    """
    club_leagues_count = execute_query_one(club_leagues_query, [SOURCE_CLUB_ID])
    print(f"   Club-league associations: {club_leagues_count['count']}")
    
    print()
    
    if dry_run:
        print("3. DRY RUN - What would be updated:")
        print("   - Update all players.club_id: 8711 → 14202")
        print("   - Update all teams.club_id: 8711 → 14202")
        print("   - Update all user_contexts.club: 'Lifesport Lshire' → 'Lifesportlshire'")
        print("   - Update all club_leagues.club_id: 8711 → 14202 (if exists)")
        print("   - Delete source club (ID 8711) after consolidation")
        print()
        print("=" * 80)
        print("DRY RUN COMPLETE - No changes made")
        print("=" * 80)
        print("To apply these changes, run with --live")
        return True
    
    # Apply consolidation
    print("3. Applying consolidation...")
    
    updates_applied = 0
    
    # Update players
    print(f"   Updating {player_count['count']} players...")
    update_players = """
        UPDATE players
        SET club_id = %s
        WHERE club_id = %s
    """
    execute_update(update_players, [TARGET_CLUB_ID, SOURCE_CLUB_ID])
    updates_applied += player_count['count']
    print(f"   ✅ Updated players")
    
    # Update teams
    print(f"   Updating {team_count['count']} teams...")
    update_teams = """
        UPDATE teams
        SET club_id = %s
        WHERE club_id = %s
    """
    execute_update(update_teams, [TARGET_CLUB_ID, SOURCE_CLUB_ID])
    updates_applied += team_count['count']
    print(f"   ✅ Updated teams")
    
    # Update user contexts
    if context_count['count'] > 0:
        print(f"   Updating {context_count['count']} user contexts...")
        update_contexts = """
            UPDATE user_contexts
            SET club = %s
            WHERE club = %s
        """
        execute_update(update_contexts, [target_club['name'], source_club['name']])
        updates_applied += context_count['count']
        print(f"   ✅ Updated user contexts")
    
    # Update club_leagues (merge if exists)
    if club_leagues_count['count'] > 0:
        print(f"   Handling {club_leagues_count['count']} club-league associations...")
        # First, check if target club already has associations for same leagues
        existing_associations = execute_query("""
            SELECT league_id FROM club_leagues WHERE club_id = %s
        """, [TARGET_CLUB_ID])
        existing_league_ids = {a['league_id'] for a in existing_associations}
        
        # Get source club associations
        source_associations = execute_query("""
            SELECT league_id FROM club_leagues WHERE club_id = %s
        """, [SOURCE_CLUB_ID])
        
        # Update to target club, but skip if target already has that league
        for assoc in source_associations:
            if assoc['league_id'] not in existing_league_ids:
                update_club_league = """
                    UPDATE club_leagues
                    SET club_id = %s
                    WHERE club_id = %s AND league_id = %s
                """
                execute_update(update_club_league, [TARGET_CLUB_ID, SOURCE_CLUB_ID, assoc['league_id']])
                updates_applied += 1
            else:
                # Delete duplicate - target already has this league
                delete_duplicate = """
                    DELETE FROM club_leagues
                    WHERE club_id = %s AND league_id = %s
                """
                execute_update(delete_duplicate, [SOURCE_CLUB_ID, assoc['league_id']])
        
        print(f"   ✅ Updated club-league associations")
    
    # Delete source club (after all references are updated)
    print(f"   Deleting source club (ID {SOURCE_CLUB_ID})...")
    delete_club = """
        DELETE FROM clubs
        WHERE id = %s
    """
    execute_update(delete_club, [SOURCE_CLUB_ID])
    print(f"   ✅ Deleted source club")
    
    print()
    print("=" * 80)
    print(f"CONSOLIDATION COMPLETE - Updated {updates_applied} records")
    print("=" * 80)
    
    # Verify consolidation
    print("4. Verifying consolidation...")
    
    # Check no players remain with source club
    remaining_players = execute_query_one("""
        SELECT COUNT(*) as count FROM players WHERE club_id = %s
    """, [SOURCE_CLUB_ID])
    
    # Check no teams remain with source club
    remaining_teams = execute_query_one("""
        SELECT COUNT(*) as count FROM teams WHERE club_id = %s
    """, [SOURCE_CLUB_ID])
    
    if remaining_players['count'] == 0 and remaining_teams['count'] == 0:
        print("✅ Verification successful - No remaining references to source club")
    else:
        print(f"⚠️  Warning: {remaining_players['count']} players and {remaining_teams['count']} teams still reference source club")
    
    # Check target club has all the data
    target_players = execute_query_one("""
        SELECT COUNT(*) as count FROM players WHERE club_id = %s AND is_active = true
    """, [TARGET_CLUB_ID])
    target_teams = execute_query_one("""
        SELECT COUNT(*) as count FROM teams WHERE club_id = %s
    """, [TARGET_CLUB_ID])
    
    print(f"✅ Target club now has {target_players['count']} active players and {target_teams['count']} teams")
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Consolidate Lifesport club variations')
    parser.add_argument('--live', action='store_true', help='Apply changes (default is dry run)')
    parser.add_argument('--staging', action='store_true', help='Connect to staging database')
    parser.add_argument('--production', action='store_true', help='Connect to production database')
    args = parser.parse_args()
    
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
    
    consolidate_lifesport_clubs(dry_run=not args.live, staging=args.staging, production=args.production)

