#!/usr/bin/env python3
"""
ETL Script: Import Players with Multi-League Support

This script imports player data from JSON files and creates proper multi-league associations.
It handles both the players table and the player_leagues join table.

Usage:
    python etl/import_players.py [--file path/to/players.json] [--dry-run]
"""

import json
import os
import sys
import psycopg2
import argparse
from datetime import datetime
from psycopg2.extras import RealDictCursor, execute_values

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

def get_or_create_league(cursor, league_id):
    """Get league database ID, creating if necessary"""
    cursor.execute(
        "SELECT id FROM leagues WHERE league_id = %s",
        (league_id,)
    )
    result = cursor.fetchone()
    
    if result:
        return result['id']
    
    # Create league if it doesn't exist
    cursor.execute(
        """
        INSERT INTO leagues (league_id, league_name, created_at)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (league_id, league_id, datetime.now())
    )
    return cursor.fetchone()['id']

def get_or_create_club(cursor, club_name):
    """Get club database ID, creating if necessary"""
    if not club_name or club_name.strip() == '':
        return None
        
    cursor.execute(
        "SELECT id FROM clubs WHERE name = %s",
        (club_name.strip(),)
    )
    result = cursor.fetchone()
    
    if result:
        return result['id']
    
    # Create club if it doesn't exist
    cursor.execute(
        """
        INSERT INTO clubs (name)
        VALUES (%s)
        RETURNING id
        """,
        (club_name.strip(),)
    )
    return cursor.fetchone()['id']

def get_or_create_series(cursor, series_name):
    """Get series database ID, creating if necessary"""
    if not series_name or series_name.strip() == '':
        return None
        
    cursor.execute(
        "SELECT id FROM series WHERE name = %s",
        (series_name.strip(),)
    )
    result = cursor.fetchone()
    
    if result:
        return result['id']
    
    # Create series if it doesn't exist
    cursor.execute(
        """
        INSERT INTO series (name)
        VALUES (%s)
        RETURNING id
        """,
        (series_name.strip(),)
    )
    return cursor.fetchone()['id']

def import_players(json_file_path, dry_run=False):
    """Import players from JSON file with multi-league support"""
    
    print(f"🏓 Starting player import from: {json_file_path}")
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
        print("🔍 DRY RUN MODE - No database changes will be made")
        unique_players = set()
        league_counts = {}
        
        for player in players_data:
            player_id = player.get('Player ID', '').strip()
            league_id = player.get('League', '').strip()
            
            if player_id:
                unique_players.add(player_id)
                league_counts[league_id] = league_counts.get(league_id, 0) + 1
        
        print(f"📊 Analysis:")
        print(f"   - Unique players: {len(unique_players)}")
        print(f"   - League distribution:")
        for league, count in sorted(league_counts.items()):
            print(f"     * {league}: {count} players")
        return True
    
    # Database import
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        print("🔄 Starting database import...")
        
        # Track statistics
        players_created = 0
        players_updated = 0
        league_associations_created = 0
        
        # Cache for foreign key lookups
        league_cache = {}
        club_cache = {}
        series_cache = {}
        
        # Process each player record
        for i, player in enumerate(players_data, 1):
            if i % 1000 == 0:
                print(f"   Processed {i}/{len(players_data)} records...")
            
            # Extract player data
            player_id = player.get('Player ID', '').strip()
            first_name = player.get('First Name', '').strip()
            last_name = player.get('Last Name', '').strip()
            league_id = player.get('League', '').strip()
            club_name = player.get('Club', '').strip()
            series_name = player.get('Series', '').strip()
            
            if not player_id:
                print(f"   ⚠️  Skipping record {i}: No Player ID")
                continue
            
            # Get foreign key IDs (with caching)
            if league_id not in league_cache:
                league_cache[league_id] = get_or_create_league(cursor, league_id)
            league_db_id = league_cache[league_id]
            
            club_db_id = None
            if club_name:
                if club_name not in club_cache:
                    club_cache[club_name] = get_or_create_club(cursor, club_name)
                club_db_id = club_cache[club_name]
            
            series_db_id = None
            if series_name:
                if series_name not in series_cache:
                    series_cache[series_name] = get_or_create_series(cursor, series_name)
                series_db_id = series_cache[series_name]
            
            # 1. Upsert player record
            cursor.execute(
                """
                INSERT INTO players (tenniscores_player_id, first_name, last_name, created_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (tenniscores_player_id) DO UPDATE
                SET first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name
                RETURNING (xmax = 0) AS created
                """,
                (player_id, first_name, last_name, datetime.now())
            )
            result = cursor.fetchone()
            if result['created']:
                players_created += 1
            else:
                players_updated += 1
            
            # Get the player's database ID
            cursor.execute(
                "SELECT id FROM players WHERE tenniscores_player_id = %s",
                (player_id,)
            )
            player_db_id = cursor.fetchone()['id']
            
            # 2. Upsert league association
            cursor.execute(
                """
                INSERT INTO player_leagues 
                (player_id, league_id, tenniscores_player_id, club_id, series_id, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (player_id, league_id, series_id) DO UPDATE
                SET club_id = EXCLUDED.club_id,
                    tenniscores_player_id = EXCLUDED.tenniscores_player_id,
                    is_active = EXCLUDED.is_active,
                    updated_at = EXCLUDED.updated_at
                RETURNING (xmax = 0) AS created
                """,
                (player_db_id, league_db_id, player_id, club_db_id, series_db_id, True, datetime.now(), datetime.now())
            )
            result = cursor.fetchone()
            if result['created']:
                league_associations_created += 1
        
        # Commit transaction
        conn.commit()
        
        # Print results
        print(f"✅ Import completed successfully!")
        print(f"📊 Results:")
        print(f"   - Players created: {players_created}")
        print(f"   - Players updated: {players_updated}")
        print(f"   - League associations created: {league_associations_created}")
        print(f"   - Total records processed: {len(players_data)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during import: {e}")
        conn.rollback()
        return False
        
    finally:
        cursor.close()
        conn.close()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Import players with multi-league support")
    parser.add_argument(
        '--file', 
        default='data/leagues/all/players.json',
        help='Path to players JSON file (default: data/leagues/all/players.json)'
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
        sys.exit(1)
    
    # Run import
    success = import_players(args.file, args.dry_run)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 