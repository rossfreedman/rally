#!/usr/bin/env python3
"""
Admin Player Audit Script

This script audits the player matching system by:
1. Loading all registered Rally users from the database
2. Attempting to match each user to a Tenniscores Player ID
3. Generating a summary report of matches, non-matches, and conflicts

Usage:
    python scripts/admin_player_audit.py [--dry-run] [--detailed]
"""
"""
⚠️  DEPRECATED SCRIPT ⚠️
This script references the old users.tenniscores_player_id column which has been removed.
The new schema uses user_player_associations table for many-to-many relationships.
Consider using the new association-based queries instead.
"""

import sys
import os
import argparse
from typing import Dict, List, Tuple

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query
from utils.match_utils import find_player_id_by_club_name, load_players_data
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def get_all_users() -> List[Dict]:
    """
    Get all registered Rally users with their club and series information.
    
    Returns:
        list: List of user dictionaries with club and series names
    """
    query = """
        SELECT u.id, u.first_name, u.last_name, u.email, u.tenniscores_player_id,
               c.name as club_name, s.name as series_name
        FROM users u
        LEFT JOIN clubs c ON u.club_id = c.id
        LEFT JOIN series s ON u.series_id = s.id
        ORDER BY u.last_name, u.first_name
    """
    return execute_query(query)

def audit_player_matching(detailed: bool = False) -> Dict:
    """
    Audit all users for player ID matching.
    
    Args:
        detailed: If True, include detailed match information
        
    Returns:
        dict: Summary statistics and detailed results
    """
    logger.info("Loading users from database...")
    users = get_all_users()
    logger.info(f"Found {len(users)} registered users")
    
    logger.info("Loading Tenniscores players data...")
    players_data = load_players_data()
    logger.info(f"Loaded {len(players_data)} Tenniscores players")
    
    # Initialize counters
    total_users = len(users)
    already_matched = 0
    newly_matched = 0
    no_match = 0
    multiple_matches = 0
    missing_data = 0
    
    # Results lists
    already_matched_users = []
    newly_matched_users = []
    no_match_users = []
    multiple_match_users = []
    missing_data_users = []
    
    logger.info("Auditing player matches...")
    
    for user in users:
        user_id = user['id']
        first_name = user['first_name']
        last_name = user['last_name']
        email = user['email']
        existing_player_id = user['tenniscores_player_id']
        club_name = user['club_name']
        series_name = user['series_name']
        
        # Check for missing required data
        if not all([first_name, last_name, club_name, series_name]):
            missing_data += 1
            missing_data_users.append({
                'user_id': user_id,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'club': club_name,
                'series': series_name,
                'missing_fields': [
                    field for field, value in [
                        ('first_name', first_name),
                        ('last_name', last_name),
                        ('club', club_name),
                        ('series', series_name)
                    ] if not value
                ]
            })
            continue
        
        # Check if already has a player ID
        if existing_player_id:
            already_matched += 1
            if detailed:
                already_matched_users.append({
                    'user_id': user_id,
                    'email': email,
                    'name': f"{first_name} {last_name}",
                    'club': club_name,
                    'series': series_name,
                    'player_id': existing_player_id
                })
            continue
        
        # Attempt to find player ID
        try:
            # Temporarily set logging level to WARNING to reduce noise
            match_logger = logging.getLogger('utils.match_utils')
            original_level = match_logger.level
            match_logger.setLevel(logging.WARNING)
            
            found_player_id = find_player_id_by_club_name(
                first_name=first_name,
                last_name=last_name,
                series_mapping_id=series_name,
                club_name=club_name,
                players_data=players_data
            )
            
            # Restore logging level
            match_logger.setLevel(original_level)
            
            if found_player_id:
                newly_matched += 1
                newly_matched_users.append({
                    'user_id': user_id,
                    'email': email,
                    'name': f"{first_name} {last_name}",
                    'club': club_name,
                    'series': series_name,
                    'player_id': found_player_id
                })
            else:
                # Check if this was due to multiple matches
                # We'll need to do a manual check for this
                no_match += 1
                no_match_users.append({
                    'user_id': user_id,
                    'email': email,
                    'name': f"{first_name} {last_name}",
                    'club': club_name,
                    'series': series_name
                })
                
        except Exception as e:
            logger.warning(f"Error matching {first_name} {last_name}: {str(e)}")
            no_match += 1
            no_match_users.append({
                'user_id': user_id,
                'email': email,
                'name': f"{first_name} {last_name}",
                'club': club_name,
                'series': series_name,
                'error': str(e)
            })
    
    # Compile results
    results = {
        'summary': {
            'total_users': total_users,
            'already_matched': already_matched,
            'newly_matched': newly_matched,
            'no_match': no_match,
            'multiple_matches': multiple_matches,
            'missing_data': missing_data
        }
    }
    
    if detailed:
        results['details'] = {
            'already_matched_users': already_matched_users,
            'newly_matched_users': newly_matched_users,
            'no_match_users': no_match_users,
            'multiple_match_users': multiple_match_users,
            'missing_data_users': missing_data_users
        }
    
    return results

def print_audit_summary(results: Dict):
    """Print a formatted summary of the audit results."""
    summary = results['summary']
    
    print("\n" + "="*60)
    print("RALLY PLAYER MATCHING AUDIT SUMMARY")
    print("="*60)
    print(f"Total registered users:        {summary['total_users']:5d}")
    print(f"Already matched users:         {summary['already_matched']:5d}")
    print(f"Newly matched users:           {summary['newly_matched']:5d}")
    print(f"Users with no match:           {summary['no_match']:5d}")
    print(f"Users with multiple matches:   {summary['multiple_matches']:5d}")
    print(f"Users with missing data:       {summary['missing_data']:5d}")
    print("-"*60)
    
    total_matchable = summary['total_users'] - summary['missing_data']
    total_matched = summary['already_matched'] + summary['newly_matched']
    
    if total_matchable > 0:
        match_rate = (total_matched / total_matchable) * 100
        print(f"Overall match rate:            {match_rate:5.1f}%")
    
    print("="*60)

def print_detailed_results(results: Dict, section: str = None):
    """Print detailed results for a specific section or all sections."""
    if 'details' not in results:
        print("No detailed results available. Run with --detailed flag.")
        return
    
    details = results['details']
    
    sections_to_print = [section] if section else [
        'newly_matched_users', 'no_match_users', 'missing_data_users'
    ]
    
    for section_name in sections_to_print:
        if section_name not in details:
            continue
            
        users = details[section_name]
        if not users:
            continue
            
        print(f"\n{section_name.replace('_', ' ').title()}:")
        print("-" * 40)
        
        for user in users:
            if section_name == 'newly_matched_users':
                print(f"  {user['name']} ({user['email']})")
                print(f"    Club: {user['club']}, Series: {user['series']}")
                print(f"    Player ID: {user['player_id']}")
            elif section_name == 'no_match_users':
                print(f"  {user['name']} ({user['email']})")
                print(f"    Club: {user['club']}, Series: {user['series']}")
                if 'error' in user:
                    print(f"    Error: {user['error']}")
            elif section_name == 'missing_data_users':
                print(f"  {user['first_name']} {user['last_name']} ({user['email']})")
                print(f"    Missing: {', '.join(user['missing_fields'])}")
            
            print()

def main():
    parser = argparse.ArgumentParser(description='Audit Rally user to Tenniscores Player ID matching')
    parser.add_argument('--detailed', action='store_true', 
                        help='Include detailed results for each category')
    parser.add_argument('--show-section', choices=['newly_matched', 'no_match', 'missing_data'],
                        help='Show detailed results for a specific section only')
    
    args = parser.parse_args()
    
    try:
        # Run the audit
        results = audit_player_matching(detailed=args.detailed or args.show_section)
        
        # Print summary
        print_audit_summary(results)
        
        # Print detailed results if requested
        if args.detailed:
            print_detailed_results(results)
        elif args.show_section:
            section_map = {
                'newly_matched': 'newly_matched_users',
                'no_match': 'no_match_users',
                'missing_data': 'missing_data_users'
            }
            print_detailed_results(results, section_map[args.show_section])
        
        print("\nAudit completed successfully!")
        
    except Exception as e:
        logger.error(f"Audit failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 