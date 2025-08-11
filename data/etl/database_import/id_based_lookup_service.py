#!/usr/bin/env python3
"""
ID-Based Lookup Service
=======================

Enhanced lookup service that prioritizes ID-based operations over name matching.
Provides robust resolution of series_id, team_id, club_id, and league_id for ETL processes.

Key Features:
- ID-first strategy with name-based fallbacks
- Comprehensive caching for performance
- Context-aware lookups (league-specific)
- Validation and error handling
- Detailed logging for troubleshooting

Usage:
    lookup_service = IdBasedLookupService()
    team_id = lookup_service.resolve_team_id(
        team_name="Tennaqua 12", 
        league_id="CNSWPL",
        series_name="Series 12",
        club_name="Tennaqua"
    )
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple, List, Union
from dataclasses import dataclass
import sys
import os
from pathlib import Path

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = Path(script_dir).parent.parent.parent
sys.path.insert(0, str(project_root))

from database_utils import execute_query, execute_query_one

logger = logging.getLogger(__name__)


@dataclass
class ResolvedIds:
    """Container for resolved database IDs"""
    league_id: Optional[str] = None
    league_db_id: Optional[int] = None
    series_id: Optional[int] = None
    series_name: Optional[str] = None
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    club_id: Optional[int] = None
    club_name: Optional[str] = None
    
    def is_complete(self) -> bool:
        """Check if all essential IDs are resolved"""
        return all([
            self.league_db_id,
            self.series_id,
            self.team_id,
            self.club_id
        ])


class IdBasedLookupService:
    """Enhanced lookup service prioritizing ID-based operations"""
    
    def __init__(self):
        self.cache = {
            'leagues': {},      # league_id -> league_db_id
            'series': {},       # (league_db_id, series_name) -> series_id
            'teams': {},        # (league_db_id, team_name) -> team_id
            'clubs': {},        # club_name -> club_id
            'team_context': {}, # team_id -> full context
            'series_teams': {}  # (league_db_id, series_id) -> list of team_ids
        }
        self._cache_loaded = False
        
    def _ensure_cache_loaded(self):
        """Load all lookup caches from database"""
        if self._cache_loaded:
            return
            
        logger.info("🔧 Loading ID-based lookup caches...")
        
        try:
            # Load league mappings
            leagues = execute_query("SELECT league_id, id FROM leagues")
            self.cache['leagues'] = {row['league_id']: row['id'] for row in leagues}
            
            # Load series mappings with league context
            series_query = """
                SELECT l.id as league_db_id, s.name as series_name, s.id as series_id
                FROM series s
                JOIN series_leagues sl ON s.id = sl.series_id
                JOIN leagues l ON sl.league_id = l.id
            """
            series_data = execute_query(series_query)
            for row in series_data:
                key = (row['league_db_id'], row['series_name'])
                self.cache['series'][key] = row['series_id']
            
            # Load team mappings with full context
            teams_query = """
                SELECT t.id, t.team_name, t.league_id, t.series_id, t.club_id,
                       l.league_id as league_string, s.name as series_name, c.name as club_name
                FROM teams t
                JOIN leagues l ON t.league_id = l.id
                LEFT JOIN series s ON t.series_id = s.id
                LEFT JOIN clubs c ON t.club_id = c.id
            """
            teams_data = execute_query(teams_query)
            for row in teams_data:
                # Cache by (league_db_id, team_name)
                team_key = (row['league_id'], row['team_name'])
                self.cache['teams'][team_key] = row['id']
                
                # Cache full context by team_id
                self.cache['team_context'][row['id']] = {
                    'team_name': row['team_name'],
                    'league_db_id': row['league_id'],
                    'league_string': row['league_string'],
                    'series_id': row['series_id'],
                    'series_name': row['series_name'],
                    'club_id': row['club_id'],
                    'club_name': row['club_name']
                }
                
                # Cache teams by series
                series_key = (row['league_id'], row['series_id'])
                if series_key not in self.cache['series_teams']:
                    self.cache['series_teams'][series_key] = []
                self.cache['series_teams'][series_key].append(row['id'])
            
            # Load club mappings
            clubs = execute_query("SELECT name, id FROM clubs")
            self.cache['clubs'] = {row['name']: row['id'] for row in clubs}
            
            self._cache_loaded = True
            logger.info(f"✅ Loaded caches: {len(self.cache['leagues'])} leagues, "
                       f"{len(self.cache['series'])} series, {len(self.cache['teams'])} teams, "
                       f"{len(self.cache['clubs'])} clubs")
            
        except Exception as e:
            logger.error(f"❌ Error loading lookup caches: {e}")
            raise
    
    def resolve_league_db_id(self, league_id: str) -> Optional[int]:
        """Resolve league string ID to database integer ID"""
        self._ensure_cache_loaded()
        
        # Direct lookup
        league_db_id = self.cache['leagues'].get(league_id)
        if league_db_id:
            logger.debug(f"✅ League resolved: '{league_id}' -> {league_db_id}")
            return league_db_id
        
        # Try normalization fallbacks
        from utils.league_utils import normalize_league_id
        normalized = normalize_league_id(league_id)
        if normalized != league_id:
            league_db_id = self.cache['leagues'].get(normalized)
            if league_db_id:
                logger.debug(f"✅ League resolved via normalization: '{league_id}' -> '{normalized}' -> {league_db_id}")
                return league_db_id
        
        logger.warning(f"❌ League not found: '{league_id}'")
        return None
    
    def resolve_series_id(self, series_name: str, league_id: str) -> Optional[int]:
        """Resolve series name to database ID within league context"""
        self._ensure_cache_loaded()
        
        league_db_id = self.resolve_league_db_id(league_id)
        if not league_db_id:
            return None
        
        # Direct lookup with league context
        series_key = (league_db_id, series_name)
        series_id = self.cache['series'].get(series_key)
        if series_id:
            logger.debug(f"✅ Series resolved: '{series_name}' in {league_id} -> {series_id}")
            return series_id
        
        logger.warning(f"❌ Series not found: '{series_name}' in league '{league_id}'")
        return None
    
    def resolve_club_id(self, club_name: str, fuzzy_match: bool = True) -> Optional[int]:
        """Resolve club name to database ID with optional fuzzy matching"""
        self._ensure_cache_loaded()
        
        # Direct lookup
        club_id = self.cache['clubs'].get(club_name)
        if club_id:
            logger.debug(f"✅ Club resolved: '{club_name}' -> {club_id}")
            return club_id
        
        if fuzzy_match:
            # Try fuzzy matching for common variations
            import re
            
            # Pattern 1: Remove numbers and suffixes (e.g., "Lake Shore CC 11" -> "Lake Shore CC")
            base_club_name = re.sub(r'\s+\d+.*$', '', club_name).strip()
            if base_club_name != club_name:
                club_id = self.cache['clubs'].get(base_club_name)
                if club_id:
                    logger.debug(f"✅ Club resolved via base name: '{club_name}' -> '{base_club_name}' -> {club_id}")
                    return club_id
            
            # Pattern 2: Handle special cases and CNSWPL partial names
            special_mappings = {
                'LifeSport-Lshire': 'LifeSport',
                'Park RIdge CC': 'Park Ridge CC',
                # CNSWPL partial club name mappings (fix for scraper issue)
                'Michigan': 'Michigan Shores',
                'River': 'River Forest', 
                'Barrington': 'Barrington Hills',
                'Lake': 'Lake Forest',  # Primary mapping for Lake
                'Sunset': 'Sunset Ridge',
                'Prairie': 'Prairie Club',
                'Hinsdale': 'Hinsdale PC',
                'Park': 'Park Ridge CC',
                'Indian': 'Indian Hill',
                'Bryn': 'Bryn Mawr CC',
                'Saddle': 'Saddle & Cycle',
                'Valley': 'Valley Lo',
                'North': 'North Shore'
            }
            
            for pattern, replacement in special_mappings.items():
                if club_name.startswith(pattern) or club_name == pattern:
                    club_id = self.cache['clubs'].get(replacement)
                    if club_id:
                        logger.debug(f"✅ Club resolved via special mapping: '{club_name}' -> '{replacement}' -> {club_id}")
                        return club_id
                    
                    # Special case for "Lake" - try Lake Bluff if Lake Forest fails
                    if club_name == 'Lake' and replacement == 'Lake Forest':
                        club_id = self.cache['clubs'].get('Lake Bluff')
                        if club_id:
                            logger.debug(f"✅ Club resolved via Lake Bluff fallback: '{club_name}' -> 'Lake Bluff' -> {club_id}")
                            return club_id
        
        logger.warning(f"❌ Club not found: '{club_name}'")
        return None
    
    def resolve_team_id(self, team_name: str, league_id: str, 
                       series_name: Optional[str] = None, 
                       club_name: Optional[str] = None) -> Optional[int]:
        """Resolve team name to database ID with multiple fallback strategies"""
        self._ensure_cache_loaded()
        
        league_db_id = self.resolve_league_db_id(league_id)
        if not league_db_id:
            return None
        
        # Strategy 1: Direct team name lookup
        team_key = (league_db_id, team_name)
        team_id = self.cache['teams'].get(team_key)
        if team_id:
            logger.debug(f"✅ Team resolved directly: '{team_name}' in {league_id} -> {team_id}")
            return team_id
        
        # Strategy 2: Series + Club context matching
        if series_name and club_name:
            series_id = self.resolve_series_id(series_name, league_id)
            
            # CNSWPL Fix: Handle Division X -> Series X mapping
            if not series_id and league_id.upper() == 'CNSWPL' and series_name.startswith('Division '):
                mapped_series_name = series_name.replace('Division ', 'Series ')
                series_id = self.resolve_series_id(mapped_series_name, league_id)
                if series_id:
                    logger.debug(f"✅ CNSWPL series mapping: '{series_name}' -> '{mapped_series_name}' (ID: {series_id})")
            
            club_id = self.resolve_club_id(club_name)
            
            if series_id and club_id:
                # Find team by series + club combination
                for team_id, context in self.cache['team_context'].items():
                    if (context['league_db_id'] == league_db_id and 
                        context['series_id'] == series_id and 
                        context['club_id'] == club_id):
                        logger.debug(f"✅ Team resolved via series+club context: "
                                   f"'{team_name}' -> {team_id} ({context['team_name']})")
                        return team_id
        
        logger.warning(f"❌ Team not found: '{team_name}' in league '{league_id}'")
        return None
    
    def resolve_all_ids(self, league_id: str, series_name: str, 
                       team_name: str, club_name: str) -> ResolvedIds:
        """Resolve all IDs for a complete player record"""
        self._ensure_cache_loaded()
        
        result = ResolvedIds()
        
        # Resolve league
        result.league_id = league_id
        result.league_db_id = self.resolve_league_db_id(league_id)
        
        if not result.league_db_id:
            logger.warning(f"Cannot resolve any IDs without valid league: {league_id}")
            return result
        
        # Resolve series
        result.series_name = series_name
        result.series_id = self.resolve_series_id(series_name, league_id)
        
        # CNSWPL Fix: Handle Division X -> Series X mapping
        if not result.series_id and league_id.upper() == 'CNSWPL' and series_name.startswith('Division '):
            mapped_series_name = series_name.replace('Division ', 'Series ')
            result.series_id = self.resolve_series_id(mapped_series_name, league_id)
            if result.series_id:
                logger.debug(f"✅ CNSWPL series mapping in resolve_all_ids: '{series_name}' -> '{mapped_series_name}' (ID: {result.series_id})")
                result.series_name = mapped_series_name  # Update to mapped name
        
        # Resolve club
        result.club_name = club_name
        result.club_id = self.resolve_club_id(club_name)
        
        # Resolve team
        result.team_name = team_name
        result.team_id = self.resolve_team_id(team_name, league_id, series_name, club_name)
        
        logger.debug(f"✅ Resolved IDs for '{team_name}': "
                    f"league_db_id={result.league_db_id}, series_id={result.series_id}, "
                    f"team_id={result.team_id}, club_id={result.club_id}")
        
        return result
    
    def get_team_context(self, team_id: int) -> Optional[Dict]:
        """Get full context for a team ID"""
        self._ensure_cache_loaded()
        return self.cache['team_context'].get(team_id)
    
    def get_teams_in_series(self, league_id: str, series_name: str) -> List[int]:
        """Get all team IDs in a specific series"""
        self._ensure_cache_loaded()
        
        league_db_id = self.resolve_league_db_id(league_id)
        series_id = self.resolve_series_id(series_name, league_id)
        
        if league_db_id and series_id:
            series_key = (league_db_id, series_id)
            return self.cache['series_teams'].get(series_key, [])
        
        return []
    
    def validate_consistency(self, resolved_ids: ResolvedIds) -> bool:
        """Validate that resolved IDs are consistent with each other"""
        if not resolved_ids.is_complete():
            return False
        
        # Get team context and verify consistency
        team_context = self.get_team_context(resolved_ids.team_id)
        if not team_context:
            logger.warning(f"Team context not found for team_id {resolved_ids.team_id}")
            return False
        
        # Check consistency
        inconsistencies = []
        
        if team_context['league_db_id'] != resolved_ids.league_db_id:
            inconsistencies.append(f"League DB ID mismatch: {team_context['league_db_id']} vs {resolved_ids.league_db_id}")
        
        if team_context['series_id'] != resolved_ids.series_id:
            inconsistencies.append(f"Series ID mismatch: {team_context['series_id']} vs {resolved_ids.series_id}")
        
        if team_context['club_id'] != resolved_ids.club_id:
            inconsistencies.append(f"Club ID mismatch: {team_context['club_id']} vs {resolved_ids.club_id}")
        
        if inconsistencies:
            logger.error(f"❌ ID consistency validation failed: {'; '.join(inconsistencies)}")
            return False
        
        logger.debug(f"✅ ID consistency validated for team_id {resolved_ids.team_id}")
        return True


def main():
    """Test the ID-based lookup service"""
    import sys
    
    if len(sys.argv) < 5:
        print("Usage: python id_based_lookup_service.py <league_id> <series_name> <team_name> <club_name>")
        print("Example: python id_based_lookup_service.py CNSWPL 'Series 12' 'Tennaqua 12' 'Tennaqua'")
        sys.exit(1)
    
    league_id, series_name, team_name, club_name = sys.argv[1:5]
    
    # Test the lookup service
    lookup_service = IdBasedLookupService()
    
    print(f"Testing ID resolution for:")
    print(f"  League: {league_id}")
    print(f"  Series: {series_name}")
    print(f"  Team: {team_name}")
    print(f"  Club: {club_name}")
    print()
    
    # Resolve all IDs
    resolved_ids = lookup_service.resolve_all_ids(league_id, series_name, team_name, club_name)
    
    print("Resolved IDs:")
    print(f"  League DB ID: {resolved_ids.league_db_id}")
    print(f"  Series ID: {resolved_ids.series_id}")
    print(f"  Team ID: {resolved_ids.team_id}")
    print(f"  Club ID: {resolved_ids.club_id}")
    print()
    
    print(f"Complete: {resolved_ids.is_complete()}")
    
    if resolved_ids.is_complete():
        print(f"Consistent: {lookup_service.validate_consistency(resolved_ids)}")
        
        # Show team context
        team_context = lookup_service.get_team_context(resolved_ids.team_id)
        if team_context:
            print(f"\nTeam Context:")
            for key, value in team_context.items():
                print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
