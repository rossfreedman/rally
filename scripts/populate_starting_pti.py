#!/usr/bin/env python3
"""
Populate starting_pti field in players table from CSV file
===========================================================

This script reads the 'APTA Players - 2025 Season Starting PTI.csv' file
and populates the starting_pti column in the players table.

Matching logic:
- Matches by: first_name + last_name + series
- Handles case-insensitive matching
- Reports matches, mismatches, and updates

Usage:
    python scripts/populate_starting_pti.py [--dry-run] [--environment local|staging|production]
"""

import argparse
import csv
import os
import sys
from decimal import Decimal

# Add root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_query_one
from database_config import get_db_url


def load_starting_pti_from_csv(csv_path):
    """
    Load starting PTI data from CSV file.
    
    Returns:
        Dict mapping (first_name, last_name, series) to PTI value
    """
    if not os.path.exists(csv_path):
        print(f"❌ CSV file not found: {csv_path}")
        sys.exit(1)
    
    starting_pti_data = {}
    empty_pti_count = 0
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                first_name = row.get('First Name', '').strip()
                last_name = row.get('Last Name', '').strip()
                series = row.get('Series', '').strip()
                pti_str = row.get('PTI', '').strip()
                
                # Skip rows with empty PTI values
                if not pti_str:
                    empty_pti_count += 1
                    continue
                
                try:
                    pti_value = float(pti_str)
                except ValueError:
                    print(f"⚠️  Row {row_num}: Invalid PTI value '{pti_str}' for {first_name} {last_name}")
                    continue
                
                # Create lookup key: (first_name, last_name, series)
                # Normalize to lowercase for case-insensitive matching
                key = (first_name.lower(), last_name.lower(), series.lower())
                starting_pti_data[key] = pti_value
                
    except Exception as e:
        print(f"❌ Error loading CSV data: {e}")
        sys.exit(1)
    
    print(f"📊 Loaded {len(starting_pti_data)} starting PTI records from CSV")
    print(f"   (Skipped {empty_pti_count} rows with empty PTI values)")
    
    return starting_pti_data


def get_players_from_database(league_id=None):
    """
    Get all players from database.
    
    Returns:
        List of player dictionaries with id, first_name, last_name, series_name
    """
    query = """
        SELECT 
            p.id,
            p.first_name,
            p.last_name,
            s.display_name as series_name,
            p.starting_pti,
            p.league_id
        FROM players p
        JOIN series s ON p.series_id = s.id
        WHERE p.is_active = true
    """
    
    params = []
    if league_id:
        query += " AND p.league_id = %s"
        params.append(league_id)
    
    query += " ORDER BY p.last_name, p.first_name"
    
    try:
        players = execute_query(query, params)
        print(f"📊 Found {len(players)} active players in database")
        return players
    except Exception as e:
        print(f"❌ Error fetching players: {e}")
        sys.exit(1)


def update_starting_pti(player_id, pti_value, dry_run=False):
    """
    Update starting_pti for a specific player.
    
    Args:
        player_id: Database ID of player
        pti_value: Starting PTI value to set
        dry_run: If True, only print what would be updated
    """
    if dry_run:
        return True
    
    try:
        query = """
            UPDATE players 
            SET starting_pti = %s 
            WHERE id = %s
        """
        execute_query(query, [pti_value, player_id])
        return True
    except Exception as e:
        print(f"❌ Error updating player {player_id}: {e}")
        return False


def populate_starting_pti(csv_path, dry_run=False, league_id=None):
    """
    Main function to populate starting_pti from CSV.
    
    Args:
        csv_path: Path to CSV file
        dry_run: If True, only show what would be updated
        league_id: Optional league ID to filter players (None = all leagues)
    """
    print("\n🎯 Starting PTI Population")
    print("=" * 70)
    print(f"📅 {csv_path}")
    if dry_run:
        print("🔍 DRY RUN MODE - No database changes will be made")
    print()
    
    # Load CSV data
    csv_data = load_starting_pti_from_csv(csv_path)
    
    # Get players from database
    players = get_players_from_database(league_id)
    
    # Match and update
    matches = 0
    mismatches = 0
    updates = 0
    already_set = 0
    
    for player in players:
        player_id = player['id']
        first_name = player['first_name'] or ''
        last_name = player['last_name'] or ''
        series_name = player['series_name'] or ''
        current_starting_pti = player['starting_pti']
        
        # Create lookup key (lowercase for case-insensitive)
        key = (first_name.lower(), last_name.lower(), series_name.lower())
        
        # Try to find match in CSV
        pti_value = csv_data.get(key)
        
        if pti_value is not None:
            matches += 1
            
            # Check if already set to same value
            if current_starting_pti is not None and abs(float(current_starting_pti) - pti_value) < 0.01:
                already_set += 1
                continue
            
            # Update the player
            if dry_run:
                print(f"✅ WOULD UPDATE: {first_name} {last_name} ({series_name}) -> {pti_value}")
            else:
                if update_starting_pti(player_id, pti_value, dry_run=False):
                    updates += 1
                    print(f"✅ Updated: {first_name} {last_name} ({series_name}) -> {pti_value}")
        else:
            mismatches += 1
            # Only show first 10 mismatches to avoid cluttering output
            if mismatches <= 10:
                print(f"⚠️  No match: {first_name} {last_name} ({series_name})")
    
    # Print summary
    print()
    print("=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"✅ Matches found:        {matches}")
    print(f"📝 Updates performed:    {updates}")
    print(f"⏭️  Already set:          {already_set}")
    print(f"⚠️  No CSV match:         {mismatches}")
    print()
    
    if dry_run:
        print("🔍 This was a DRY RUN - run without --dry-run to apply changes")
    else:
        print("✅ Starting PTI population completed!")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Populate starting_pti field from CSV file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without making changes'
    )
    parser.add_argument(
        '--environment',
        choices=['local', 'staging', 'production'],
        default='local',
        help='Database environment to update (default: local)'
    )
    parser.add_argument(
        '--league-id',
        type=int,
        help='Only update players for specific league ID'
    )
    
    args = parser.parse_args()
    
    # Set database URL based on environment
    if args.environment == 'staging':
        db_url = os.getenv('DATABASE_STAGING_URL')
        if not db_url:
            print("❌ DATABASE_STAGING_URL not set in environment")
            sys.exit(1)
    elif args.environment == 'production':
        db_url = os.getenv('DATABASE_PUBLIC_URL')
        if not db_url:
            print("❌ DATABASE_PUBLIC_URL not set in environment")
            sys.exit(1)
        
        # Extra confirmation for production
        print("⚠️  WARNING: You are about to modify PRODUCTION database!")
        response = input("Type 'PRODUCTION' to confirm: ").strip()
        if response != 'PRODUCTION':
            print("❌ Production update cancelled")
            sys.exit(0)
    else:
        db_url = "postgresql://rossfreedman@localhost/rally"
    
    print(f"🗄️  Database: {args.environment}")
    
    # CSV file path
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data',
        'APTA Players - 2025 Season Starting PTI.csv'
    )
    
    # Run population
    populate_starting_pti(csv_path, dry_run=args.dry_run, league_id=args.league_id)


if __name__ == '__main__':
    main()

