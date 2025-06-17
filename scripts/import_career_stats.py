#!/usr/bin/env python3

"""
DEPRECATED: Import career stats from player_history.json into players table career stats columns

⚠️  DEPRECATION NOTICE:
This standalone script is now DEPRECATED as of 2025-06-16.
Career stats import is now integrated into the main ETL script:
    python etl/database_import/json_import_all_to_database.py

This script is kept for backward compatibility but should not be used.
Use the main ETL script instead, which imports career stats automatically.
"""

import os
import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'app'))

from database_utils import execute_update, execute_query_one

def import_career_stats():
    """
    DEPRECATED: Import career wins/losses from player_history.json into players table
    
    ⚠️  This function is deprecated. Career stats are now imported automatically
    by the main ETL script: etl/database_import/json_import_all_to_database.py
    """
    
    print("⚠️  DEPRECATION WARNING")
    print("=" * 60)
    print("This script is DEPRECATED as of 2025-06-16.")
    print("Career stats import is now integrated into the main ETL script.")
    print()
    print("Instead of running this script, use:")
    print("    python etl/database_import/json_import_all_to_database.py")
    print()
    print("The main ETL script now automatically imports career stats")
    print("as part of the complete data import process.")
    print("=" * 60)
    print()
    
    # Ask user if they want to continue
    response = input("Do you want to continue with this deprecated script? (y/N): ").lower().strip()
    if response not in ['y', 'yes']:
        print("✅ Recommended: Use the main ETL script instead.")
        print("   python etl/database_import/json_import_all_to_database.py")
        return
    
    print("\n🏓 IMPORTING CAREER STATS FROM JSON (DEPRECATED)")
    print("=" * 50)
    
    # Find the player_history.json file
    json_paths = [
        project_root / 'data' / 'leagues' / 'all' / 'player_history.json',
        project_root / 'data' / 'player_history.json'
    ]
    
    player_history_path = None
    for path in json_paths:
        if path.exists():
            player_history_path = path
            break
    
    if not player_history_path:
        print("❌ Could not find player_history.json file")
        return
    
    print(f"📁 Reading from: {player_history_path}")
    
    # Load the JSON data
    try:
        with open(player_history_path, 'r') as f:
            players_data = json.load(f)
        print(f"✅ Loaded {len(players_data)} players from JSON")
    except Exception as e:
        print(f"❌ Error reading JSON file: {e}")
        return
    
    # Process each player
    updated_count = 0
    not_found_count = 0
    
    for player_data in players_data:
        # Extract career stats from JSON
        player_name = player_data.get('name', '')
        career_wins = player_data.get('wins', 0)
        career_losses = player_data.get('losses', 0)
        tenniscores_id = player_data.get('player_id', '')
        
        if not tenniscores_id:
            print(f"⚠️  Skipping player {player_name} - no player_id")
            continue
        
        # Calculate derived stats
        career_matches = career_wins + career_losses
        career_win_percentage = round((career_wins / career_matches) * 100, 2) if career_matches > 0 else 0.00
        
        # Find the player in the database
        try:
            player_check = execute_query_one(
                "SELECT id, first_name, last_name FROM players WHERE tenniscores_player_id = %s",
                [tenniscores_id]
            )
            
            if not player_check:
                not_found_count += 1
                print(f"⚠️  Player not found in DB: {player_name} ({tenniscores_id})")
                continue
            
            # Update career stats
            update_query = """
                UPDATE players 
                SET 
                    career_wins = %s,
                    career_losses = %s, 
                    career_matches = %s,
                    career_win_percentage = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE tenniscores_player_id = %s
            """
            
            execute_update(update_query, [
                career_wins, career_losses, career_matches, 
                career_win_percentage, tenniscores_id
            ])
            
            updated_count += 1
            
            # Log progress for significant players
            if career_matches >= 20:
                db_name = f"{player_check['first_name']} {player_check['last_name']}"
                print(f"✅ Updated {db_name}: {career_wins}W-{career_losses}L ({career_win_percentage}%)")
                
        except Exception as e:
            print(f"❌ Error updating {player_name}: {e}")
            continue
    
    print("\n" + "=" * 50)
    print(f"🎉 IMPORT COMPLETE")
    print(f"   Updated: {updated_count} players")
    print(f"   Not found: {not_found_count} players")
    print(f"   Total processed: {len(players_data)} players")
    
    # Show some sample results
    print(f"\n📊 Sample career stats in database:")
    sample_query = """
        SELECT first_name, last_name, career_wins, career_losses, career_win_percentage
        FROM players 
        WHERE career_matches > 0 
        ORDER BY career_matches DESC 
        LIMIT 5
    """
    
    try:
        sample_players = execute_query_one(sample_query, fetch_all=True)
        for player in sample_players:
            print(f"   {player['first_name']} {player['last_name']}: {player['career_wins']}W-{player['career_losses']}L ({player['career_win_percentage']}%)")
    except:
        pass
    
    print("\n⚠️  REMINDER: Use the main ETL script for future imports:")
    print("   python etl/database_import/json_import_all_to_database.py")

if __name__ == "__main__":
    import_career_stats() 