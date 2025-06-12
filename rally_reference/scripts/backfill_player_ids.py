#!/usr/bin/env python3
"""
Backfill Player IDs Script

This script backfills tenniscores_player_id for existing Rally users who don't have one set.
It uses the same matching logic as the registration system.

Usage:
    python scripts/backfill_player_ids.py [--dry-run] [--batch-size 50]
"""

import sys
import os
import argparse
from typing import Dict, List, Tuple

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_update
from utils.match_utils import find_player_id_by_club_name, load_players_data
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def get_users_without_player_ids() -> List[Dict]:
    """
    Get all Rally users who don't have a tenniscores_player_id set.
    
    Returns:
        list: List of user dictionaries without player IDs
    """
    query = """
        SELECT u.id, u.first_name, u.last_name, u.email,
               c.name as club_name, s.name as series_name
        FROM users u
        LEFT JOIN clubs c ON u.club_id = c.id
        LEFT JOIN series s ON u.series_id = s.id
        WHERE u.tenniscores_player_id IS NULL
        ORDER BY u.last_name, u.first_name
    """
    return execute_query(query)

def update_user_player_id(user_id: int, player_id: str) -> bool:
    """
    Update a user's tenniscores_player_id in the database.
    
    Args:
        user_id: The user's ID
        player_id: The Tenniscores Player ID to set
        
    Returns:
        bool: True if update was successful
    """
    query = """
        UPDATE users 
        SET tenniscores_player_id = %(player_id)s 
        WHERE id = %(user_id)s
    """
    return execute_update(query, {'user_id': user_id, 'player_id': player_id})

def backfill_player_ids(dry_run: bool = False, batch_size: int = 50) -> Dict:
    """
    Backfill player IDs for users who don't have them.
    
    Args:
        dry_run: If True, don't actually update the database
        batch_size: Number of users to process in each batch
        
    Returns:
        dict: Summary of results
    """
    logger.info("Loading users without player IDs...")
    users = get_users_without_player_ids()
    logger.info(f"Found {len(users)} users without player IDs")
    
    if not users:
        logger.info("No users need backfilling!")
        return {
            'total_processed': 0,
            'successful_matches': 0,
            'no_matches': 0,
            'errors': 0,
            'updated_users': [],
            'no_match_users': [],
            'error_users': []
        }
    
    logger.info("Loading Tenniscores players data...")
    players_data = load_players_data()
    logger.info(f"Loaded {len(players_data)} Tenniscores players")
    
    # Initialize results tracking
    total_processed = 0
    successful_matches = 0
    no_matches = 0
    errors = 0
    
    updated_users = []
    no_match_users = []
    error_users = []
    
    # Process users in batches
    for i in range(0, len(users), batch_size):
        batch = users[i:i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} users)...")
        
        for user in batch:
            user_id = user['id']
            first_name = user['first_name']
            last_name = user['last_name']
            email = user['email']
            club_name = user['club_name']
            series_name = user['series_name']
            
            total_processed += 1
            
            # Check for missing required data
            if not all([first_name, last_name, club_name, series_name]):
                logger.warning(f"Skipping user {email} - missing required data")
                errors += 1
                error_users.append({
                    'user_id': user_id,
                    'email': email,
                    'name': f"{first_name} {last_name}",
                    'error': 'Missing required data (name, club, or series)'
                })
                continue
            
            try:
                # Attempt to find player ID
                player_id = find_player_id_by_club_name(
                    first_name=first_name,
                    last_name=last_name,
                    series_mapping_id=series_name,
                    club_name=club_name,
                    players_data=players_data
                )
                
                if player_id:
                    logger.info(f"Found match for {first_name} {last_name}: {player_id}")
                    
                    if not dry_run:
                        # Update the database
                        success = update_user_player_id(user_id, player_id)
                        if success:
                            successful_matches += 1
                            updated_users.append({
                                'user_id': user_id,
                                'email': email,
                                'name': f"{first_name} {last_name}",
                                'club': club_name,
                                'series': series_name,
                                'player_id': player_id
                            })
                        else:
                            logger.error(f"Failed to update database for {first_name} {last_name}")
                            errors += 1
                            error_users.append({
                                'user_id': user_id,
                                'email': email,
                                'name': f"{first_name} {last_name}",
                                'error': 'Database update failed'
                            })
                    else:
                        # Dry run - just count as successful
                        successful_matches += 1
                        updated_users.append({
                            'user_id': user_id,
                            'email': email,
                            'name': f"{first_name} {last_name}",
                            'club': club_name,
                            'series': series_name,
                            'player_id': player_id
                        })
                else:
                    logger.info(f"No match found for {first_name} {last_name} ({club_name}, {series_name})")
                    no_matches += 1
                    no_match_users.append({
                        'user_id': user_id,
                        'email': email,
                        'name': f"{first_name} {last_name}",
                        'club': club_name,
                        'series': series_name
                    })
                    
            except Exception as e:
                logger.error(f"Error processing {first_name} {last_name}: {str(e)}")
                errors += 1
                error_users.append({
                    'user_id': user_id,
                    'email': email,
                    'name': f"{first_name} {last_name}",
                    'error': str(e)
                })
    
    results = {
        'total_processed': total_processed,
        'successful_matches': successful_matches,
        'no_matches': no_matches,
        'errors': errors,
        'updated_users': updated_users,
        'no_match_users': no_match_users,
        'error_users': error_users
    }
    
    return results

def print_backfill_summary(results: Dict, dry_run: bool = False):
    """Print a formatted summary of the backfill results."""
    action = "would be updated" if dry_run else "updated"
    
    print("\n" + "="*60)
    print(f"PLAYER ID BACKFILL SUMMARY{'(DRY RUN)' if dry_run else ''}")
    print("="*60)
    print(f"Total users processed:         {results['total_processed']:5d}")
    print(f"Successful matches:            {results['successful_matches']:5d}")
    print(f"Users with no match:           {results['no_matches']:5d}")
    print(f"Errors encountered:            {results['errors']:5d}")
    print("-"*60)
    
    if results['total_processed'] > 0:
        success_rate = (results['successful_matches'] / results['total_processed']) * 100
        print(f"Match success rate:            {success_rate:5.1f}%")
    
    print("="*60)
    
    if dry_run and results['successful_matches'] > 0:
        print(f"\n{results['successful_matches']} users would be updated with Player IDs.")
        print("Run without --dry-run to actually update the database.")

def print_detailed_results(results: Dict, section: str = None):
    """Print detailed results for successful matches, no matches, or errors."""
    sections_to_print = [section] if section else ['updated_users', 'no_match_users', 'error_users']
    
    for section_name in sections_to_print:
        if section_name not in results:
            continue
            
        users = results[section_name]
        if not users:
            continue
            
        print(f"\n{section_name.replace('_', ' ').title()}:")
        print("-" * 40)
        
        for user in users:
            if section_name == 'updated_users':
                print(f"  {user['name']} ({user['email']})")
                print(f"    Club: {user['club']}, Series: {user['series']}")
                print(f"    Player ID: {user['player_id']}")
            elif section_name == 'no_match_users':
                print(f"  {user['name']} ({user['email']})")
                print(f"    Club: {user['club']}, Series: {user['series']}")
            elif section_name == 'error_users':
                print(f"  {user['name']} ({user['email']})")
                print(f"    Error: {user['error']}")
            
            print()

def main():
    parser = argparse.ArgumentParser(description='Backfill Tenniscores Player IDs for existing Rally users')
    parser.add_argument('--dry-run', action='store_true', 
                        help='Preview what would be updated without making changes')
    parser.add_argument('--batch-size', type=int, default=50,
                        help='Number of users to process in each batch (default: 50)')
    parser.add_argument('--detailed', action='store_true',
                        help='Show detailed results for each category')
    parser.add_argument('--show-section', choices=['updated', 'no_match', 'errors'],
                        help='Show detailed results for a specific section only')
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No database changes will be made")
    
    try:
        # Run the backfill
        results = backfill_player_ids(dry_run=args.dry_run, batch_size=args.batch_size)
        
        # Print summary
        print_backfill_summary(results, dry_run=args.dry_run)
        
        # Print detailed results if requested
        if args.detailed:
            print_detailed_results(results)
        elif args.show_section:
            section_map = {
                'updated': 'updated_users',
                'no_match': 'no_match_users',
                'errors': 'error_users'
            }
            print_detailed_results(results, section_map[args.show_section])
        
        print("\nBackfill completed successfully!")
        
        # Return appropriate exit code
        if results['errors'] > 0:
            logger.warning(f"Completed with {results['errors']} errors")
            sys.exit(1)
        else:
            sys.exit(0)
        
    except Exception as e:
        logger.error(f"Backfill failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 