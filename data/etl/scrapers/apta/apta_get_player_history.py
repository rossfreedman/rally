#!/usr/bin/env python3
"""
APTA Player History Import Script

This script imports missing player history records from player_history.json
into the database for players who have match scores but are missing their
historical PTI data.

Usage:
    python3 apta_get_player_history.py [--player "Pete Wahlstrom"] [--dry-run] [--all]
    
Arguments:
    --player: Import history for a specific player (e.g., "Pete Wahlstrom")
    --all: Import history for all players missing history data
    --dry-run: Show what would be imported without actually importing
"""

import sys
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import argparse

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
sys.path.insert(0, project_root)

from database_utils import execute_query, execute_query_one, execute_update


class PlayerHistoryImporter:
    """Import player history from JSON to database"""
    
    def __init__(self, json_path, dry_run=False):
        self.json_path = json_path
        self.dry_run = dry_run
        self.player_history_data = None
        self.stats = {
            'players_checked': 0,
            'players_found_in_json': 0,
            'history_records_imported': 0,
            'errors': []
        }
        
    def load_json_data(self):
        """Load player history from JSON file"""
        print(f"📂 Loading player history from {self.json_path}...")
        with open(self.json_path, 'r') as f:
            self.player_history_data = json.load(f)
        print(f"✅ Loaded {len(self.player_history_data)} player records from JSON")
        
        # Create lookup dictionary by name (lowercase for case-insensitive matching)
        self.player_lookup = {}
        for player in self.player_history_data:
            name_key = player['name'].lower()
            self.player_lookup[name_key] = player
        
    def get_missing_players(self):
        """Get list of players with matches but no history"""
        query = """
        SELECT DISTINCT 
          p.id as player_db_id,
          p.tenniscores_player_id,
          p.first_name,
          p.last_name,
          p.first_name || ' ' || p.last_name as full_name,
          s.name as series,
          c.name as club,
          l.id as league_db_id,
          COUNT(DISTINCT ms.id) as match_count
        FROM players p
        JOIN leagues l ON p.league_id = l.id
        LEFT JOIN series s ON p.series_id = s.id
        LEFT JOIN clubs c ON p.club_id = c.id
        LEFT JOIN player_history ph ON ph.player_id = p.id
        LEFT JOIN match_scores ms ON (
          ms.home_player_1_id = p.tenniscores_player_id OR 
          ms.home_player_2_id = p.tenniscores_player_id OR 
          ms.away_player_1_id = p.tenniscores_player_id OR 
          ms.away_player_2_id = p.tenniscores_player_id
        )
        WHERE l.league_id = 'APTA_CHICAGO' 
          AND ph.id IS NULL
          AND ms.id IS NOT NULL
        GROUP BY p.id, p.tenniscores_player_id, p.first_name, p.last_name, 
                 s.name, c.name, l.id
        ORDER BY p.last_name, p.first_name
        """
        
        return execute_query(query)
    
    def get_specific_player(self, player_name):
        """Get a specific player's database record"""
        name_parts = player_name.strip().split()
        if len(name_parts) < 2:
            print(f"❌ Invalid player name format: {player_name}")
            return None
            
        first_name = name_parts[0]
        last_name = " ".join(name_parts[1:])
        
        query = """
        SELECT 
          p.id as player_db_id,
          p.tenniscores_player_id,
          p.first_name,
          p.last_name,
          p.first_name || ' ' || p.last_name as full_name,
          s.name as series,
          c.name as club,
          l.id as league_db_id,
          (SELECT COUNT(*) FROM player_history ph WHERE ph.player_id = p.id) as history_count,
          (SELECT COUNT(*) FROM match_scores ms 
           WHERE ms.home_player_1_id = p.tenniscores_player_id 
              OR ms.home_player_2_id = p.tenniscores_player_id 
              OR ms.away_player_1_id = p.tenniscores_player_id 
              OR ms.away_player_2_id = p.tenniscores_player_id
          ) as match_count
        FROM players p
        JOIN leagues l ON p.league_id = l.id
        LEFT JOIN series s ON p.series_id = s.id
        LEFT JOIN clubs c ON p.club_id = c.id
        WHERE l.league_id = 'APTA_CHICAGO' 
          AND p.first_name = %s 
          AND p.last_name = %s
        """
        
        result = execute_query_one(query, [first_name, last_name])
        
        if result:
            print(f"\n📋 Found player in database:")
            print(f"   Name: {result['full_name']}")
            print(f"   Player ID: {result['tenniscores_player_id']}")
            print(f"   Series: {result['series']}")
            print(f"   Club: {result['club']}")
            print(f"   History in DB: {result['history_count']} records")
            print(f"   Matches in DB: {result['match_count']} matches")
            
        return result
    
    def import_player_history(self, player_record):
        """Import history for a single player"""
        self.stats['players_checked'] += 1
        
        full_name = player_record['full_name']
        player_db_id = player_record['player_db_id']
        league_db_id = player_record['league_db_id']
        
        # Look up player in JSON data
        json_data = self.player_lookup.get(full_name.lower())
        
        if not json_data:
            print(f"⚠️  {full_name}: Not found in JSON")
            return 0
        
        self.stats['players_found_in_json'] += 1
        matches = json_data.get('matches', [])
        
        if not matches:
            print(f"⚠️  {full_name}: No match history in JSON")
            return 0
        
        print(f"\n{'🔍 [DRY RUN]' if self.dry_run else '✅'} {full_name}: Found {len(matches)} history records in JSON")
        
        if self.dry_run:
            print(f"   Sample records:")
            for i, match in enumerate(matches[:3]):
                print(f"     {i+1}. {match['date']} - PTI: {match['end_pti']} ({match.get('series', 'N/A')})")
            print(f"   ... and {len(matches) - 3} more records")
            return len(matches)
        
        # Import each match history record
        imported_count = 0
        for match in matches:
            try:
                # Parse date (format: MM/DD/YYYY)
                match_date = datetime.strptime(match['date'], '%m/%d/%Y').date()
                end_pti = float(match['end_pti']) if match['end_pti'] else None
                series = match.get('series', '')
                
                # Insert into player_history table
                insert_query = """
                INSERT INTO player_history (player_id, league_id, series, date, end_pti, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT DO NOTHING
                """
                
                execute_update(
                    insert_query,
                    [player_db_id, league_db_id, series, match_date, end_pti]
                )
                
                imported_count += 1
                
            except Exception as e:
                error_msg = f"Error importing match for {full_name} on {match.get('date')}: {str(e)}"
                self.stats['errors'].append(error_msg)
                print(f"   ❌ {error_msg}")
                continue
        
        self.stats['history_records_imported'] += imported_count
        print(f"   ✅ Imported {imported_count} history records")
        
        return imported_count
    
    def import_all_missing_players(self):
        """Import history for all players missing data"""
        print("\n" + "=" * 80)
        print("IMPORTING PLAYER HISTORY FOR ALL MISSING PLAYERS")
        print("=" * 80)
        
        missing_players = self.get_missing_players()
        print(f"\n📊 Found {len(missing_players)} players with matches but no history\n")
        
        for i, player in enumerate(missing_players, 1):
            print(f"[{i}/{len(missing_players)}] Processing {player['full_name']}...")
            self.import_player_history(player)
            
            # Progress update every 50 players
            if i % 50 == 0:
                print(f"\n📈 Progress: {i}/{len(missing_players)} players processed")
                print(f"   - Found in JSON: {self.stats['players_found_in_json']}")
                print(f"   - Records imported: {self.stats['history_records_imported']}\n")
        
    def print_summary(self):
        """Print import summary"""
        print("\n" + "=" * 80)
        print("IMPORT SUMMARY")
        print("=" * 80)
        print(f"Players checked: {self.stats['players_checked']}")
        print(f"Players found in JSON: {self.stats['players_found_in_json']}")
        print(f"History records imported: {self.stats['history_records_imported']}")
        
        if self.stats['errors']:
            print(f"\n⚠️  Errors encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:10]:
                print(f"   - {error}")
            if len(self.stats['errors']) > 10:
                print(f"   ... and {len(self.stats['errors']) - 10} more errors")


def main():
    parser = argparse.ArgumentParser(
        description='Import missing APTA player history from JSON to database'
    )
    parser.add_argument(
        '--player',
        type=str,
        help='Import history for a specific player (e.g., "Pete Wahlstrom")'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Import history for all players missing data'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be imported without actually importing'
    )
    
    args = parser.parse_args()
    
    # Path to player history JSON
    json_path = os.path.join(
        os.path.dirname(__file__),
        '../../../leagues/APTA_CHICAGO/player_history.json'
    )
    
    if not os.path.exists(json_path):
        print(f"❌ Error: player_history.json not found at {json_path}")
        return 1
    
    # Initialize importer
    importer = PlayerHistoryImporter(json_path, dry_run=args.dry_run)
    importer.load_json_data()
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No data will be imported\n")
    
    # Import specific player or all missing players
    if args.player:
        player_record = importer.get_specific_player(args.player)
        if player_record:
            importer.import_player_history(player_record)
        else:
            print(f"❌ Player not found in database: {args.player}")
            return 1
    elif args.all:
        importer.import_all_missing_players()
    else:
        print("❌ Error: Must specify either --player or --all")
        parser.print_help()
        return 1
    
    # Print summary
    importer.print_summary()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

