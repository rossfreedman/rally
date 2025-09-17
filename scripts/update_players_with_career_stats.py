#!/usr/bin/env python3
"""
Update APTA_CHICAGO players.json with career stats from player_history.json
"""

import json
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def update_players_with_career_stats():
    """Update players.json with career stats from player_history.json."""
    print("🔄 Updating APTA_CHICAGO players.json with career stats")
    print("=" * 60)
    
    # File paths
    players_file = project_root / 'data' / 'leagues' / 'APTA_CHICAGO' / 'players.json'
    history_file = project_root / 'data' / 'leagues' / 'APTA_CHICAGO' / 'player_history.json'
    
    # Load players data
    print("📖 Loading players data...")
    with open(players_file, 'r') as f:
        players_data = json.load(f)
    print(f"   Loaded {len(players_data)} players")
    
    # Load player history data
    print("📖 Loading player history data...")
    with open(history_file, 'r') as f:
        history_data = json.load(f)
    print(f"   Loaded {len(history_data)} history records")
    
    # Create lookup dictionary for career stats by player_id
    print("🔍 Building career stats lookup...")
    career_stats = {}
    for record in history_data:
        player_id = record.get('player_id')
        if player_id:
            wins = record.get('wins', 0)
            losses = record.get('losses', 0)
            total_matches = wins + losses
            
            # Calculate win percentage
            if total_matches > 0:
                win_percentage = (wins / total_matches) * 100
                win_percentage_str = f"{win_percentage:.1f}%"
            else:
                win_percentage_str = "0.0%"
            
            career_stats[player_id] = {
                'Career Wins': str(wins),
                'Career Losses': str(losses),
                'Career Win %': win_percentage_str
            }
    
    print(f"   Built lookup for {len(career_stats)} players with career stats")
    
    # Update players with career stats
    print("🔄 Updating players with career stats...")
    updated_count = 0
    missing_count = 0
    
    for player in players_data:
        player_id = player.get('Player ID')
        if player_id and player_id in career_stats:
            # Add career stats to player record
            player['Career Wins'] = career_stats[player_id]['Career Wins']
            player['Career Losses'] = career_stats[player_id]['Career Losses']
            player['Career Win %'] = career_stats[player_id]['Career Win %']
            updated_count += 1
        else:
            # Set default values for players without career stats
            player['Career Wins'] = "0"
            player['Career Losses'] = "0"
            player['Career Win %'] = "0.0%"
            missing_count += 1
    
    print(f"   Updated {updated_count} players with career stats")
    print(f"   Set defaults for {missing_count} players without career stats")
    
    # Save updated players data
    print("💾 Saving updated players data...")
    with open(players_file, 'w') as f:
        json.dump(players_data, f, indent=2)
    
    print("✅ Successfully updated players.json with career stats!")
    
    # Show some sample updated records
    print("\n📊 Sample updated records:")
    for i, player in enumerate(players_data[:5]):
        print(f"   {i+1}. {player.get('First Name')} {player.get('Last Name')} - "
              f"Career: {player.get('Career Wins')}W-{player.get('Career Losses')}L "
              f"({player.get('Career Win %')})")
    
    # Show stats summary
    print(f"\n📈 Summary:")
    print(f"   Total players: {len(players_data)}")
    print(f"   Players with career stats: {updated_count}")
    print(f"   Players without career stats: {missing_count}")

if __name__ == "__main__":
    update_players_with_career_stats()
