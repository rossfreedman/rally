#!/usr/bin/env python3
"""
Script to fix all users' tenniscores_player_id in the database.
This script matches Rally users with their corresponding player records in player_history.json
and updates the database with the correct player IDs.
"""

import sys
import os
import json
from typing import Dict, List, Optional

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query

def normalize_name(name: str) -> str:
    """Normalize player name for consistent matching"""
    return name.replace(',', '').replace('  ', ' ').strip().lower()

def load_player_history() -> List[Dict]:
    """Load player history data from JSON file"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    player_history_path = os.path.join(project_root, 'data', 'leagues', 'APTA', 'player_history.json')
    
    print(f"📂 Loading player history from: {player_history_path}")
    
    try:
        with open(player_history_path, 'r') as f:
            players = json.load(f)
        print(f"✅ Loaded {len(players)} players from player history")
        return players
    except Exception as e:
        print(f"❌ Error loading player history: {str(e)}")
        return []

def find_player_by_name(players: List[Dict], first_name: str, last_name: str, club: str = None) -> Optional[Dict]:
    """Find a player in the player history by name and optionally club"""
    target_name = normalize_name(f"{first_name} {last_name}")
    
    # First try exact name match
    for player in players:
        if normalize_name(player.get('name', '')) == target_name:
            # If club is provided, prefer matching club
            if club and player.get('club'):
                if normalize_name(player.get('club', '')) == normalize_name(club):
                    return player
            else:
                return player
    
    # If no exact match found and club wasn't used, try again without club constraint
    if club:
        for player in players:
            if normalize_name(player.get('name', '')) == target_name:
                return player
    
    return None

def get_all_rally_users() -> List[Dict]:
    """Get all users from the Rally database"""
    try:
        users = execute_query("""
            SELECT u.id, u.first_name, u.last_name, u.email, u.tenniscores_player_id,
                   c.name as club_name, s.name as series_name
            FROM users u
            LEFT JOIN clubs c ON u.club_id = c.id
            LEFT JOIN series s ON u.series_id = s.id
            ORDER BY u.last_name, u.first_name
        """)
        print(f"📋 Found {len(users)} Rally users in database")
        return users
    except Exception as e:
        print(f"❌ Error getting Rally users: {str(e)}")
        return []

def update_user_player_id(user_id: int, player_id: str) -> bool:
    """Update a user's tenniscores_player_id in the database"""
    try:
        execute_query(
            "UPDATE users SET tenniscores_player_id = %(player_id)s WHERE id = %(user_id)s",
            {'player_id': player_id, 'user_id': user_id}
        )
        return True
    except Exception as e:
        print(f"❌ Error updating user {user_id}: {str(e)}")
        return False

def fix_all_player_ids():
    """Main function to fix all player IDs"""
    
    print("🔧 Starting bulk player ID fix for all Rally users...")
    print("=" * 60)
    
    # Load player history data
    players = load_player_history()
    if not players:
        print("❌ Cannot proceed without player history data")
        return False
    
    # Get all Rally users
    users = get_all_rally_users()
    if not users:
        print("❌ Cannot proceed without Rally users")
        return False
    
    # Statistics
    stats = {
        'total_users': len(users),
        'already_correct': 0,
        'updated': 0,
        'not_found': 0,
        'errors': 0
    }
    
    print(f"\n🔍 Processing {stats['total_users']} users...")
    print("-" * 60)
    
    for user in users:
        user_name = f"{user['first_name']} {user['last_name']}"
        current_player_id = user['tenniscores_player_id']
        club_name = user['club_name']
        
        print(f"\n👤 Processing: {user_name} ({user['email']})")
        print(f"   Club: {club_name}")
        print(f"   Current player_id: {current_player_id}")
        
        # Find matching player in player history
        matching_player = find_player_by_name(
            players, 
            user['first_name'], 
            user['last_name'], 
            club_name
        )
        
        if not matching_player:
            print(f"   ❌ No matching player found in player history")
            stats['not_found'] += 1
            continue
        
        correct_player_id = matching_player['player_id']
        player_club = matching_player.get('club', 'Unknown')
        
        print(f"   ✅ Found match: {matching_player['name']} (Club: {player_club})")
        print(f"   Correct player_id: {correct_player_id}")
        
        # Check if already correct
        if current_player_id == correct_player_id:
            print(f"   ✅ Player ID already correct")
            stats['already_correct'] += 1
            continue
        
        # Update the player ID
        if update_user_player_id(user['id'], correct_player_id):
            print(f"   ✅ Updated player_id: {current_player_id} → {correct_player_id}")
            stats['updated'] += 1
        else:
            print(f"   ❌ Failed to update player_id")
            stats['errors'] += 1
    
    # Print final statistics
    print("\n" + "=" * 60)
    print("📊 FINAL STATISTICS")
    print("=" * 60)
    print(f"Total users processed: {stats['total_users']}")
    print(f"Already correct: {stats['already_correct']}")
    print(f"Successfully updated: {stats['updated']}")
    print(f"Not found in player data: {stats['not_found']}")
    print(f"Errors: {stats['errors']}")
    
    success_rate = ((stats['already_correct'] + stats['updated']) / stats['total_users']) * 100
    print(f"\n🎯 Success rate: {success_rate:.1f}%")
    
    if stats['updated'] > 0:
        print(f"\n✅ Successfully updated {stats['updated']} users!")
        print("💡 Player analysis should now work for these users")
    
    if stats['not_found'] > 0:
        print(f"\n⚠️  {stats['not_found']} users could not be matched to player data")
        print("   These users may need manual review or may not be active players")
    
    return stats['errors'] == 0

if __name__ == "__main__":
    success = fix_all_player_ids()
    
    if success:
        print("\n🎉 Player ID fix completed successfully!")
    else:
        print("\n❌ Player ID fix completed with some errors. Check the output above.") 