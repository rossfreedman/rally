#!/usr/bin/env python3
"""
Enhanced Players Import with ID-Based Lookups
==============================================

Advanced player import system that prioritizes ID-based operations over name matching.
Provides robust import with comprehensive validation and error handling.

Key Features:
- ID-first strategy with name-based fallbacks
- Duplicate prevention and validation
- Enhanced error handling and logging
- Session data preparation for immediate use
- Comprehensive statistics and reporting

Usage:
    # Import all players
    enhanced_etl = EnhancedPlayersETL()
    enhanced_etl.import_players()
    
    # Import specific league
    enhanced_etl = EnhancedPlayersETL(league_filter="CNSWPL")
    enhanced_etl.import_players()
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import psycopg2

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = Path(script_dir).parent.parent.parent
sys.path.insert(0, str(project_root))

from database_utils import execute_query, execute_update
from database_config import get_db
from data.etl.database_import.id_based_lookup_service import IdBasedLookupService, ResolvedIds
from data.etl.database_import.duplicate_prevention_service import DuplicatePreventionService
from utils.league_utils import normalize_league_id

logger = logging.getLogger(__name__)


@dataclass
class ImportStats:
    """Statistics for import process"""
    total_records: int = 0
    processed: int = 0
    imported: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    id_resolved: int = 0
    name_fallback: int = 0
    validation_failed: int = 0
    
    def print_summary(self):
        """Print formatted summary of import statistics"""
        print("\n" + "="*60)
        print("📊 ENHANCED PLAYERS IMPORT SUMMARY")
        print("="*60)
        print(f"📋 Total Records: {self.total_records:,}")
        print(f"⚙️  Processed: {self.processed:,}")
        print(f"✅ Imported: {self.imported:,}")
        print(f"🔄 Updated: {self.updated:,}")
        print(f"⏭️  Skipped: {self.skipped:,}")
        print(f"❌ Errors: {self.errors:,}")
        print()
        print("🎯 ID Resolution:")
        print(f"   🆔 ID-based: {self.id_resolved:,}")
        print(f"   📝 Name fallback: {self.name_fallback:,}")
        print(f"   ❌ Validation failed: {self.validation_failed:,}")
        print()
        success_rate = (self.imported + self.updated) / max(self.total_records, 1) * 100
        print(f"🏆 Success Rate: {success_rate:.1f}%")
        print("="*60)


class EnhancedPlayersETL:
    """Enhanced ETL for importing players with ID-based lookups"""
    
    def __init__(self, players_file: Optional[str] = None, 
                 league_filter: Optional[str] = None,
                 prevent_duplicates: bool = True,
                 validate_consistency: bool = True):
        self.league_filter = league_filter
        self.validate_consistency = validate_consistency
        self.stats = ImportStats()
        
        # Initialize services
        self.lookup_service = IdBasedLookupService()
        
        self.prevent_duplicates = prevent_duplicates
        if self.prevent_duplicates:
            self.duplicate_service = DuplicatePreventionService()
            logger.info("✅ Duplicate prevention service initialized")
        
        # Define paths
        self.data_dir = project_root / "data" / "leagues" / "all"
        
        if players_file:
            self.players_file = Path(players_file)
        else:
            # Find the most recent players file
            self.players_file = self._find_latest_players_file()
        
        logger.info("🚀 Enhanced Players ETL initialized")
        logger.info(f"📁 Data directory: {self.data_dir}")
        logger.info(f"📄 Players file: {self.players_file}")
        if self.league_filter:
            logger.info(f"🎯 League filter: {self.league_filter}")
    
    def _find_latest_players_file(self) -> Path:
        """Find the most recent players file"""
        # Try incremental files first
        incremental_files = list(self.data_dir.glob("players_incremental_*.json"))
        if incremental_files:
            incremental_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return incremental_files[0]
        
        # Fallback to players.json
        players_file = self.data_dir / "players.json"
        if players_file.exists():
            return players_file
        
        raise FileNotFoundError(f"No players file found in {self.data_dir}")
    
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
            
            # Apply league filter if specified
            if self.league_filter:
                original_count = len(data)
                normalized_filter = normalize_league_id(self.league_filter)
                
                filtered_data = []
                for record in data:
                    raw_league = (record.get("League") or "").strip()
                    normalized_league = normalize_league_id(raw_league)
                    
                    if (raw_league == self.league_filter or 
                        normalized_league == normalized_filter or
                        normalized_league == self.league_filter):
                        filtered_data.append(record)
                
                data = filtered_data
                logger.info(f"🎯 Filtered from {original_count:,} to {len(data):,} records for league '{self.league_filter}'")
            
            self.stats.total_records = len(data)
            logger.info(f"✅ Loaded {len(data):,} player records")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error loading players data: {e}")
            raise
    
    def process_player_record(self, record: Dict) -> Optional[Tuple]:
        """Process a single player record using enhanced ID-based lookups"""
        try:
            # Extract data from record
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
                self.stats.skipped += 1
                return None
            
            # Normalize league ID
            league_id = normalize_league_id(raw_league_id) if raw_league_id else ""
            if not league_id:
                logger.warning(f"Invalid league ID: {raw_league_id}")
                self.stats.skipped += 1
                return None
            
            # **ENHANCED: Use ID-based lookup service**
            resolved_ids = self.lookup_service.resolve_all_ids(
                league_id=league_id,
                series_name=series_name,
                team_name=team_name,
                club_name=club_name
            )
            
            # Check if we have essential IDs
            if not resolved_ids.league_db_id:
                logger.warning(f"Could not resolve league: {league_id}")
                self.stats.errors += 1
                return None
            
            # Track resolution method
            if resolved_ids.is_complete():
                self.stats.id_resolved += 1
                
                # Validate consistency if enabled
                if self.validate_consistency:
                    if not self.lookup_service.validate_consistency(resolved_ids):
                        logger.error(f"ID consistency validation failed for {tenniscores_player_id}")
                        self.stats.validation_failed += 1
                        return None
            else:
                self.stats.name_fallback += 1
                logger.debug(f"Incomplete ID resolution for {tenniscores_player_id}: "
                           f"league_db_id={resolved_ids.league_db_id}, "
                           f"series_id={resolved_ids.series_id}, "
                           f"team_id={resolved_ids.team_id}, "
                           f"club_id={resolved_ids.club_id}")
            
            # Parse PTI
            pti = None
            if pti_str and pti_str.lower() not in ['n/a', 'none', '']:
                try:
                    pti = float(pti_str)
                except ValueError:
                    logger.debug(f"Invalid PTI value: {pti_str}")
            
            # Prepare data tuple for insertion
            return (
                tenniscores_player_id,
                first_name,
                last_name,
                resolved_ids.league_db_id,
                resolved_ids.club_id,
                resolved_ids.series_id,
                resolved_ids.team_id,
                pti,
                True  # is_active
            )
            
        except Exception as e:
            logger.error(f"Error processing player record {record.get('Player ID', 'unknown')}: {e}")
            self.stats.errors += 1
            return None
    
    def import_players(self):
        """Import players using enhanced ID-based lookup system"""
        logger.info("🚀 Starting enhanced players import...")
        
        # Load data
        players_data = self.load_players_data()
        
        # Get database connection
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                
                # Process each player record
                batch_size = 100
                batch_data = []
                
                for i, record in enumerate(players_data):
                    self.stats.processed += 1
                    
                    # Process record
                    player_data = self.process_player_record(record)
                    if player_data is None:
                        continue
                    
                    # Check for duplicates if enabled
                    if self.prevent_duplicates:
                        try:
                            # Extract data for duplicate check
                            tenniscores_player_id, _, _, league_db_id, club_id, series_id, team_id, _, _ = player_data
                            
                            existing_record = self.duplicate_service.check_existing_player(
                                tenniscores_player_id=tenniscores_player_id,
                                league_id=league_db_id,
                                club_id=club_id,
                                series_id=series_id
                            )
                            
                            if existing_record:
                                logger.debug(f"Player already exists: {tenniscores_player_id}")
                                self.stats.skipped += 1
                                continue
                                
                        except Exception as e:
                            logger.warning(f"Duplicate check failed for {player_data[0]}: {e}")
                    
                    batch_data.append(player_data)
                    
                    # Process batch
                    if len(batch_data) >= batch_size or i == len(players_data) - 1:
                        self._process_batch(cursor, batch_data)
                        batch_data = []
                    
                    # Progress reporting
                    if (i + 1) % 1000 == 0:
                        logger.info(f"📊 Processed {i + 1:,}/{len(players_data):,} records "
                                   f"({(i + 1) / len(players_data) * 100:.1f}%)")
                
                # Commit transaction
                conn.commit()
                logger.info("✅ Transaction committed successfully")
                
        except Exception as e:
            logger.error(f"❌ Error during import: {e}")
            raise
        
        # Print summary
        self.stats.print_summary()
    
    def _process_batch(self, cursor, batch_data: List[Tuple]):
        """Process a batch of player records"""
        if not batch_data:
            return
        
        try:
            # Use ON CONFLICT for upsert behavior
            insert_query = """
                INSERT INTO players (
                    tenniscores_player_id, first_name, last_name, league_id,
                    club_id, series_id, team_id, pti, is_active
                ) VALUES %s
                ON CONFLICT (tenniscores_player_id, league_id, club_id, series_id) 
                DO UPDATE SET
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    team_id = EXCLUDED.team_id,
                    pti = EXCLUDED.pti,
                    is_active = EXCLUDED.is_active,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING 
                    tenniscores_player_id,
                    (xmax = 0) AS inserted
            """
            
            # Execute batch insert
            from psycopg2.extras import execute_values
            results = execute_values(
                cursor, insert_query, batch_data, 
                template=None, page_size=100, fetch=True
            )
            
            # Track insert vs update statistics
            for result in results:
                if result[1]:  # inserted (xmax = 0)
                    self.stats.imported += 1
                else:  # updated (xmax > 0)
                    self.stats.updated += 1
            
            logger.debug(f"✅ Processed batch of {len(batch_data)} records")
            
        except Exception as e:
            logger.error(f"❌ Error processing batch: {e}")
            self.stats.errors += len(batch_data)
            raise
    
    def generate_session_data_cache(self):
        """Generate session data cache for immediate use after import"""
        logger.info("🔧 Generating session data cache...")
        
        try:
            # This could be enhanced to pre-populate session data
            # for faster user login experiences
            session_query = """
                SELECT 
                    p.tenniscores_player_id,
                    p.first_name,
                    p.last_name,
                    l.league_id,
                    l.id as league_db_id,
                    c.name as club,
                    s.name as series,
                    t.team_name,
                    t.id as team_id
                FROM players p
                JOIN leagues l ON p.league_id = l.id
                LEFT JOIN clubs c ON p.club_id = c.id
                LEFT JOIN series s ON p.series_id = s.id
                LEFT JOIN teams t ON p.team_id = t.id
                WHERE p.is_active = TRUE
                LIMIT 10
            """
            
            sample_data = execute_query(session_query)
            logger.info(f"✅ Session data sample ready: {len(sample_data)} records")
            
            # Could save this to a cache file for faster access
            
        except Exception as e:
            logger.error(f"❌ Error generating session data cache: {e}")


def main():
    """Main entry point for enhanced players import"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Players Import with ID-based lookups")
    parser.add_argument("--league", help="Filter by specific league")
    parser.add_argument("--file", help="Specific players file to import")
    parser.add_argument("--no-duplicates", action="store_true", 
                       help="Disable duplicate prevention")
    parser.add_argument("--no-validation", action="store_true",
                       help="Disable ID consistency validation")
    parser.add_argument("--test", action="store_true",
                       help="Run test mode with sample data")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        if args.test:
            # Test mode - run with sample data
            logger.info("🧪 Running in test mode...")
            
            # Test the lookup service
            lookup_service = IdBasedLookupService()
            resolved_ids = lookup_service.resolve_all_ids(
                league_id="CNSWPL",
                series_name="Series 12", 
                team_name="Tennaqua 12",
                club_name="Tennaqua"
            )
            
            print(f"Test resolution:")
            print(f"  Complete: {resolved_ids.is_complete()}")
            print(f"  League DB ID: {resolved_ids.league_db_id}")
            print(f"  Series ID: {resolved_ids.series_id}")
            print(f"  Team ID: {resolved_ids.team_id}")
            print(f"  Club ID: {resolved_ids.club_id}")
            
            if resolved_ids.is_complete():
                consistent = lookup_service.validate_consistency(resolved_ids)
                print(f"  Consistent: {consistent}")
        
        else:
            # Normal import mode
            enhanced_etl = EnhancedPlayersETL(
                players_file=args.file,
                league_filter=args.league,
                prevent_duplicates=not args.no_duplicates,
                validate_consistency=not args.no_validation
            )
            
            enhanced_etl.import_players()
            enhanced_etl.generate_session_data_cache()
            
            logger.info("🎉 Enhanced players import completed successfully!")
    
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
