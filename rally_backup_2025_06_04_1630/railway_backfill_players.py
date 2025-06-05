#!/usr/bin/env python3
"""
Railway Player ID Backfill Script

This script backfills tenniscores_player_id for existing Railway users who don't have one set.
It uses the same matching logic as the registration system.
"""

import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List
import logging

# Add project root to path
sys.path.append('.')

from utils.match_utils import find_player_id_by_club_name, load_players_data

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Railway database URL
RAILWAY_DB_URL = 'postgresql://postgres:HKJnPmxKZmKiIglQhQPSmfcAjTgBsSIq@ballast.proxy.rlwy.net:40911/railway'

def get_railway_users_without_player_ids() -> List[Dict]:
    """
    Get all Railway users who don't have a tenniscores_player_id set.
    
    Returns:
        list: List of user dictionaries without player IDs
    """
    conn = psycopg2.connect(RAILWAY_DB_URL, cursor_factory=RealDictCursor)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT u.id, u.first_name, u.last_name, u.email,
               c.name as club_name, s.name as series_name
        FROM users u
        LEFT JOIN clubs c ON u.club_id = c.id
        LEFT JOIN series s ON u.series_id = s.id
        WHERE u.tenniscores_player_id IS NULL
        ORDER BY u.last_name, u.first_name
    """)
    
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return [dict(user) for user in users]

def update_railway_user_player_id(user_id: int, player_id: str) -> bool:
    """
    Update a user's tenniscores_player_id in the Railway database.
    
    Args:
        user_id: The user's ID
        player_id: The Tenniscores Player ID to set
        
    Returns:
        bool: True if update was successful
    """
    try:
        conn = psycopg2.connect(RAILWAY_DB_URL)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users 
            SET tenniscores_player_id = %s 
            WHERE id = %s
        """, (player_id, user_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to update user {user_id}: {str(e)}")
        return False

def backfill_railway_player_ids() -> Dict:
    """
    Backfill player IDs for Railway users who don't have them.
    
    Returns:
        dict: Summary of results
    """
    logger.info("Loading Railway users without player IDs...")
    users = get_railway_users_without_player_ids()
    logger.info(f"Found {len(users)} users without player IDs")
    
    if not users:
        logger.info("No users need backfilling!")
        return {
            'total_processed': 0,
            'successful_matches': 0,
            'no_matches': 0,
            'updated_users': []
        }
    
    logger.info("Loading Tenniscores players data...")
    players_data = load_players_data()
    logger.info(f"Loaded {len(players_data)} Tenniscores players")
    
    # Initialize results tracking
    total_processed = 0
    successful_matches = 0
    no_matches = 0
    
    updated_users = []
    no_match_users = []
    
    for user in users:
        user_id = user['id']
        first_name = user['first_name']
        last_name = user['last_name']
        email = user['email']
        club_name = user['club_name']
        series_name = user['series_name']
        
        total_processed += 1
        print(f"\n🔍 Processing {first_name} {last_name} ({club_name}, {series_name})...")
        
        try:
            # Attempt to find player ID using our enhanced matching logic
            player_id = find_player_id_by_club_name(
                first_name=first_name,
                last_name=last_name,
                series_mapping_id=series_name,
                club_name=club_name,
                players_data=players_data
            )
            
            if player_id:
                logger.info(f"Found match for {first_name} {last_name}: {player_id}")
                
                # Update the Railway database
                success = update_railway_user_player_id(user_id, player_id)
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
                    print(f"✅ Updated {first_name} {last_name} with player ID: {player_id}")
                else:
                    print(f"❌ Failed to update database for {first_name} {last_name}")
            else:
                logger.warning(f"No match found for {first_name} {last_name}")
                no_matches += 1
                no_match_users.append({
                    'user_id': user_id,
                    'email': email,
                    'name': f"{first_name} {last_name}",
                    'club': club_name,
                    'series': series_name
                })
                print(f"❌ No match found for {first_name} {last_name}")
                
        except Exception as e:
            logger.error(f"Error processing {first_name} {last_name}: {str(e)}")
            no_matches += 1
    
    return {
        'total_processed': total_processed,
        'successful_matches': successful_matches,
        'no_matches': no_matches,
        'updated_users': updated_users,
        'no_match_users': no_match_users
    }

def main():
    """Main function"""
    print("🚀 Railway Player ID Backfill Script")
    print("=" * 50)
    
    try:
        # Run the backfill
        results = backfill_railway_player_ids()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 BACKFILL SUMMARY")
        print("=" * 50)
        print(f"Total users processed: {results['total_processed']}")
        print(f"Successful matches: {results['successful_matches']}")
        print(f"No matches found: {results['no_matches']}")
        
        if results['updated_users']:
            print(f"\n✅ Successfully updated {len(results['updated_users'])} users:")
            for user in results['updated_users']:
                print(f"  • {user['name']} → {user['player_id']}")
        
        if results['no_match_users']:
            print(f"\n❌ Could not find matches for {len(results['no_match_users'])} users:")
            for user in results['no_match_users']:
                print(f"  • {user['name']} ({user['club']}, {user['series']})")
        
        print("\n🎉 Backfill completed!")
        
        return True
        
    except Exception as e:
        logger.error(f"Backfill failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
    else:
        sys.exit(0) 