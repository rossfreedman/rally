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
import re
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.insert(0, project_root)

# Convert project_root to Path object for proper path operations
project_root = Path(project_root)

from database_config import get_db, get_db_url, get_database_mode, is_local_development
from utils.league_utils import normalize_league_id

# Club normalization regex patterns
_ROMAN_RE = re.compile(r'\b[IVXLCDM]{1,4}\b', re.IGNORECASE)
_ALNUM_SUFFIX_RE = re.compile(r'\b(\d+[A-Za-z]?|[A-Za-z]?\d+)\b')
_LETTER_PAREN_RE = re.compile(r'\b[A-Za-z]{1,3}\(\d+\)\b')
_ALLCAP_SHORT_RE = re.compile(r'\b[A-Z]{1,3}\b')
_KEEP_SUFFIXES: Set[str] = {"CC", "GC", "RC", "PC", "TC", "AC"}  # preserve common club types

def _strip_trailing_suffix_tokens(tokens: list[str]) -> list[str]:
    """Strip trailing series/division/team markers without using hard-coded club maps."""
    while tokens:
        t = tokens[-1]

        # Preserve common club-type suffixes (e.g., 'Lake Shore CC')
        if t.upper() in _KEEP_SUFFIXES:
            break

        if _ROMAN_RE.fullmatch(t):
            tokens.pop()
            continue
        if _ALNUM_SUFFIX_RE.fullmatch(t):
            tokens.pop()
            continue
        if _LETTER_PAREN_RE.fullmatch(t):
            tokens.pop()
            continue
        # Generic short all-caps trailing marker (PD, H, B, F, etc.)
        if _ALLCAP_SHORT_RE.fullmatch(t):
            tokens.pop()
            continue
        break
    return tokens

def normalize_club_name(raw: str) -> str:
    """
    Normalize club names during season bootstrap so variants collapse to a single base club.
    
    Rules applied in order:
    1. Trim and normalize internal whitespace
    2. If name contains " - " segments, keep only the first segment
    3. Drop any trailing parenthetical segments: (... ) at the end
    4. Iteratively strip trailing team/series suffix tokens until none remain
    5. Remove stray punctuation other than & and spaces
    6. Collapse multiple spaces and strip ends
    7. Title-case the result (preserving club type abbreviations)
    """
    if not raw:
        return ""
    
    # Trim and normalize internal whitespace
    base = re.sub(r'\s+', ' ', raw.strip())
    
    # If the name contains " - " segments, keep only the first segment
    if " - " in base:
        base = base.split(" - ")[0].strip()
    
    # Drop any trailing parenthetical segments: (... ) at the end
    base = re.sub(r'\s*\([^)]*\)\s*$', '', base).strip()
    
    # Split into tokens for suffix stripping
    tokens = base.split()
    if not tokens:
        return ""
    
    # Iteratively strip trailing suffix tokens
    tokens = _strip_trailing_suffix_tokens(tokens)
    
    if not tokens:
        return ""
    
    # Remove stray punctuation from the remaining body (keep &)
    base = ' '.join(tokens)
    base = re.sub(r'[^\w\s&]', ' ', base)
    base = re.sub(r'\s+', ' ', base).strip()

    # Title case for display consistency, but preserve club type abbreviations
    words = base.split()
    title_words = []
    for word in words:
        if word.upper() in _KEEP_SUFFIXES:
            title_words.append(word.upper())
        else:
            title_words.append(word.title())
    base = ' '.join(title_words)

    return base

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
    
    def normalize_club_name(self, raw: str) -> str:
        """
        Normalize club names using consistent logic across all import scripts.
        
        Rules:
        1. Trim and normalize internal whitespace
        2. If name contains " - " segments, keep only the first segment
        3. Drop trailing parenthetical segments
        4. Strip trailing team/series suffix tokens
        5. Remove stray punctuation other than & and spaces
        6. Collapse multiple spaces and strip ends
        7. Title-case the result
        """
        if not raw:
            return ""
        
        # Step 1: Trim and normalize internal whitespace
        text = re.sub(r'\s+', ' ', raw.strip())
        
        # Step 2: If name contains " - " segments, keep only the first segment
        if " - " in text:
            text = text.split(" - ")[0]
        
        # Step 3: Drop trailing parenthetical segments
        text = re.sub(r'\s*\([^)]*\)\s*$', '', text)
        
        # Step 4: Strip trailing team/series suffix tokens
        tokens = text.split()
        tokens = self._strip_trailing_suffix_tokens(tokens)
        
        # Step 5: Remove stray punctuation other than & and spaces
        text = ' '.join(tokens)
        text = re.sub(r'[^\w\s&]', '', text)
        
        # Step 6: Collapse multiple spaces and strip ends
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Step 7: Title-case the result, preserving club type abbreviations
        if not text:
            return ""
        
        words = text.split()
        result_words = []
        for word in words:
            if word.upper() in _KEEP_SUFFIXES:
                result_words.append(word.upper())
            else:
                result_words.append(word.title())
        
        return ' '.join(result_words)
    
    def _strip_trailing_suffix_tokens(self, tokens: list[str]) -> list[str]:
        """Strip trailing series/division/team markers without using hard-coded club maps."""
        while tokens:
            t = tokens[-1]
            
            # Preserve common club-type suffixes (e.g., 'Lake Shore CC')
            if t.upper() in _KEEP_SUFFIXES:
                break
            
            if _ROMAN_RE.fullmatch(t):
                tokens.pop()
                continue
            if _ALNUM_SUFFIX_RE.fullmatch(t):
                tokens.pop()
                continue
            if _LETTER_PAREN_RE.fullmatch(t):
                tokens.pop()
                continue
            if _ALLCAP_SHORT_RE.fullmatch(t):
                tokens.pop()
                continue
            
            break
        
        return tokens
    
    def parse_team_name(self, team_name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Parse team name to extract club, series, and team identifier."""
        if not team_name:
            return None, None, None
        
        # Handle special cases with dashes and complex names
        if " - " in team_name:
            parts = team_name.split(" - ")
            if len(parts) == 2:
                club_name = parts[0].strip()
                series_part = parts[1].strip()
                return club_name, series_part, series_part
        
        # Try to extract numeric series first (e.g., "12", "3b", "14a")
        numeric_match = re.search(r'(\d+[a-z]?)$', team_name)
        if numeric_match:
            team_number = numeric_match.group(1)
            club_name = team_name[:numeric_match.start()].strip()
            series_name = f"Series {team_number}"
            return club_name, series_name, team_number
        
        # Try to extract single letter series (e.g., "A", "B", "C")
        letter_match = re.search(r'\s([A-Z])\s*$', team_name)
        if letter_match:
            team_letter = letter_match.group(1)
            club_name = team_name[:letter_match.start()].strip()
            series_name = f"Series {team_letter}"
            return club_name, series_name, team_letter
        
        # Try to extract multi-letter series (e.g., "AA", "BB", "CC")
        multi_letter_match = re.search(r'\s([A-Z]{2,})\s*$', team_name)
        if multi_letter_match:
            team_letters = multi_letter_match.group(1)
            club_name = team_name[:multi_letter_match.start()].strip()
            series_name = f"Series {team_letters}"
            return club_name, series_name, team_letters
        
        # Default fallback
        return team_name.strip(), "Series 1", "1"
    
    def find_team_in_database(self, team_name: str, league_id: str, team_cache: Dict) -> Optional[int]:
        """Enhanced team lookup using unified team management logic."""
        # First try the cache for performance
        team_id = team_cache.get((league_id, team_name))
        if team_id:
            return team_id
        
        # Use unified team management logic for consistent matching
        team_id = self._find_team_by_name_unified(team_name, league_id, team_cache)
        if team_id:
            # Update cache for future lookups
            team_cache[(league_id, team_name)] = team_id
            return team_id
        
        return None
    
    def _find_team_by_name_unified(self, team_name: str, league_id: str, team_cache: Dict) -> Optional[int]:
        """Find team by name using unified team management logic."""
        if not team_name:
            return None
        
        # Strategy 1: Exact match
        for (cache_league, cache_team), cache_team_id in team_cache.items():
            if cache_league == league_id and cache_team == team_name:
                return cache_team_id
        
        # Strategy 2: Parse and match by components
        raw_club_name, series_name, _ = self.parse_team_name(team_name)
        if raw_club_name and series_name:
            club_name = self.normalize_club_name(raw_club_name)
            
            # Look for teams with matching club and series
            for (cache_league, cache_team), cache_team_id in team_cache.items():
                if cache_league == league_id:
                    # Extract club name from database team name and normalize it
                    db_parts = cache_team.split()
                    if len(db_parts) >= 2:
                        db_potential_club = " ".join(db_parts[:2])  # Take first two parts
                        db_normalized_club = self.normalize_club_name(db_potential_club)
                        if db_normalized_club == club_name:
                            return cache_team_id
        
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
            
            # Prevent self-matches (same team playing against itself)
            if home_team_id and away_team_id and home_team_id == away_team_id:
                logger.warning(f"Skipping self-match: {home_team} vs {away_team} (both team_id: {home_team_id})")
                self.stats['skipped'] += 1
                return None
            
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