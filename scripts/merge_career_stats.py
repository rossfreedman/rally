#!/usr/bin/env python3
"""
Merge career stats from player_history.json into players.json

This script:
1. Loads both players.json and player_history.json
2. Creates a lookup dictionary from player_history.json using player_id as key
3. Updates each player in players.json with Career Wins and Career Losses from history
4. Preserves existing Wins/Losses (current season) and adds Career Wins/Career Losses
5. Saves the updated players.json
"""

import json
import os
from datetime import datetime

def merge_career_stats():
    """Merge career stats from player_history.json into players.json"""
    
    # File paths
    players_file = 'data/leagues/APTA_CHICAGO/players.json'
    history_file = 'data/leagues/APTA_CHICAGO/player_history.json'
    backup_file = f'data/leagues/APTA_CHICAGO/players_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    print('=== MERGING CAREER STATS ===')
    print()
    
    # Load players.json
    print('Loading players.json...')
    with open(players_file, 'r') as f:
        players_data = json.load(f)
    print(f'Loaded {len(players_data)} players')
    
    # Load player_history.json
    print('Loading player_history.json...')
    with open(history_file, 'r') as f:
        history_data = json.load(f)
    print(f'Loaded {len(history_data)} history records')
    
    # Create lookup dictionary from history data
    print('Creating history lookup dictionary...')
    history_lookup = {}
    for record in history_data:
        player_id = record.get('player_id')
        if player_id:
            history_lookup[player_id] = {
                'wins': record.get('wins', 0),
                'losses': record.get('losses', 0)
            }
    
    print(f'Created lookup for {len(history_lookup)} players')
    
    # Update players with career stats
    print('Updating players with career stats...')
    updated_count = 0
    not_found_count = 0
    
    for player in players_data:
        player_id = player.get('Player ID')
        if player_id and player_id in history_lookup:
            # Get career stats from history
            career_wins = history_lookup[player_id]['wins']
            career_losses = history_lookup[player_id]['losses']
            
            # Add career stats to player record
            player['Career Wins'] = str(career_wins)
            player['Career Losses'] = str(career_losses)
            
            # Calculate career win percentage
            total_matches = career_wins + career_losses
            if total_matches > 0:
                win_percentage = (career_wins / total_matches) * 100
                player['Career Win %'] = f'{win_percentage:.1f}%'
            else:
                player['Career Win %'] = '0.0%'
            
            updated_count += 1
        else:
            # Player not found in history, set career stats to 0
            player['Career Wins'] = '0'
            player['Career Losses'] = '0'
            player['Career Win %'] = '0.0%'
            not_found_count += 1
    
    print(f'Updated {updated_count} players with career stats')
    print(f'Set {not_found_count} players to 0 career stats (not found in history)')
    
    # Create backup
    print(f'Creating backup: {backup_file}')
    with open(backup_file, 'w') as f:
        json.dump(players_data, f, indent=2)
    
    # Save updated players.json
    print('Saving updated players.json...')
    with open(players_file, 'w') as f:
        json.dump(players_data, f, indent=2)
    
    print('✅ Career stats merge completed successfully!')
    print(f'Backup saved to: {backup_file}')
    
    # Show some sample results
    print('\nSample updated players:')
    sample_count = 0
    for player in players_data:
        if player.get('Career Wins', '0') != '0' and sample_count < 5:
            first_name = player.get('First Name', '')
            last_name = player.get('Last Name', '')
            career_wins = player.get('Career Wins')
            career_losses = player.get('Career Losses')
            career_win_pct = player.get('Career Win %')
            print(f'  {first_name} {last_name}: {career_wins} wins, {career_losses} losses, {career_win_pct} win rate')
            sample_count += 1

if __name__ == '__main__':
    merge_career_stats()
