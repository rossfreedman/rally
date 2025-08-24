#!/usr/bin/env python3
"""
Deduplicate CNSWPL players in staging database
"""

import os
import sys
from typing import Dict, List, Any
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_utils import execute_query, execute_update

def get_staging_connection():
    """Get staging database connection"""
    staging_url = os.getenv('DATABASE_PUBLIC_URL')
    if not staging_url:
        print("❌ DATABASE_PUBLIC_URL not set")
        return None
    
    # Set environment for staging
    os.environ['DATABASE_URL'] = staging_url
    print(f"✅ Connected to staging database")
    return True

def find_cnswpl_duplicates():
    """Find duplicate CNSWPL players by name"""
    query = """
    SELECT first_name, last_name, COUNT(*) as count,
           ARRAY_AGG(id) as player_ids,
           ARRAY_AGG(tenniscores_player_id) as tc_ids
    FROM players 
    WHERE league_id = 4932  -- CNSWPL league
    GROUP BY first_name, last_name 
    HAVING COUNT(*) > 1
    ORDER BY count DESC
    """
    
    duplicates = execute_query(query)
    print(f"🔍 Found {len(duplicates)} sets of duplicate names")
    
    return duplicates

def deduplicate_player_group(first_name: str, last_name: str, player_ids: List[int], tc_ids: List[str]):
    """Deduplicate a group of players with the same name"""
    print(f"\n🔧 Deduplicating {first_name} {last_name} ({len(player_ids)} records)")
    
    # Get detailed info for each player
    players_info = []
    for pid in player_ids:
        player = execute_query("""
            SELECT p.id, p.tenniscores_player_id, p.first_name, p.last_name,
                   p.wins, p.losses, p.created_at,
                   c.name as club_name, s.name as series_name
            FROM players p
            LEFT JOIN clubs c ON p.club_id = c.id
            LEFT JOIN series s ON p.series_id = s.id
            WHERE p.id = %s
        """, [pid])
        
        if player:
            players_info.append(player[0])
    
    if len(players_info) < 2:
        print("  ⚠️ Less than 2 records found, skipping")
        return
    
    # Display all records
    for i, player in enumerate(players_info):
        print(f"  Record {i+1}: {player['club_name']} {player['series_name']}")
        print(f"    ID: {player['id']}, TC_ID: {player['tenniscores_player_id']}")
        print(f"    Record: {player['wins']}W-{player['losses']}L")
        print(f"    Created: {player['created_at']}")
    
    # Strategy: Keep the record with the most match activity (wins + losses)
    # If tied, keep the most recently created one
    primary_player = max(players_info, key=lambda p: (
        p['wins'] + p['losses'],  # Most activity first
        p['created_at']           # Most recent if tied
    ))
    
    print(f"  ✅ Keeping: {primary_player['club_name']} {primary_player['series_name']} (ID: {primary_player['id']})")
    
    # Get other players to remove
    players_to_remove = [p for p in players_info if p['id'] != primary_player['id']]
    
    # Update any match_scores that reference the duplicate players
    for player in players_to_remove:
        print(f"  🔄 Updating match references for player ID {player['id']}")
        
        # Update match_scores to point to primary player
        execute_update("""
            UPDATE match_scores 
            SET home_player_1_id = %s 
            WHERE home_player_1_id = %s
        """, [primary_player['tenniscores_player_id'], player['tenniscores_player_id']])
        
        execute_update("""
            UPDATE match_scores 
            SET home_player_2_id = %s 
            WHERE home_player_2_id = %s
        """, [primary_player['tenniscores_player_id'], player['tenniscores_player_id']])
        
        execute_update("""
            UPDATE match_scores 
            SET away_player_1_id = %s 
            WHERE away_player_1_id = %s
        """, [primary_player['tenniscores_player_id'], player['tenniscores_player_id']])
        
        execute_update("""
            UPDATE match_scores 
            SET away_player_2_id = %s 
            WHERE away_player_2_id = %s
        """, [primary_player['tenniscores_player_id'], player['tenniscores_player_id']])
        
        # Sum up wins/losses into primary player
        total_wins = primary_player['wins'] + player['wins']
        total_losses = primary_player['losses'] + player['losses']
        
        execute_update("""
            UPDATE players 
            SET wins = %s, losses = %s
            WHERE id = %s
        """, [total_wins, total_losses, primary_player['id']])
        
        print(f"  🗑️ Deleting duplicate player ID {player['id']}")
        execute_update("DELETE FROM players WHERE id = %s", [player['id']])
    
    print(f"  ✅ Deduplication complete for {first_name} {last_name}")

def main():
    """Main deduplication process"""
    print("🚀 Starting CNSWPL Staging Deduplication")
    print("=" * 50)
    
    if not get_staging_connection():
        return False
    
    # Find duplicates
    duplicates = find_cnswpl_duplicates()
    
    if not duplicates:
        print("✅ No duplicates found!")
        return True
    
    print(f"\n📋 Processing {len(duplicates)} duplicate groups:")
    for dup in duplicates:
        print(f"  {dup['first_name']} {dup['last_name']}: {dup['count']} records")
    
    # Process each duplicate group
    for dup in duplicates:
        deduplicate_player_group(
            dup['first_name'], 
            dup['last_name'],
            dup['player_ids'],
            dup['tc_ids']
        )
    
    print("\n" + "=" * 50)
    print("🎉 STAGING DEDUPLICATION COMPLETE!")
    
    # Verify results
    final_duplicates = find_cnswpl_duplicates()
    print(f"📊 Remaining duplicates: {len(final_duplicates)}")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
