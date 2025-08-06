#!/usr/bin/env python3
"""
Enhanced Schedule Import with Validation
=======================================

Enhanced ETL process for importing schedule data with comprehensive validation,
error handling, and data quality checks. This addresses the root causes of
the previous schedule data issues.

Usage:
    python3 data/etl/database_import/enhanced_import_schedules.py [schedules_file]
"""

import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.insert(0, project_root)

from database_config import get_db
from utils.league_utils import normalize_league_id

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class EnhancedSchedulesETL:
    """Enhanced ETL class for importing schedules with comprehensive validation"""
    
    def __init__(self, schedules_file: str = None):
        # Define paths
        self.data_dir = Path(project_root) / "data" / "leagues" / "all"
        
        if schedules_file:
            self.schedules_file = Path(schedules_file)
        else:
            # Find the schedules file - try incremental first, then fallback to schedules.json
            schedules_files = list(self.data_dir.glob("schedules_incremental_*.json"))
            if schedules_files:
                # Sort by modification time and get the most recent
                schedules_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                self.schedules_file = schedules_files[0]
            else:
                # Fallback to schedules.json
                schedules_file_path = self.data_dir / "schedules.json"
                if schedules_file_path.exists():
                    self.schedules_file = schedules_file_path
                else:
                    raise FileNotFoundError(f"No schedules file found in {self.data_dir}")
        
        # Statistics
        self.stats = {
            'total_records': 0,
            'imported': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0,
            'validation_issues': 0
        }
        
        # Validation results
        self.validation_issues = []
        self.team_mapping_issues = []
        
        logger.info("🔧 Enhanced Schedules ETL initialized")
        logger.info(f"📁 Data directory: {self.data_dir}")
        logger.info(f"📄 Schedules file: {self.schedules_file}")
    
    def validate_etl_preconditions(self) -> Tuple[bool, List[str]]:
        """Validate ETL preconditions before import"""
        logger.info("🔍 Validating ETL preconditions...")
        
        issues = []
        
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                
                # Check 1: Unique constraint exists
                cursor.execute("""
                    SELECT constraint_name 
                    FROM information_schema.table_constraints 
                    WHERE table_name = 'schedule' 
                    AND constraint_type = 'UNIQUE'
                    AND constraint_name = 'unique_schedule_match'
                """)
                
                if not cursor.fetchone():
                    issues.append("Missing unique constraint 'unique_schedule_match' on schedule table")
                
                # Check 2: No existing duplicate records
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM (
                        SELECT match_date, home_team, away_team, league_id, COUNT(*)
                        FROM schedule 
                        GROUP BY match_date, home_team, away_team, league_id 
                        HAVING COUNT(*) > 1
                    ) duplicates
                """)
                
                duplicate_count = cursor.fetchone()[0]
                if duplicate_count > 0:
                    issues.append(f"Found {duplicate_count} groups of duplicate schedule records")
                
                # Check 3: Team name mapping integrity
                mapping_issues = self.validate_team_name_mapping(cursor)
                if mapping_issues:
                    issues.extend(mapping_issues)
                
        except Exception as e:
            issues.append(f"Database connection error: {e}")
        
        is_safe = len(issues) == 0
        if not is_safe:
            logger.warning("⚠️ ETL preconditions validation failed:")
            for issue in issues:
                logger.warning(f"   ❌ {issue}")
        else:
            logger.info("✅ ETL preconditions validation passed")
        
        return is_safe, issues
    
    def validate_team_name_mapping(self, cursor) -> List[str]:
        """Validate team name mapping integrity"""
        issues = []
        
        # Check for teams with missing schedule data
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM teams t
            LEFT JOIN schedule s ON (t.id = s.home_team_id OR t.id = s.away_team_id)
            GROUP BY t.id
            HAVING COUNT(s.id) = 0
        """)
        
        missing_teams = len(cursor.fetchall())
        if missing_teams > 0:
            issues.append(f"{missing_teams} teams have no schedule data")
        
        # Check for schedule records with NULL team_id
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM schedule
            WHERE home_team_id IS NULL AND away_team_id IS NULL
        """)
        
        null_team_records = cursor.fetchone()[0]
        if null_team_records > 0:
            issues.append(f"{null_team_records} schedule records have NULL team_id")
        
        return issues
    
    def load_schedules_data(self) -> List[Dict]:
        """Load schedules data from JSON file with validation"""
        if not self.schedules_file.exists():
            raise FileNotFoundError(f"Schedules file not found: {self.schedules_file}")
        
        logger.info(f"📖 Loading schedules data from {self.schedules_file}")
        
        try:
            with open(self.schedules_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                logger.warning("Data is not a list, wrapping in list")
                data = [data]
            
            # Validate data structure
            validation_issues = self.validate_schedule_data_structure(data)
            if validation_issues:
                logger.warning(f"⚠️ Data structure validation issues: {validation_issues}")
                self.stats['validation_issues'] += len(validation_issues)
            
            self.stats['total_records'] = len(data)
            logger.info(f"✅ Loaded {len(data):,} schedule records")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error loading schedules data: {e}")
            raise
    
    def validate_schedule_data_structure(self, data: List[Dict]) -> List[str]:
        """Validate schedule data structure"""
        issues = []
        
        required_fields = ['date', 'home_team', 'away_team']
        optional_fields = ['time', 'location', 'League']
        
        for i, record in enumerate(data):
            if not isinstance(record, dict):
                issues.append(f"Record {i}: Not a dictionary")
                continue
            
            # Check required fields
            for field in required_fields:
                if field not in record or not record[field]:
                    issues.append(f"Record {i}: Missing required field '{field}'")
            
            # Check for unexpected fields
            expected_fields = required_fields + optional_fields
            unexpected_fields = [f for f in record.keys() if f not in expected_fields]
            if unexpected_fields:
                issues.append(f"Record {i}: Unexpected fields: {unexpected_fields}")
        
        return issues
    
    def pre_cache_lookup_data(self, conn) -> tuple:
        """Pre-cache league and team data for faster lookups with enhanced mapping"""
        cursor = conn.cursor()
        
        logger.info("🔧 Pre-caching lookup data...")
        
        # Cache league mappings
        cursor.execute("SELECT league_id, id FROM leagues")
        league_cache = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Enhanced team cache with multiple name variations
        cursor.execute("""
            SELECT l.league_id, t.team_name, t.id, t.club_id, t.series_id
            FROM teams t 
            JOIN leagues l ON t.league_id = l.id
        """)
        
        team_cache = {}
        team_variations = {}
        
        for row in cursor.fetchall():
            league_id, team_name, team_id, club_id, series_id = row
            
            # Store exact match
            team_cache[(league_id, team_name)] = team_id
            
            # Create name variations for enhanced matching
            variations = self.generate_team_name_variations(team_name)
            for variation in variations:
                team_cache[(league_id, variation)] = team_id
            
            # Store team info for fallback matching
            team_variations[team_id] = {
                'name': team_name,
                'club_id': club_id,
                'series_id': series_id,
                'variations': variations
            }
        
        logger.info(f"✅ Cached {len(league_cache)} leagues, {len(team_cache)} team mappings")
        
        return league_cache, team_cache, team_variations
    
    def generate_team_name_variations(self, team_name: str) -> List[str]:
        """Generate team name variations for enhanced matching"""
        variations = [team_name]
        
        # Remove " - Series X" suffix
        if " - Series " in team_name:
            simple_name = team_name.split(" - Series ")[0]
            variations.append(simple_name)
        
        # Add "(Division X)" suffix if not present
        if " (Division " not in team_name:
            import re
            match = re.search(r'(\w+)\s*-\s*(\d+)', team_name)
            if match:
                club_name = match.group(1)
                division_num = match.group(2)
                division_name = f"{club_name} - {division_num} (Division {division_num})"
                variations.append(division_name)
        
        # Remove "(Division X)" suffix
        if " (Division " in team_name:
            simple_name = team_name.split(" (Division ")[0]
            variations.append(simple_name)
        
        return list(set(variations))  # Remove duplicates
    
    def enhanced_team_name_mapping(self, team_name: str, league_id: str, 
                                 team_cache: Dict, team_variations: Dict) -> Optional[int]:
        """Enhanced team name mapping with multiple fallback strategies"""
        
        # Strategy 1: Exact match
        team_id = team_cache.get((league_id, team_name))
        if team_id:
            return team_id
        
        # Strategy 2: Try all variations
        for team_id, team_info in team_variations.items():
            if team_name in team_info['variations']:
                return team_id
        
        # Strategy 3: Fuzzy matching (simple contains check)
        for cached_name, cached_id in team_cache.items():
            if cached_name[0] == league_id and team_name.lower() in cached_name[1].lower():
                return cached_id
        
        return None
    
    def process_schedule_record(self, record: Dict, league_cache: Dict, 
                              team_cache: Dict, team_variations: Dict) -> Optional[tuple]:
        """Process a single schedule record with enhanced validation"""
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
            
            # Parse date with enhanced error handling
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
            
            # Handle empty time fields
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
            
            # Enhanced team ID lookup with multiple strategies
            home_team_id = None
            away_team_id = None
            
            if home_team and home_team != "BYE":
                home_team_id = self.enhanced_team_name_mapping(
                    home_team, league_id, team_cache, team_variations
                )
                
                if not home_team_id:
                    logger.warning(f"Home team not found: {home_team} in {league_id}")
                    self.team_mapping_issues.append(f"Home team: {home_team}")
            
            if away_team and away_team != "BYE":
                away_team_id = self.enhanced_team_name_mapping(
                    away_team, league_id, team_cache, team_variations
                )
                
                if not away_team_id:
                    logger.warning(f"Away team not found: {away_team} in {league_id}")
                    self.team_mapping_issues.append(f"Away team: {away_team}")
            
            return (
                match_date, match_time, home_team, away_team, 
                home_team_id, away_team_id, location, league_db_id
            )
            
        except Exception as e:
            logger.error(f"❌ Error processing schedule record: {e}")
            self.stats['errors'] += 1
            return None
    
    def process_batch(self, cursor, batch_data: List[tuple]) -> int:
        """Process a batch of schedule records using upsert logic with error handling"""
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
    
    def validate_import_results(self) -> Tuple[bool, List[str]]:
        """Validate ETL import results"""
        logger.info("🔍 Validating import results...")
        
        validations = []
        
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                
                # Validation 1: Check for teams without schedule data
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM teams t
                    LEFT JOIN schedule s ON (t.id = s.home_team_id OR t.id = s.away_team_id)
                    GROUP BY t.id
                    HAVING COUNT(s.id) = 0
                """)
                
                missing_teams = len(cursor.fetchall())
                if missing_teams > 0:
                    validations.append(f"Teams missing schedule data: {missing_teams}")
                
                # Validation 2: Check for NULL team_id values
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM schedule
                    WHERE home_team_id IS NULL AND away_team_id IS NULL
                """)
                
                null_team_count = cursor.fetchone()[0]
                if null_team_count > 0:
                    validations.append(f"Schedule records with NULL team_id: {null_team_count}")
                
                # Validation 3: Check for duplicate records
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM (
                        SELECT match_date, home_team, away_team, league_id, COUNT(*)
                        FROM schedule 
                        GROUP BY match_date, home_team, away_team, league_id 
                        HAVING COUNT(*) > 1
                    ) duplicates
                """)
                
                duplicate_count = cursor.fetchone()[0]
                if duplicate_count > 0:
                    validations.append(f"Duplicate schedule records: {duplicate_count}")
                
        except Exception as e:
            validations.append(f"Validation error: {e}")
        
        is_valid = len(validations) == 0
        if not is_valid:
            logger.warning("⚠️ Import validation issues:")
            for validation in validations:
                logger.warning(f"   ❌ {validation}")
        else:
            logger.info("✅ Import validation passed")
        
        return is_valid, validations
    
    def import_schedules(self, schedules_data: List[Dict]):
        """Import schedules to the database with enhanced error handling"""
        logger.info("🚀 Starting enhanced schedules import...")
        
        try:
            with get_db() as conn:
                # Pre-cache lookup data
                league_cache, team_cache, team_variations = self.pre_cache_lookup_data(conn)
                
                # Process records in batches
                batch_size = 100
                batch_data = []
                
                for record_idx, record in enumerate(schedules_data):
                    # Process the record
                    processed_data = self.process_schedule_record(
                        record, league_cache, team_cache, team_variations
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
        """Print enhanced import summary"""
        logger.info("=" * 60)
        logger.info("📊 ENHANCED SCHEDULES IMPORT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"📄 Total records processed: {self.stats['total_records']:,}")
        logger.info(f"✅ Successfully imported: {self.stats['imported']:,}")
        logger.info(f"❌ Errors: {self.stats['errors']}")
        logger.info(f"⏭️ Skipped: {self.stats['skipped']}")
        logger.info(f"🔍 Validation issues: {self.stats['validation_issues']}")
        
        if self.team_mapping_issues:
            logger.info(f"⚠️ Team mapping issues: {len(self.team_mapping_issues)}")
            for issue in self.team_mapping_issues[:5]:  # Show first 5
                logger.info(f"   - {issue}")
            if len(self.team_mapping_issues) > 5:
                logger.info(f"   ... and {len(self.team_mapping_issues) - 5} more")
        
        # Calculate success rate
        total_processed = self.stats['total_records']
        if total_processed > 0:
            success_rate = ((self.stats['imported'] + self.stats['skipped']) / total_processed) * 100
            logger.info(f"📈 Success rate: {success_rate:.2f}%")
        
        logger.info("=" * 60)
    
    def run(self):
        """Run the complete enhanced ETL process"""
        logger.info("🚀 Starting Enhanced Schedules ETL...")
        
        try:
            # Step 1: Validate preconditions
            is_safe, preconditions = self.validate_etl_preconditions()
            if not is_safe:
                logger.error("❌ ETL preconditions validation failed - aborting")
                return False
            
            # Step 2: Load schedules data
            schedules_data = self.load_schedules_data()
            
            # Step 3: Import schedules
            self.import_schedules(schedules_data)
            
            # Step 4: Validate import results
            is_valid, validations = self.validate_import_results()
            
            # Step 5: Print summary
            self.print_summary()
            
            if is_valid:
                logger.info("✅ Enhanced Schedules ETL completed successfully!")
                return True
            else:
                logger.warning("⚠️ Enhanced Schedules ETL completed with validation issues")
                return False
            
        except Exception as e:
            logger.error(f"❌ Enhanced Schedules ETL failed: {e}")
            raise


def main():
    """Main function"""
    logger.info("🎯 Enhanced Schedules ETL Script")
    logger.info("=" * 50)
    
    # Get schedules file from command line argument
    schedules_file = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        etl = EnhancedSchedulesETL(schedules_file)
        success = etl.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 