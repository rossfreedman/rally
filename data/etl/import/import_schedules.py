#!/usr/bin/env python3
"""
Import Schedules with Upsert Logic

This script imports schedule data from JSON files using upsert logic (ON CONFLICT DO UPDATE).
It's designed to be incremental and idempotent - only updating schedules that have new data.

Usage:
    python3 data/etl/import/import_schedules.py <LEAGUE_KEY>

This script:
1. Uses the database specified by RALLY_DATABASE environment variable (default: main)
2. Loads schedule data from data/leagues/<LEAGUE_KEY>/schedules.json
3. Imports schedules using upsert logic (ON CONFLICT DO UPDATE)
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

from database_config import get_db, get_db_url, get_database_mode, is_local_development
from utils.league_utils import normalize_league_id

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SchedulesETL:
    """ETL class for importing schedules to database"""
    
    def __init__(self, league_key: str):
        # Define paths - use league-specific directory
        self.league_key = league_key
        self.data_dir = project_root / "data" / "leagues" / league_key
        self.schedules_file = self.data_dir / "schedules.json"
        
        # Statistics
        self.stats = {
            'total_records': 0,
            'imported': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        # Show environment information
        logger.info("🔧 Schedules ETL initialized")
        logger.info(f"📁 Data directory: {self.data_dir}")
        logger.info(f"📄 Schedules file: {self.schedules_file}")
        logger.info(f"🏆 League: {league_key}")
        logger.info(f"🌍 Environment: {'Local Development' if is_local_development() else 'Railway/Production'}")
        logger.info(f"🗄️ Database Mode: {get_database_mode()}")
        logger.info(f"🔗 Database URL: {get_db_url()}")
        logger.info("")
    
    def load_schedules_data(self) -> List[Dict]:
        """Load schedules data from JSON file"""
        if not self.schedules_file.exists():
            raise FileNotFoundError(f"Schedules file not found: {self.schedules_file}")
        
        logger.info(f"📖 Loading schedules data from {self.schedules_file}")
        
        try:
            with open(self.schedules_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                logger.warning("Data is not a list, wrapping in list")
                data = [data]
            
            self.stats['total_records'] = len(data)
            logger.info(f"✅ Loaded {len(data):,} schedule records")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error loading schedules data: {e}")
            raise
    
    def pre_cache_lookup_data(self, conn) -> tuple:
        """Pre-cache league and team data for faster lookups"""
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
        
        logger.info(f"✅ Cached {len(league_cache)} leagues, {len(team_cache)} teams")
        
        return league_cache, team_cache
    
    def normalize_team_name_for_matching(self, team_name: str) -> str:
        """Normalize team name by removing ' - Series X' suffix for matching"""
        if " - Series " in team_name:
            return team_name.split(" - Series ")[0]
        return team_name
    
    def find_team_in_database(self, team_name: str, league_id: str, team_cache: Dict) -> Optional[int]:
        """Enhanced team lookup that tries multiple matching strategies"""
        # Strategy 1: Exact match
        team_id = team_cache.get((league_id, team_name))
        if team_id:
            return team_id
        
        # Strategy 2: Remove " - Series X" suffix
        normalized_name = self.normalize_team_name_for_matching(team_name)
        team_id = team_cache.get((league_id, normalized_name))
        if team_id:
            return team_id
        
        # Strategy 3: Try to match by removing series number suffix (e.g., "Team Name 1" -> "Team Name")
        # This handles database format like "Hinsdale PC 1b 1" vs schedule format "Hinsdale PC 1b"
        if team_name and team_name[-1].isdigit():
            # Remove trailing number
            base_name = team_name.rstrip('0123456789').rstrip()
            team_id = team_cache.get((league_id, base_name))
            if team_id:
                return team_id
        
        # Strategy 4: Try to match by removing series number suffix from database names
        # Look for database teams that start with the schedule team name
        for (cache_league, cache_team), cache_team_id in team_cache.items():
            if cache_league == league_id and cache_team.startswith(team_name + ' '):
                return cache_team_id
        
        # Strategy 5: Handle Series SN naming variations
        if "SN - Series SN" in team_name:
            # Convert "Michigan Shores SN - Series SN" to "Michigan Shores - Series SN"
            base_name = team_name.replace(" SN - Series SN", " - Series SN")
            team_id = team_cache.get((league_id, base_name))
            if team_id:
                return team_id
        
        # Strategy 6: Handle Series SN with parentheses variations
        if "SN (" in team_name and " - Series SN" in team_name:
            # Convert "Prarie Club SN (1) - Series SN" to "Prarie Club - Series SN"
            base_name = team_name.split("SN (")[0].rstrip() + " - Series SN"
            team_id = team_cache.get((league_id, base_name))
            if team_id:
                return team_id
        
        return None
    
    def process_schedule_record(self, record: Dict, league_cache: Dict, 
                              team_cache: Dict) -> Optional[tuple]:
        """Process a single schedule record and return data tuple for insertion"""
        try:
            # Extract data using the exact field names from the JSON format
            date_str = (record.get("date") or "").strip()
            time_str = (record.get("time") or "").strip()
            home_team = (record.get("home_team") or "").strip()
            away_team = (record.get("away_team") or "").strip()
            location = (record.get("location") or "").strip()
            raw_league_id = (record.get("League") or "").strip()
            
            # Validate required fields
            if not date_str or not home_team or not away_team:
                logger.warning(f"Skipping record with missing required fields: {record}")
                self.stats['skipped'] += 1
                return None
            
            # Parse date
            match_date = None
            if date_str:
                try:
                    match_date = datetime.strptime(date_str, "%m/%d/%Y").date()
                except ValueError:
                    try:
                        match_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    except ValueError:
                        logger.warning(f"Invalid date format: {date_str}")
                        self.stats['skipped'] += 1
                        return None
            
            # Handle empty time fields - convert to None for PostgreSQL TIME column
            match_time = None
            if time_str:
                match_time = time_str
            
            # Normalize league ID
            league_id = normalize_league_id(raw_league_id) if raw_league_id else ""
            
            # Use cached lookups
            league_db_id = league_cache.get(league_id)
            if not league_db_id:
                logger.warning(f"League not found: {league_id}")
                self.stats['skipped'] += 1
                return None
            
            # Look up team IDs with enhanced matching
            home_team_id = None
            away_team_id = None
            
            if home_team and home_team != "BYE":
                home_team_id = self.find_team_in_database(home_team, league_id, team_cache)
                if not home_team_id:
                    logger.warning(f"Home team not found: {home_team} in {league_id}")
            
            if away_team and away_team != "BYE":
                away_team_id = self.find_team_in_database(away_team, league_id, team_cache)
                if not away_team_id:
                    logger.warning(f"Away team not found: {away_team} in {league_id}")
            
            return (
                match_date, match_time, home_team, away_team, 
                home_team_id, away_team_id, location, league_db_id
            )
            
        except Exception as e:
            logger.error(f"❌ Error processing schedule record: {e}")
            self.stats['errors'] += 1
            return None
    
    def ensure_unique_constraint(self, conn):
        """Ensure the unique constraint exists for upsert operations"""
        cursor = conn.cursor()
        
        try:
            # Check if unique constraint already exists
            cursor.execute("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'schedule' 
                AND constraint_type = 'UNIQUE'
                AND constraint_name = 'unique_schedule_match'
            """)
            
            if not cursor.fetchone():
                logger.info("🔧 Creating unique constraint for upsert operations...")
                cursor.execute("""
                    ALTER TABLE schedule 
                    ADD CONSTRAINT unique_schedule_match 
                    UNIQUE (match_date, home_team, away_team, league_id)
                """)
                logger.info("✅ Unique constraint created")
            else:
                logger.info("✅ Unique constraint already exists")
                
        except Exception as e:
            logger.warning(f"⚠️ Could not create unique constraint: {e}")
            logger.warning("⚠️ Upsert operations may not work correctly")
    
    def process_batch(self, cursor, batch_data: List[tuple]) -> int:
        """Process a batch of schedule records using upsert logic"""
        if not batch_data:
            return 0
        
        try:
            # Use executemany for better performance with upsert
            cursor.executemany(
                """
                INSERT INTO schedule (
                    match_date, match_time, home_team, away_team, 
                    home_team_id, away_team_id, location, league_id, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (match_date, home_team, away_team, league_id) DO UPDATE SET
                    match_time = EXCLUDED.match_time,
                    home_team_id = EXCLUDED.home_team_id,
                    away_team_id = EXCLUDED.away_team_id,
                    location = EXCLUDED.location
                """,
                batch_data
            )
            
            return len(batch_data)
            
        except Exception as e:
            logger.error(f"❌ Batch insert failed: {e}")
            self.stats['errors'] += len(batch_data)
            return 0
    
    def import_schedules(self, schedules_data: List[Dict]):
        """Import schedules to the database"""
        logger.info("🚀 Starting schedules import...")
        
        try:
            with get_db() as conn:
                # Ensure unique constraint exists
                self.ensure_unique_constraint(conn)
                
                # Pre-cache lookup data
                league_cache, team_cache = self.pre_cache_lookup_data(conn)
                
                # Process records in batches
                batch_size = 100
                batch_data = []
                
                for record_idx, record in enumerate(schedules_data):
                    # Process the record
                    processed_data = self.process_schedule_record(
                        record, league_cache, team_cache
                    )
                    
                    if processed_data:
                        batch_data.append(processed_data)
                    
                    # Process batch when it reaches batch_size or at the end
                    if len(batch_data) >= batch_size or record_idx == len(schedules_data) - 1:
                        with conn.cursor() as cursor:
                            imported_count = self.process_batch(cursor, batch_data)
                            self.stats['imported'] += imported_count
                        
                        # Commit after each batch
                        conn.commit()
                        batch_data = []
                        
                        # Log progress
                        if self.stats['imported'] % 500 == 0:
                            logger.info(f"📊 Imported {self.stats['imported']:,} schedule records so far...")
                
                # Final commit
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ Error during import: {e}")
            raise
    
    def print_summary(self):
        """Print import summary"""
        logger.info("=" * 60)
        logger.info("📊 SCHEDULES IMPORT SUMMARY")
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
        logger.info("🚀 Starting Schedules ETL...")
        
        try:
            # Load schedules data
            schedules_data = self.load_schedules_data()
            
            # Import schedules
            self.import_schedules(schedules_data)
            
            # Print summary
            self.print_summary()
            
            logger.info("✅ Schedules ETL completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Schedules ETL failed: {e}")
            raise


def main():
    """Main function"""
    logger.info("🎯 Schedules ETL Script")
    logger.info("=" * 50)
    
    # Get league key from command line argument
    if len(sys.argv) < 2:
        logger.error("Usage: python3 data/etl/import/import_schedules.py <LEAGUE_KEY>")
        sys.exit(1)
    
    league_key = sys.argv[1]
    
    try:
        etl = SchedulesETL(league_key)
        etl.run()
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 