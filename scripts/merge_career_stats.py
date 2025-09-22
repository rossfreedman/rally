#!/usr/bin/env python3
"""
Merge career stats from player_history.json into players.json

This script:
1. Loads players.json and player_history.json
2. Matches players by Player ID
3. Adds career_wins, career_losses, and career_win_percentage fields
4. Updates the players.json file with the merged data
"""

import json
import os
from typing import Dict, List, Any

def load_json_file(file_path: str) -> List[Dict[str, Any]]:
    """Load JSON data from file"""
    print(f"📂 Loading {file_path}...")
    with open(file_path, 'r') as f:
        data = json.load(f)
    print(f"   ✅ Loaded {len(data):,} records")
    return data

def save_json_file(file_path: str, data: List[Dict[str, Any]]) -> None:
    """Save JSON data to file"""
    print(f"💾 Saving updated data to {file_path}...")
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"   ✅ Saved {len(data):,} records")

def calculate_win_percentage(wins: int, losses: int) -> float:
    """Calculate win percentage"""
    total_matches = wins + losses
    if total_matches == 0:
        return 0.0
    return (wins / total_matches) * 100

def merge_career_stats(players: List[Dict[str, Any]], history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge career stats from history into players data"""
    print("🔄 Merging career stats...")
    
    # Create lookup dictionary for history data
    history_lookup = {}
    for record in history:
        player_id = record.get('player_id')
        if player_id:
            history_lookup[player_id] = record
    
    print(f"   📊 Created lookup for {len(history_lookup):,} history records")
    
    # Track statistics
    matched_players = 0
    unmatched_players = 0
    total_career_wins = 0
    total_career_losses = 0
    
    # Update players with career stats
    for player in players:
        player_id = player.get('Player ID')
        
        if player_id in history_lookup:
            history_record = history_lookup[player_id]
            
            # Extract career stats
            career_wins = int(history_record.get('wins', 0))
            career_losses = int(history_record.get('losses', 0))
            career_win_percentage = calculate_win_percentage(career_wins, career_losses)
            
            # Add career stats to player record
            player['Career Wins'] = career_wins
            player['Career Losses'] = career_losses
            player['Career Win %'] = f"{career_win_percentage:.1f}%"
            
            matched_players += 1
            total_career_wins += career_wins
            total_career_losses += career_losses
            
        else:
            # No history found, set to 0
            player['Career Wins'] = 0
            player['Career Losses'] = 0
            player['Career Win %'] = "0.0%"
            unmatched_players += 1
    
    print(f"   ✅ Matched {matched_players:,} players with history")
    print(f"   ⚠️  {unmatched_players:,} players without history (set to 0)")
    print(f"   📈 Total career wins: {total_career_wins:,}")
    print(f"   📉 Total career losses: {total_career_losses:,}")
    
    return players

def main():
    print("🚀 MERGING CAREER STATS INTO PLAYERS DATA")
    print("=" * 60)
    
    # File paths
    players_file = "data/leagues/APTA_CHICAGO/players.json"
    history_file = "data/leagues/APTA_CHICAGO/player_history.json"
    
    # Check if files exist
    if not os.path.exists(players_file):
        print(f"❌ Error: {players_file} not found")
        return
    
    if not os.path.exists(history_file):
        print(f"❌ Error: {history_file} not found")
        return
    
    # Load data
    players_data = load_json_file(players_file)
    history_data = load_json_file(history_file)
    
    # Merge career stats
    updated_players = merge_career_stats(players_data, history_data)
    
    # Save updated data
    save_json_file(players_file, updated_players)
    
    print("\n🎉 MERGE COMPLETE!")
    print("=" * 60)
    print("✅ Career stats successfully merged into players.json")
    print("📊 New fields added:")
    print("   - Career Wins")
    print("   - Career Losses") 
    print("   - Career Win %")
    
    # Show sample of updated data
    print("\n📋 SAMPLE UPDATED RECORD:")
    if updated_players:
        sample = updated_players[0]
        print(f"   Player: {sample.get('First Name')} {sample.get('Last Name')}")
        print(f"   Player ID: {sample.get('Player ID')}")
        print(f"   Current Season: {sample.get('Wins')}W-{sample.get('Losses')}L ({sample.get('Win %')})")
        print(f"   Career: {sample.get('Career Wins')}W-{sample.get('Career Losses')}L ({sample.get('Career Win %')})")

if __name__ == "__main__":
    main()