#!/usr/bin/env python3
"""
Import Players with Upsert Logic

This script imports player data from JSON files using upsert logic (ON CONFLICT DO UPDATE).
It's designed to be incremental and idempotent - only updating players who have new data.

Usage:
    python3 data/etl/database_import/import_players.py [players_file]

This script:
1. Uses the database specified by RALLY_DATABASE environment variable (default: main)
2. Loads player data from JSON file
3. Imports players using upsert logic (ON CONFLICT DO UPDATE)
4. Provides detailed logging and statistics
"""

import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.insert(0, project_root)

# Convert project_root to Path object for proper path operations
project_root = Path(project_root)

from database_config import get_db
from utils.league_utils import normalize_league_id

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PlayersETL:
    """ETL class for importing players to database"""
    
    def __init__(self, players_file: str = None):
        # Define paths
        self.data_dir = project_root / "data" / "leagues" / "all"
        
        if players_file:
            self.players_file = Path(players_file)
        else:
            # Find the players file - try incremental first, then fallback to players.json
            players_files = list(self.data_dir.glob("players_incremental_*.json"))
            if players_files:
                # Sort by modification time and get the most recent
                players_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                self.players_file = players_files[0]
            else:
                # Fallback to players.json
                players_file_path = self.data_dir / "players.json"
                if players_file_path.exists():
                    self.players_file = players_file_path
                else:
                    raise FileNotFoundError(f"No players file found in {self.data_dir}")
        
        # Statistics
        self.stats = {
            'total_records': 0,
            'imported': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        logger.info("🔧 Players ETL initialized")
        logger.info(f"📁 Data directory: {self.data_dir}")
        logger.info(f"📄 Players file: {self.players_file}")
    
    def load_players_data(self) -> List[Dict]:
        """Load players data from JSON file"""
        if not self.players_file.exists():
            raise FileNotFoundError(f"Players file not found: {self.players_file}")
        
        logger.info(f"📖 Loading players data from {self.players_file}")
        
        try:
            with open(self.players_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                logger.warning("Data is not a list, wrapping in list")
                data = [data]
            
            self.stats['total_records'] = len(data)
            logger.info(f"✅ Loaded {len(data):,} player records")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error loading players data: {e}")
            raise
    
    def pre_cache_lookup_data(self, conn) -> tuple:
        """Pre-cache league, team, and club data for faster lookups"""
        cursor = conn.cursor()
        
        logger.info("🔧 Pre-caching lookup data...")
        
        # Cache league mappings
        cursor.execute("SELECT league_id, id FROM leagues")
        league_cache = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Cache team mappings (league_id, team_name) -> team_id
        cursor.execute("""
            SELECT l.league_id, t.team_name, t.id 
            FROM teams t 
            JOIN leagues l ON t.league_id = l.id
        """)
        team_cache = {(row[0], row[1]): row[2] for row in cursor.fetchall()}
        
        # Cache club mappings (club_name) -> club_id
        cursor.execute("SELECT name, id FROM clubs")
        club_cache = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Cache series mappings (league_id, series_name) -> series_id
        cursor.execute("""
            SELECT l.league_id, s.name, s.id 
            FROM series s 
            JOIN series_leagues sl ON s.id = sl.series_id
            JOIN leagues l ON sl.league_id = l.id
        """)
        series_cache = {(row[0], row[1]): row[2] for row in cursor.fetchall()}
        
        logger.info(f"✅ Cached {len(league_cache)} leagues, {len(team_cache)} teams, {len(club_cache)} clubs, {len(series_cache)} series")
        
        return league_cache, team_cache, club_cache, series_cache
    

    
    def process_player_record(self, record: Dict, league_cache: Dict, 
                            team_cache: Dict, club_cache: Dict, 
                            series_cache: Dict) -> Optional[tuple]:
        """Process a single player record and return data tuple for insertion"""
        try:
            # Extract data using the exact field names from the JSON format
            tenniscores_player_id = (record.get("Player ID") or "").strip()
            first_name = (record.get("First Name") or "").strip()
            last_name = (record.get("Last Name") or "").strip()
            team_name = (record.get("Series Mapping ID") or "").strip()
            club_name = (record.get("Club") or "").strip()
            raw_league_id = (record.get("League") or "").strip()
            series_name = (record.get("Series") or "").strip()
            pti_str = (record.get("PTI") or "").strip()
            
            # Validate required fields
            if not tenniscores_player_id or not first_name or not last_name:
                logger.warning(f"Skipping record with missing required fields: {record}")
                self.stats['skipped'] += 1
                return None
            
            # Normalize league ID
            league_id = normalize_league_id(raw_league_id) if raw_league_id else ""
            
            # Use cached lookups
            league_db_id = league_cache.get(league_id)
            if not league_db_id:
                logger.warning(f"League not found: {league_id}")
                self.stats['skipped'] += 1
                return None
            
            # Look up team ID
            team_id = None
            if team_name and league_id:
                team_id = team_cache.get((league_id, team_name))
                if not team_id:
                    logger.warning(f"Team not found: {team_name} in {league_id}")
            
            # Look up club ID - extract base club name from team-specific names
            club_id = None
            if club_name:
                # Try exact match first
                club_id = club_cache.get(club_name)
                
                # If not found, try to extract base club name (remove numbers and common suffixes)
                if not club_id:
                    import re
                    # Try multiple patterns to extract base club name
                    base_club_name = club_name
                    
                    # Pattern 1: Remove numbers and everything after (e.g., "Lake Shore CC 11" -> "Lake Shore CC")
                    base_club_name = re.sub(r'\s+\d+.*$', '', base_club_name)
                    
                    # Pattern 2: Handle special cases like "LifeSport-Lshire" -> "LifeSport"
                    if base_club_name.startswith('LifeSport-'):
                        base_club_name = 'LifeSport'
                    
                    # Pattern 3: Handle "Park RIdge CC" -> "Park Ridge CC" (fix typo)
                    if base_club_name == 'Park RIdge CC':
                        base_club_name = 'Park Ridge CC'
                    
                    base_club_name = base_club_name.strip()
                    
                    if base_club_name != club_name:
                        club_id = club_cache.get(base_club_name)
                        if club_id:
                            logger.debug(f"Mapped club '{club_name}' to '{base_club_name}'")
                
                if not club_id:
                    logger.warning(f"Club not found: {club_name}")
            
            # Look up series ID
            series_id = None
            if series_name and league_id:
                series_id = series_cache.get((league_id, series_name))
                if not series_id:
                    logger.warning(f"Series not found: {series_name} in {league_id}")
            
            # Validate PTI
            current_pti = None
            if pti_str and pti_str != "N/A":
                try:
                    current_pti = float(pti_str)
                except (ValueError, TypeError):
                    current_pti = None
            
            return (
                tenniscores_player_id, first_name, last_name, team_id, 
                league_db_id, club_id, series_id, current_pti
            )
            
        except Exception as e:
            logger.error(f"❌ Error processing player record: {e}")
            self.stats['errors'] += 1
            return None
    
    def process_batch(self, cursor, batch_data: List[tuple]) -> int:
        """Process a batch of player records using upsert logic"""
        if not batch_data:
            return 0
        
        try:
            # Use executemany for better performance with upsert
            cursor.executemany(
                """
                INSERT INTO players (
                    tenniscores_player_id, first_name, last_name, team_id,
                    league_id, club_id, series_id, pti, is_active, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true, CURRENT_TIMESTAMP)
                ON CONFLICT (tenniscores_player_id, league_id, club_id, series_id) DO UPDATE SET
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    team_id = EXCLUDED.team_id,
                    pti = EXCLUDED.pti,
                    updated_at = CURRENT_TIMESTAMP
                """,
                batch_data
            )
            
            return len(batch_data)
            
        except Exception as e:
            logger.error(f"❌ Batch insert failed: {e}")
            self.stats['errors'] += len(batch_data)
            return 0
    
    def import_players(self, players_data: List[Dict]):
        """Import players to the database"""
        logger.info("🚀 Starting players import...")
        
        try:
            with get_db() as conn:
                # Pre-cache lookup data
                league_cache, team_cache, club_cache, series_cache = self.pre_cache_lookup_data(conn)
                
                # Process records in batches
                batch_size = 100
                batch_data = []
                
                for record_idx, record in enumerate(players_data):
                    # Process the record
                    processed_data = self.process_player_record(
                        record, league_cache, team_cache, club_cache, series_cache
                    )
                    
                    if processed_data:
                        batch_data.append(processed_data)
                    
                    # Process batch when it reaches batch_size or at the end
                    if len(batch_data) >= batch_size or record_idx == len(players_data) - 1:
                        with conn.cursor() as cursor:
                            imported_count = self.process_batch(cursor, batch_data)
                            self.stats['imported'] += imported_count
                        
                        # Commit after each batch
                        conn.commit()
                        batch_data = []
                        
                        # Log progress
                        if self.stats['imported'] % 500 == 0:
                            logger.info(f"📊 Imported {self.stats['imported']:,} player records so far...")
                
                # Final commit
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ Error during import: {e}")
            raise
    
    def print_summary(self):
        """Print import summary"""
        logger.info("=" * 60)
        logger.info("📊 PLAYERS IMPORT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"📄 Total records processed: {self.stats['total_records']:,}")
        logger.info(f"✅ Successfully imported: {self.stats['imported']:,}")
        logger.info(f"❌ Errors: {self.stats['errors']}")
        logger.info(f"⏭️ Skipped: {self.stats['skipped']}")
        
        # Ensure we're working with integers for the calculation
        errors = int(self.stats['errors'])
        total_records = int(self.stats['total_records'])
        
        if errors > 0 and total_records > 0:
            error_rate = (errors / total_records) * 100
            logger.info(f"⚠️ Error rate: {error_rate:.2f}%")
        else:
            logger.info("🎉 100% success rate!")
        
        logger.info("=" * 60)
    
    def run(self):
        """Run the complete ETL process"""
        logger.info("🚀 Starting Players ETL...")
        
        try:
            # Load players data
            players_data = self.load_players_data()
            
            # Import players
            self.import_players(players_data)
            
            # Print summary
            self.print_summary()
            
            logger.info("✅ Players ETL completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Players ETL failed: {e}")
            raise


def main():
    """Main function"""
    logger.info("🎯 Players ETL Script")
    logger.info("=" * 50)
    
    # Get players file from command line argument
    players_file = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        etl = PlayersETL(players_file)
        etl.run()
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 