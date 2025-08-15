#!/usr/bin/env python3
"""
Enhanced Bootstrap System
=========================

Comprehensive bootstrapping system that ensures all necessary database entities
(leagues, series, clubs, teams) are properly created with correct ID relationships
before importing player data.

Key Features:
- Dependency-aware bootstrapping order
- ID relationship validation
- Comprehensive error handling and rollback
- Pre-import validation checks
- Detailed logging and reporting

Usage:
    # Bootstrap all leagues
    bootstrap_system = EnhancedBootstrapSystem()
    bootstrap_system.bootstrap_all()
    
    # Bootstrap specific league
    bootstrap_system = EnhancedBootstrapSystem(league_filter="CNSWPL")
    bootstrap_system.bootstrap_league()
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import psycopg2

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = Path(script_dir).parent.parent.parent
sys.path.insert(0, str(project_root))

from database_utils import execute_query, execute_query_one, execute_update
from database_config import get_db
from utils.league_utils import normalize_league_id

logger = logging.getLogger(__name__)


@dataclass
class BootstrapStats:
    """Statistics for bootstrap operations"""
    leagues_processed: int = 0
    series_created: int = 0
    series_linked: int = 0
    clubs_created: int = 0
    teams_created: int = 0
    teams_updated: int = 0
    validation_errors: int = 0
    skipped_records: int = 0
    
    def print_summary(self):
        """Print formatted summary of bootstrap statistics"""
        print("\n" + "="*60)
        print("🏗️  ENHANCED BOOTSTRAP SUMMARY")
        print("="*60)
        print(f"🏆 Leagues Processed: {self.leagues_processed}")
        print(f"📊 Series Created: {self.series_created}")
        print(f"🔗 Series-League Links: {self.series_linked}")
        print(f"🏢 Clubs Created: {self.clubs_created}")
        print(f"👥 Teams Created: {self.teams_created}")
        print(f"🔄 Teams Updated: {self.teams_updated}")
        print(f"❌ Validation Errors: {self.validation_errors}")
        print(f"⏭️  Skipped Records: {self.skipped_records}")
        print("="*60)


@dataclass 
class EntityContext:
    """Context for database entities"""
    leagues: Dict[str, int] = field(default_factory=dict)  # league_id -> db_id
    series: Dict[Tuple[int, str], int] = field(default_factory=dict)  # (league_db_id, name) -> series_id
    clubs: Dict[str, int] = field(default_factory=dict)  # club_name -> club_id
    teams: Dict[Tuple[int, str], int] = field(default_factory=dict)  # (league_db_id, team_name) -> team_id


class EnhancedBootstrapSystem:
    """Enhanced bootstrapping system with ID-first approach"""
    
    def __init__(self, league_filter: Optional[str] = None):
        self.league_filter = league_filter
        self.stats = BootstrapStats()
        self.context = EntityContext()
        
        # Define paths
        self.data_dir = project_root / "data" / "leagues" / "all"
        self.players_file = self._find_latest_players_file()
        
        logger.info("🏗️  Enhanced Bootstrap System initialized")
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
        """Load players data for bootstrapping"""
        if not self.players_file.exists():
            raise FileNotFoundError(f"Players file not found: {self.players_file}")
        
        logger.info(f"📖 Loading players data from {self.players_file}")
        
        try:
            with open(self.players_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
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
            
            logger.info(f"✅ Loaded {len(data):,} player records for bootstrapping")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error loading players data: {e}")
            raise
    
    def load_existing_context(self):
        """Load existing database entities into context cache"""
        logger.info("🔧 Loading existing database context...")
        
        try:
            # Load leagues
            leagues = execute_query("SELECT league_id, id FROM leagues")
            self.context.leagues = {row['league_id']: row['id'] for row in leagues}
            
            # Load series with league context
            series_query = """
                SELECT l.id as league_db_id, s.name as series_name, s.id as series_id
                FROM series s
                JOIN series_leagues sl ON s.id = sl.series_id
                JOIN leagues l ON sl.league_id = l.id
            """
            series_data = execute_query(series_query)
            for row in series_data:
                key = (row['league_db_id'], row['series_name'])
                self.context.series[key] = row['series_id']
            
            # Load clubs
            clubs = execute_query("SELECT name, id FROM clubs")
            self.context.clubs = {row['name']: row['id'] for row in clubs}
            
            # Load teams
            teams_query = """
                SELECT t.league_id, t.team_name, t.id
                FROM teams t
            """
            teams_data = execute_query(teams_query)
            for row in teams_data:
                key = (row['league_id'], row['team_name'])
                self.context.teams[key] = row['id']
            
            logger.info(f"✅ Loaded context: {len(self.context.leagues)} leagues, "
                       f"{len(self.context.series)} series, {len(self.context.clubs)} clubs, "
                       f"{len(self.context.teams)} teams")
            
        except Exception as e:
            logger.error(f"❌ Error loading database context: {e}")
            raise
    
    def ensure_series(self, series_name: str, league_id: int) -> int:
        """Ensure series exists with league isolation and return its ID"""
        if not series_name.strip():
            raise ValueError("Series name cannot be empty")
        
        # Check if already exists for this league
        existing_series = execute_query_one(
            "SELECT id FROM series WHERE name = %s AND league_id = %s", 
            [series_name, league_id]
        )
        
        if existing_series:
            series_id = existing_series['id']
            logger.debug(f"✅ Series exists: '{series_name}' (league {league_id}) -> {series_id}")
            return series_id
        
        # Create new series with league_id
        try:
            series_id = execute_query_one("""
                INSERT INTO series (name, league_id) 
                VALUES (%s, %s) 
                RETURNING id
            """, [series_name, league_id])['id']
            
            self.stats.series_created += 1
            logger.info(f"✅ Created series: '{series_name}' (league {league_id}) -> {series_id}")
            return series_id
            
        except Exception as e:
            logger.error(f"❌ Error creating series '{series_name}' for league {league_id}: {e}")
            raise
    
    def ensure_series_league_link(self, series_id: int, league_db_id: int):
        """Ensure series is linked to league"""
        # Check if link exists
        existing_link = execute_query_one("""
            SELECT 1 FROM series_leagues 
            WHERE series_id = %s AND league_id = %s
        """, [series_id, league_db_id])
        
        if existing_link:
            logger.debug(f"✅ Series-league link exists: {series_id} <-> {league_db_id}")
            return
        
        # Create link
        try:
            execute_update("""
                INSERT INTO series_leagues (series_id, league_id) 
                VALUES (%s, %s)
            """, [series_id, league_db_id])
            
            self.stats.series_linked += 1
            logger.info(f"✅ Linked series {series_id} to league {league_db_id}")
            
        except Exception as e:
            logger.error(f"❌ Error linking series {series_id} to league {league_db_id}: {e}")
            raise
    
    def ensure_club(self, club_name: str) -> Optional[int]:
        """Ensure club exists and return its ID"""
        if not club_name.strip():
            return None
        
        # Normalize club name (handle common variations)
        normalized_name = self._normalize_club_name(club_name)
        
        # Check if already exists (try both original and normalized)
        for name_to_try in [club_name, normalized_name]:
            if name_to_try in self.context.clubs:
                club_id = self.context.clubs[name_to_try]
                logger.debug(f"✅ Club exists in cache: '{club_name}' -> {club_id}")
                return club_id
            
            existing_club = execute_query_one(
                "SELECT id FROM clubs WHERE name = %s", 
                [name_to_try]
            )
            if existing_club:
                club_id = existing_club['id']
                self.context.clubs[name_to_try] = club_id  # Cache it
                logger.debug(f"✅ Club exists: '{club_name}' -> {club_id}")
                return club_id
        
        # Create new club
        try:
            club_id = execute_query_one("""
                INSERT INTO clubs (name) 
                VALUES (%s) 
                RETURNING id
            """, [normalized_name])['id']
            
            self.context.clubs[normalized_name] = club_id
            self.stats.clubs_created += 1
            logger.info(f"✅ Created club: '{club_name}' -> '{normalized_name}' -> {club_id}")
            return club_id
            
        except Exception as e:
            logger.error(f"❌ Error creating club '{club_name}': {e}")
            return None
    
    def _normalize_club_name(self, club_name: str) -> str:
        """Normalize club name for consistency"""
        import re
        
        # Handle common variations
        normalized = club_name
        
        # Remove numbers and suffixes (e.g., "Lake Shore CC 11" -> "Lake Shore CC")
        normalized = re.sub(r'\s+\d+.*$', '', normalized).strip()
        
        # Handle special cases
        special_mappings = {
            'LifeSport-Lshire': 'LifeSport',
            'Park RIdge CC': 'Park Ridge CC',
            'Barrington Hills': 'Barrington'
        }
        
        for pattern, replacement in special_mappings.items():
            if normalized.startswith(pattern) or normalized == pattern:
                normalized = replacement
                break
        
        return normalized.strip()
    
    def ensure_team(self, team_name: str, club_id: Optional[int], 
                   series_id: Optional[int], league_db_id: int) -> Optional[int]:
        """Ensure team exists and return its ID"""
        if not team_name.strip():
            return None
        
        # Check if already exists
        team_key = (league_db_id, team_name)
        if team_key in self.context.teams:
            team_id = self.context.teams[team_key]
            logger.debug(f"✅ Team exists in cache: '{team_name}' -> {team_id}")
            return team_id
        
        existing_team = execute_query_one("""
            SELECT id FROM teams 
            WHERE team_name = %s AND league_id = %s
        """, [team_name, league_db_id])
        
        if existing_team:
            team_id = existing_team['id']
            self.context.teams[team_key] = team_id
            logger.debug(f"✅ Team exists: '{team_name}' -> {team_id}")
            
            # Check if team needs updates
            self._update_team_if_needed(team_id, club_id, series_id)
            return team_id
        
        # Create new team
        try:
            team_id = execute_query_one("""
                INSERT INTO teams (
                    team_name, club_id, series_id, league_id, 
                    is_active, team_alias
                ) VALUES (%s, %s, %s, %s, TRUE, %s) 
                RETURNING id
            """, [team_name, club_id, series_id, league_db_id, team_name])['id']
            
            self.context.teams[team_key] = team_id
            self.stats.teams_created += 1
            logger.info(f"✅ Created team: '{team_name}' -> {team_id} "
                       f"(club: {club_id}, series: {series_id}, league: {league_db_id})")
            return team_id
            
        except Exception as e:
            logger.error(f"❌ Error creating team '{team_name}': {e}")
            return None
    
    def _update_team_if_needed(self, team_id: int, club_id: Optional[int], 
                              series_id: Optional[int]):
        """Update team if club_id or series_id are missing"""
        if not club_id and not series_id:
            return
        
        # Get current team data
        current_team = execute_query_one("""
            SELECT club_id, series_id FROM teams WHERE id = %s
        """, [team_id])
        
        if not current_team:
            return
        
        updates_needed = []
        params = []
        
        if club_id and not current_team['club_id']:
            updates_needed.append("club_id = %s")
            params.append(club_id)
        
        if series_id and not current_team['series_id']:
            updates_needed.append("series_id = %s")
            params.append(series_id)
        
        if updates_needed:
            params.append(team_id)
            update_query = f"""
                UPDATE teams 
                SET {', '.join(updates_needed)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            
            execute_update(update_query, params)
            self.stats.teams_updated += 1
            logger.info(f"✅ Updated team {team_id} with missing references")
    
    def bootstrap_league_entities(self, league_data: List[Dict]):
        """Bootstrap all entities for league(s) from player data"""
        logger.info(f"🏗️  Bootstrapping entities from {len(league_data)} player records...")
        
        # Track what we've seen to avoid duplicates
        seen_series: Set[Tuple[str, str]] = set()  # (league_id, series_name)
        seen_clubs: Set[str] = set()
        seen_teams: Set[Tuple[str, str, str]] = set()  # (league_id, series_name, team_name)
        
        for record in league_data:
            try:
                # Extract data
                raw_league_id = (record.get("League") or "").strip()
                series_name = (record.get("Series") or "").strip()
                team_name = (record.get("Series Mapping ID") or "").strip()
                club_name = (record.get("Club") or "").strip()
                
                if not all([raw_league_id, series_name, team_name]):
                    self.stats.skipped_records += 1
                    continue
                
                # Normalize league ID
                league_id = normalize_league_id(raw_league_id)
                league_db_id = self.context.leagues.get(league_id)
                
                if not league_db_id:
                    logger.warning(f"League not found in database: {league_id}")
                    self.stats.validation_errors += 1
                    continue
                
                # Ensure series exists and is linked to league
                series_key = (league_id, series_name)
                if series_key not in seen_series:
                    series_id = self.ensure_series(series_name, league_db_id)
                    self.ensure_series_league_link(series_id, league_db_id)
                    
                    # Cache the series
                    cache_key = (league_db_id, series_name)
                    self.context.series[cache_key] = series_id
                    
                    seen_series.add(series_key)
                else:
                    # Get from cache
                    cache_key = (league_db_id, series_name)
                    series_id = self.context.series.get(cache_key)
                
                # Ensure club exists
                club_id = None
                if club_name and club_name not in seen_clubs:
                    club_id = self.ensure_club(club_name)
                    seen_clubs.add(club_name)
                elif club_name:
                    club_id = self.context.clubs.get(self._normalize_club_name(club_name))
                
                # Ensure team exists
                team_key = (league_id, series_name, team_name)
                if team_key not in seen_teams:
                    team_id = self.ensure_team(team_name, club_id, series_id, league_db_id)
                    seen_teams.add(team_key)
                
            except Exception as e:
                logger.error(f"Error processing record: {e}")
                self.stats.validation_errors += 1
                continue
        
        # Count processed leagues
        processed_leagues = set()
        for record in league_data:
            raw_league = (record.get("League") or "").strip()
            if raw_league:
                processed_leagues.add(normalize_league_id(raw_league))
        
        self.stats.leagues_processed = len(processed_leagues)
        
        logger.info(f"✅ Bootstrap completed for {len(processed_leagues)} leagues")
    
    def validate_bootstrap_integrity(self) -> bool:
        """Validate that all bootstrap operations created consistent data"""
        logger.info("🔍 Validating bootstrap integrity...")
        
        validation_errors = []
        
        try:
            # Check for orphaned series (series without league links)
            orphaned_series = execute_query("""
                SELECT s.id, s.name 
                FROM series s 
                LEFT JOIN series_leagues sl ON s.id = sl.series_id 
                WHERE sl.series_id IS NULL
            """)
            
            if orphaned_series:
                validation_errors.append(f"Found {len(orphaned_series)} orphaned series")
                for series in orphaned_series[:5]:  # Show first 5
                    validation_errors.append(f"  - Series {series['id']}: '{series['name']}'")
            
            # Check for teams without proper references
            invalid_teams = execute_query("""
                SELECT t.id, t.team_name, t.league_id, t.series_id, t.club_id
                FROM teams t
                LEFT JOIN leagues l ON t.league_id = l.id
                LEFT JOIN series s ON t.series_id = s.id
                LEFT JOIN clubs c ON t.club_id = c.id
                WHERE t.is_active = TRUE AND (
                    l.id IS NULL OR 
                    (t.series_id IS NOT NULL AND s.id IS NULL) OR
                    (t.club_id IS NOT NULL AND c.id IS NULL)
                )
            """)
            
            if invalid_teams:
                validation_errors.append(f"Found {len(invalid_teams)} teams with invalid references")
                for team in invalid_teams[:5]:  # Show first 5
                    validation_errors.append(f"  - Team {team['id']}: '{team['team_name']}'")
            
            # Check for series not linked to any league
            unlinked_series = execute_query("""
                SELECT COUNT(*) as count
                FROM series s
                WHERE NOT EXISTS (
                    SELECT 1 FROM series_leagues sl WHERE sl.series_id = s.id
                )
            """)
            
            if unlinked_series and unlinked_series[0]['count'] > 0:
                validation_errors.append(f"Found {unlinked_series[0]['count']} series not linked to any league")
            
            if validation_errors:
                logger.error("❌ Bootstrap validation failed:")
                for error in validation_errors:
                    logger.error(f"   {error}")
                return False
            else:
                logger.info("✅ Bootstrap validation passed")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error during validation: {e}")
            return False
    
    def bootstrap_all(self):
        """Bootstrap all entities from players data"""
        logger.info("🚀 Starting enhanced bootstrap process...")
        
        try:
            # Load existing context
            self.load_existing_context()
            
            # Load players data
            players_data = self.load_players_data()
            
            # Bootstrap entities
            self.bootstrap_league_entities(players_data)
            
            # Validate integrity
            if not self.validate_bootstrap_integrity():
                raise Exception("Bootstrap validation failed")
            
            # Print summary
            self.stats.print_summary()
            
            logger.info("✅ Enhanced bootstrap completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Bootstrap failed: {e}")
            raise
    
    def bootstrap_league(self):
        """Bootstrap specific league (when league_filter is set)"""
        if not self.league_filter:
            raise ValueError("League filter must be set for league-specific bootstrap")
        
        logger.info(f"🚀 Starting enhanced bootstrap for league: {self.league_filter}")
        self.bootstrap_all()


def main():
    """Main entry point for enhanced bootstrap system"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Bootstrap System")
    parser.add_argument("--league", help="Bootstrap specific league only")
    parser.add_argument("--validate-only", action="store_true",
                       help="Only run validation checks")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        bootstrap_system = EnhancedBootstrapSystem(league_filter=args.league)
        
        if args.validate_only:
            # Just run validation
            bootstrap_system.load_existing_context()
            if bootstrap_system.validate_bootstrap_integrity():
                print("✅ Bootstrap validation passed")
            else:
                print("❌ Bootstrap validation failed")
                sys.exit(1)
        else:
            # Run full bootstrap
            if args.league:
                bootstrap_system.bootstrap_league()
            else:
                bootstrap_system.bootstrap_all()
    
    except Exception as e:
        logger.error(f"❌ Bootstrap system failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
