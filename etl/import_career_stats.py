#!/usr/bin/env python3
"""
ETL Script: Import Career Stats from Player History JSON

This script imports career wins/losses statistics from player_history.json
into the players table career stats columns.

Usage:
    python etl/import_career_stats.py [--file path/to/player_history.json] [--dry-run]
"""

import json
import os
import sys
import psycopg2
import argparse
from datetime import datetime
from psycopg2.extras import RealDictCursor

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database_config import get_db_url

def get_db_connection():
    """Get database connection"""
    try:
        DATABASE_URL = get_db_url()
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        sys.exit(1)

def import_career_stats(json_file_path, dry_run=False):
    """Import career stats from player_history.json into players table"""
    
    print(f"🏓 Starting career stats import from: {json_file_path}")
    print(f"   Dry run: {'Yes' if dry_run else 'No'}")
    
    # Load JSON data
    try:
        with open(json_file_path, 'r') as f:
            players_data = json.load(f)
        print(f"📄 Loaded {len(players_data)} player records")
    except Exception as e:
        print(f"❌ Error loading JSON file: {e}")
        return False
    
    if dry_run:
        print("🔍 DRY RUN MODE - Analyzing career stats data")
        
        # Analyze the data
        total_players = len(players_data)
        players_with_stats = 0
        total_career_matches = 0
        players_with_significant_career = 0
        
        for player_data in players_data:
            career_wins = player_data.get('wins', 0)
            career_losses = player_data.get('losses', 0)
            career_matches = career_wins + career_losses
            
            if career_matches > 0:
                players_with_stats += 1
                total_career_matches += career_matches
                
                if career_matches >= 20:  # Significant career activity
                    players_with_significant_career += 1
        
        print(f"📊 Analysis:")
        print(f"   - Total players in JSON: {total_players}")
        print(f"   - Players with career stats: {players_with_stats}")
        print(f"   - Players with significant career (20+ matches): {players_with_significant_career}")
        print(f"   - Total career matches across all players: {total_career_matches:,}")
        if players_with_stats > 0:
            print(f"   - Average career matches per active player: {total_career_matches/players_with_stats:.1f}")
        return True
    
    # Database import
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        print("🔄 Starting career stats import...")
        
        # Track statistics
        updated_count = 0
        not_found_count = 0
        skipped_no_stats = 0
        skipped_no_id = 0
        
        # Process each player record
        for i, player_data in enumerate(players_data, 1):
            if i % 500 == 0:
                print(f"   Processed {i}/{len(players_data)} records...")
            
            # Extract career stats from JSON
            player_name = player_data.get('name', '')
            career_wins = player_data.get('wins', 0)
            career_losses = player_data.get('losses', 0)
            tenniscores_id = player_data.get('player_id', '')
            
            if not tenniscores_id:
                skipped_no_id += 1
                continue
            
            # Skip players with no career activity
            career_matches = career_wins + career_losses
            if career_matches == 0:
                skipped_no_stats += 1
                continue
            
            # Calculate derived stats
            career_win_percentage = round((career_wins / career_matches) * 100, 2) if career_matches > 0 else 0.00
            
            # Find the player in the database
            cursor.execute(
                "SELECT id, first_name, last_name FROM players WHERE tenniscores_player_id = %s",
                (tenniscores_id,)
            )
            player_record = cursor.fetchone()
            
            if not player_record:
                not_found_count += 1
                continue
            
            # Update career stats
            cursor.execute(
                """
                UPDATE players 
                SET 
                    career_wins = %s,
                    career_losses = %s, 
                    career_matches = %s,
                    career_win_percentage = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE tenniscores_player_id = %s
                """,
                (career_wins, career_losses, career_matches, career_win_percentage, tenniscores_id)
            )
            
            updated_count += 1
            
            # Log progress for significant players (during verbose runs)
            if career_matches >= 50:
                db_name = f"{player_record['first_name']} {player_record['last_name']}"
                print(f"   📊 Updated {db_name}: {career_wins}W-{career_losses}L ({career_win_percentage}%)")
        
        # Commit transaction
        conn.commit()
        
        # Print results
        print(f"✅ Career stats import completed successfully!")
        print(f"📊 Results:")
        print(f"   - Players updated: {updated_count}")
        print(f"   - Players not found in DB: {not_found_count}")
        print(f"   - Players skipped (no player_id): {skipped_no_id}")
        print(f"   - Players skipped (no career stats): {skipped_no_stats}")
        print(f"   - Total records processed: {len(players_data)}")
        
        # Show some sample results
        print(f"\n📈 Sample updated career stats:")
        cursor.execute(
            """
            SELECT first_name, last_name, career_wins, career_losses, career_win_percentage
            FROM players 
            WHERE career_matches > 0 
            ORDER BY career_matches DESC 
            LIMIT 5
            """
        )
        
        sample_players = cursor.fetchall()
        for player in sample_players:
            print(f"   {player['first_name']} {player['last_name']}: {player['career_wins']}W-{player['career_losses']}L ({player['career_win_percentage']}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during career stats import: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
        
    finally:
        cursor.close()
        conn.close()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Import career stats from player_history.json")
    parser.add_argument(
        '--file', 
        default='data/leagues/all/player_history.json',
        help='Path to player_history JSON file (default: data/leagues/all/player_history.json)'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Analyze data without making database changes'
    )
    
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.file):
        print(f"❌ File not found: {args.file}")
        print(f"   Looking for: {os.path.abspath(args.file)}")
        
        # Try alternative paths
        alternative_paths = [
            'data/player_history.json',
            'data/leagues/APTA/player_history.json'
        ]
        
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                print(f"   ✅ Found alternative: {alt_path}")
                args.file = alt_path
                break
        else:
            print(f"   ❌ No alternative files found")
            sys.exit(1)
    
    # Run import
    success = import_career_stats(args.file, args.dry_run)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 