#!/usr/bin/env python3
"""
Import Match Scores

This script imports match scores from the consolidated JSON files to the database
using upsert logic (ON CONFLICT DO UPDATE).

Usage:
    python3 data/etl/database_import/import_match_scores.py

This script:
1. Uses the database specified by RALLY_DATABASE environment variable (default: main)
2. Loads match_history.json from data/leagues/all/
3. Imports match scores using upsert logic (ON CONFLICT DO UPDATE)
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

class MatchScoresETL:
    """ETL class for importing match scores to database"""
    
    def __init__(self):
        # Define paths
        self.data_dir = project_root / "data" / "leagues" / "all"
        self.match_history_file = self.data_dir / "match_history.json"
        
        # Statistics
        self.stats = {
            'total_records': 0,
            'imported': 0,
            'updated': 0,
            'errors': 0,
            'winner_corrections': 0,
            'player_id_fixes': 0
        }
        
        logger.info("🔧 Match Scores ETL initialized")
        logger.info(f"📁 Data directory: {self.data_dir}")
        logger.info(f"📄 Match history file: {self.match_history_file}")
    
    def load_match_history(self) -> List[Dict]:
        """Load match history data from JSON file"""
        if not self.match_history_file.exists():
            raise FileNotFoundError(f"Match history file not found: {self.match_history_file}")
        
        logger.info(f"📖 Loading match history from {self.match_history_file}")
        
        try:
            with open(self.match_history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                logger.warning("Data is not a list, wrapping in list")
                data = [data]
            
            self.stats['total_records'] = len(data)
            logger.info(f"✅ Loaded {len(data):,} match records")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error loading match history: {e}")
            raise
    
    def validate_and_correct_winner(self, scores: str, winner: str, 
                                  home_team: str, away_team: str, 
                                  league_id: str = None) -> str:
        """Validate and correct winner field based on scores and teams"""
        if not winner or not scores:
            return winner
        
        winner_lower = winner.lower().strip()
        
        # Handle common variations
        if winner_lower in ['home', 'h', 'home team']:
            return 'home'
        elif winner_lower in ['away', 'a', 'away team']:
            return 'away'
        
        # Try to determine winner from scores if available
        if scores and (home_team != "BYE" and away_team != "BYE"):
            # Simple score parsing - look for patterns like "6-4, 6-2" or "7-5, 6-4"
            try:
                # Split by comma and look for set scores
                sets = scores.split(',')
                home_sets = 0
                away_sets = 0
                
                for set_score in sets:
                    set_score = set_score.strip()
                    if '-' in set_score:
                        # Parse "6-4" format
                        parts = set_score.split('-')
                        if len(parts) == 2:
                            try:
                                home_score = int(parts[0])
                                away_score = int(parts[1])
                                if home_score > away_score:
                                    home_sets += 1
                                elif away_score > home_score:
                                    away_sets += 1
                            except ValueError:
                                continue
                
                # Determine winner based on sets won
                if home_sets > away_sets:
                    return 'home'
                elif away_sets > home_sets:
                    return 'away'
                    
            except Exception:
                pass
        
        # If we can't determine, return None
        return None
    
    def pre_cache_lookup_data(self, conn) -> tuple:
        """Pre-cache league, team, and player data for faster lookups"""
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
        
        # Cache active player IDs for validation
        cursor.execute("SELECT tenniscores_player_id FROM players WHERE is_active = true")
        valid_player_ids = {row[0] for row in cursor.fetchall()}
        
        logger.info(f"✅ Cached {len(league_cache)} leagues, {len(team_cache)} teams, {len(valid_player_ids):,} players")
        
        return league_cache, team_cache, valid_player_ids
    
    def process_match_record(self, record: Dict, league_cache: Dict, 
                           team_cache: Dict, valid_player_ids: set) -> Optional[tuple]:
        """Process a single match record and return data tuple for insertion"""
        try:
            # Extract data using the actual field names from the JSON
            match_date_str = (record.get("Date") or "").strip()
            home_team = (record.get("Home Team") or "").strip()
            away_team = (record.get("Away Team") or "").strip()
            scores = record.get("Scores") or ""
            winner = (record.get("Winner") or "").strip()
            raw_league_id = (record.get("league_id") or "").strip()
            league_id = normalize_league_id(raw_league_id) if raw_league_id else ""

            # Extract and validate player IDs
            home_player_1_id = (record.get("Home Player 1 ID") or "").strip()
            home_player_2_id = (record.get("Home Player 2 ID") or "").strip()
            away_player_1_id = (record.get("Away Player 1 ID") or "").strip()
            away_player_2_id = (record.get("Away Player 2 ID") or "").strip()
            
            # Quick validation using cached player IDs
            player_ids = [home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id]
            validated_ids = []
            
            for pid in player_ids:
                if pid and pid in valid_player_ids:
                    validated_ids.append(pid)
                else:
                    validated_ids.append(None)
                    if pid:
                        self.stats['player_id_fixes'] += 1

            home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id = validated_ids

            # Parse date
            match_date = None
            if match_date_str:
                try:
                    # Try DD-Mon-YY format first
                    match_date = datetime.strptime(match_date_str, "%d-%b-%y").date()
                except ValueError:
                    try:
                        match_date = datetime.strptime(match_date_str, "%m/%d/%Y").date()
                    except ValueError:
                        try:
                            match_date = datetime.strptime(match_date_str, "%Y-%m-%d").date()
                        except ValueError:
                            pass

            if not all([match_date, home_team, away_team]):
                return None

            # Validate winner
            original_winner = winner
            winner = self.validate_and_correct_winner(scores, winner, home_team, away_team, league_id)
            if winner != original_winner:
                self.stats['winner_corrections'] += 1

            # Validate winner field - only allow 'home', 'away', or None
            if winner and winner.lower() not in ["home", "away"]:
                winner = None

            # Generate unique tenniscores_match_id
            base_match_id = record.get("match_id", "").strip()
            line = record.get("Line", "").strip()
            
            # Use the match_id directly if it already contains the line information
            # The JSON data already has the correct format like "nndz-WWlHNnc3djZnQT09_Line4"
            if base_match_id:
                tenniscores_match_id = base_match_id
            else:
                # Fallback: construct from base and line if match_id is missing
                if line:
                    line_number = line.replace(" ", "")  # "Line 1" -> "Line1"
                    tenniscores_match_id = f"unknown_{line_number}"
                else:
                    tenniscores_match_id = "unknown"

            # Use cached lookups
            league_db_id = league_cache.get(league_id)
            home_team_id = team_cache.get((league_id, home_team)) if home_team != "BYE" else None
            away_team_id = team_cache.get((league_id, away_team)) if away_team != "BYE" else None

            return (
                match_date, home_team, away_team, home_team_id, away_team_id,
                home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id,
                str(scores), winner, league_db_id, tenniscores_match_id
            )
            
        except Exception as e:
            logger.error(f"❌ Error processing match record: {e}")
            self.stats['errors'] += 1
            return None
    
    def process_batch(self, cursor, batch_data: List[tuple]) -> int:
        """Process a batch of match records using upsert logic"""
        if not batch_data:
            return 0
        
        try:
            # Use executemany for better performance with upsert
            cursor.executemany(
                """
                INSERT INTO match_scores (
                    match_date, home_team, away_team, home_team_id, away_team_id,
                    home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id, 
                    scores, winner, league_id, tenniscores_match_id, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (tenniscores_match_id) WHERE tenniscores_match_id IS NOT NULL DO UPDATE
                SET
                    match_date = EXCLUDED.match_date,
                    home_team = EXCLUDED.home_team,
                    away_team = EXCLUDED.away_team,
                    home_team_id = EXCLUDED.home_team_id,
                    away_team_id = EXCLUDED.away_team_id,
                    home_player_1_id = EXCLUDED.home_player_1_id,
                    home_player_2_id = EXCLUDED.home_player_2_id,
                    away_player_1_id = EXCLUDED.away_player_1_id,
                    away_player_2_id = EXCLUDED.away_player_2_id,
                    scores = EXCLUDED.scores,
                    winner = EXCLUDED.winner,
                    league_id = EXCLUDED.league_id
                """,
                batch_data
            )
            
            return len(batch_data)
            
        except Exception as e:
            logger.error(f"❌ Batch insert failed: {e}")
            self.stats['errors'] += len(batch_data)
            return 0
    
    def import_match_scores(self, match_history_data: List[Dict]):
        """Import match scores to the database"""
        logger.info("🚀 Starting match scores import...")
        
        try:
            with get_db() as conn:
                # Pre-cache lookup data
                league_cache, team_cache, valid_player_ids = self.pre_cache_lookup_data(conn)
                
                # Process records in batches
                batch_size = 500
                batch_data = []
                
                for record_idx, record in enumerate(match_history_data):
                    # Process the record
                    processed_data = self.process_match_record(record, league_cache, team_cache, valid_player_ids)
                    
                    if processed_data:
                        batch_data.append(processed_data)
                    
                    # Process batch when it reaches batch_size or at the end
                    if len(batch_data) >= batch_size or record_idx == len(match_history_data) - 1:
                        with conn.cursor() as cursor:
                            imported_count = self.process_batch(cursor, batch_data)
                            self.stats['imported'] += imported_count
                        
                        # Commit after each batch
                        conn.commit()
                        batch_data = []
                        
                        # Log progress
                        if self.stats['imported'] % 2000 == 0:
                            logger.info(f"📊 Imported {self.stats['imported']:,} match records so far...")
                
                # Final commit
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ Error during import: {e}")
            raise
    
    def print_summary(self):
        """Print import summary"""
        logger.info("=" * 60)
        logger.info("📊 MATCH SCORES IMPORT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"📄 Total records processed: {self.stats['total_records']:,}")
        logger.info(f"✅ Successfully imported: {self.stats['imported']:,}")
        logger.info(f"❌ Errors: {self.stats['errors']}")
        logger.info(f"🔧 Winner corrections: {self.stats['winner_corrections']}")
        logger.info(f"👤 Player ID fixes: {self.stats['player_id_fixes']}")
        
        # Ensure we're working with integers for the calculation
        errors = int(self.stats['errors'])
        total_records = int(self.stats['total_records'])
        
        if errors > 0 and total_records > 0:
            error_rate = (errors / total_records) * 100
            logger.info(f"⚠️  Error rate: {error_rate:.2f}%")
        else:
            logger.info("🎉 100% success rate!")
        
        logger.info("=" * 60)
    
    def run(self):
        """Run the complete ETL process"""
        logger.info("🚀 Starting Match Scores ETL...")
        
        try:
            # Load match history data
            match_history_data = self.load_match_history()
            
            # Import match scores
            self.import_match_scores(match_history_data)
            
            # Print summary
            self.print_summary()
            
            logger.info("✅ Match Scores ETL completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Match Scores ETL failed: {e}")
            raise

def main():
    """Main function"""
    logger.info("🎯 Match Scores ETL Script")
    logger.info("=" * 50)
    
    try:
        etl = MatchScoresETL()
        etl.run()
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 