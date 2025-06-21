#!/usr/bin/env python3

"""
Series Name Mapping Service

Provides scalable, database-driven series name mapping for all leagues.
This replaces hardcoded mapping logic and supports easy addition of new leagues.
"""

from database_utils import execute_query_one
import re
from typing import Optional, Tuple

class SeriesMappingService:
    """Service for mapping user-facing series names to database series names"""
    
    def __init__(self):
        self._cache = {}  # Cache mappings for performance
    
    def get_mapped_series_name(self, league_id: str, user_series_name: str) -> Optional[str]:
        """
        Get the database series name for a given user series name and league.
        
        Args:
            league_id: League identifier (e.g., 'NSTF', 'CNSWPL')
            user_series_name: Series name from user session/data
            
        Returns:
            Database series name if mapping exists, None otherwise
        """
        cache_key = f"{league_id}:{user_series_name}"
        
        # Check cache first
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Query database for mapping
        mapping_query = """
            SELECT database_series_name 
            FROM series_name_mappings 
            WHERE league_id = %s AND user_series_name = %s
        """
        
        try:
            result = execute_query_one(mapping_query, [league_id, user_series_name])
            if result:
                mapped_name = result['database_series_name']
                self._cache[cache_key] = mapped_name
                return mapped_name
                
        except Exception as e:
            print(f"[SERIES_MAPPING] Database query failed: {e}")
        
        # Cache negative results to avoid repeated queries
        self._cache[cache_key] = None
        return None
    
    def find_team_with_mapping(self, club: str, user_series: str, league_id: str, league_db_id: int) -> Optional[dict]:
        """
        Find a team using series name mapping if direct lookup fails.
        
        Args:
            club: Club name
            user_series: User's series name
            league_id: League identifier (e.g., 'NSTF')
            league_db_id: League database ID
            
        Returns:
            Team record if found, None otherwise
        """
        from database_utils import execute_query_one
        
        # First try direct lookup
        team_query = """
            SELECT t.id, t.team_name
            FROM teams t
            JOIN clubs c ON t.club_id = c.id
            JOIN series s ON t.series_id = s.id
            JOIN leagues l ON t.league_id = l.id
            WHERE c.name = %s 
            AND s.name = %s 
            AND l.id = %s
        """
        
        try:
            # Try direct lookup first
            team_record = execute_query_one(team_query, [club, user_series, league_db_id])
            if team_record:
                return team_record
            
            # Try with mapped series name
            mapped_series = self.get_mapped_series_name(league_id, user_series)
            if mapped_series:
                print(f"[SERIES_MAPPING] {league_id} mapping: '{user_series}' -> '{mapped_series}'")
                team_record = execute_query_one(team_query, [club, mapped_series, league_db_id])
                if team_record:
                    print(f"[SERIES_MAPPING] Found team with mapped series: {team_record['team_name']}")
                    return team_record
            
        except Exception as e:
            print(f"[SERIES_MAPPING] Team lookup failed: {e}")
        
        return None
    
    def add_mapping(self, league_id: str, user_series_name: str, database_series_name: str) -> bool:
        """
        Add a new series name mapping (useful for new leagues).
        
        Args:
            league_id: League identifier
            user_series_name: User-facing series name
            database_series_name: Database series name
            
        Returns:
            True if mapping was added successfully
        """
        from database_utils import execute_update
        
        insert_query = """
            INSERT INTO series_name_mappings (league_id, user_series_name, database_series_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (league_id, user_series_name) 
            DO UPDATE SET 
                database_series_name = EXCLUDED.database_series_name,
                updated_at = CURRENT_TIMESTAMP
        """
        
        try:
            execute_update(insert_query, [league_id, user_series_name, database_series_name])
            # Update cache
            cache_key = f"{league_id}:{user_series_name}"
            self._cache[cache_key] = database_series_name
            print(f"[SERIES_MAPPING] Added mapping: {league_id} '{user_series_name}' -> '{database_series_name}'")
            return True
        except Exception as e:
            print(f"[SERIES_MAPPING] Failed to add mapping: {e}")
            return False
    
    def get_all_mappings_for_league(self, league_id: str) -> list:
        """Get all series mappings for a specific league"""
        from database_utils import execute_query
        
        query = """
            SELECT user_series_name, database_series_name, created_at, updated_at
            FROM series_name_mappings 
            WHERE league_id = %s
            ORDER BY user_series_name
        """
        
        try:
            return execute_query(query, [league_id])
        except Exception as e:
            print(f"[SERIES_MAPPING] Failed to get mappings for {league_id}: {e}")
            return []
    
    def auto_detect_mapping_pattern(self, league_id: str) -> dict:
        """
        Auto-detect series naming patterns for a league by analyzing existing data.
        Useful when adding new leagues.
        """
        from database_utils import execute_query
        
        # Get all series names for the league from teams data
        query = """
            SELECT DISTINCT s.name as series_name, COUNT(t.id) as team_count
            FROM series s
            JOIN series_leagues sl ON s.id = sl.series_id
            JOIN leagues l ON sl.league_id = l.id
            JOIN teams t ON t.series_id = s.id
            WHERE l.league_id = %s
            GROUP BY s.name
            ORDER BY s.name
        """
        
        try:
            series_data = execute_query(query, [league_id])
            
            # Analyze patterns
            patterns = {
                'series_count': len(series_data),
                'naming_patterns': [],
                'suggestions': []
            }
            
            for series in series_data:
                name = series['series_name']
                
                # Detect common patterns
                if re.match(r'^S\d+[A-Z]*$', name):  # S1, S2A, S2B pattern (NSTF)
                    patterns['naming_patterns'].append(f"Short format: {name}")
                elif re.match(r'^Series \d+[A-Z]*$', name):  # Series 1, Series 2A pattern
                    patterns['naming_patterns'].append(f"Long format: {name}")
                elif re.match(r'^Division \d+[A-Z]*$', name):  # Division 1, Division 2A pattern
                    patterns['naming_patterns'].append(f"Division format: {name}")
                elif re.match(r'^Chicago \d+', name):  # Chicago 30, Chicago 4.0 pattern
                    patterns['naming_patterns'].append(f"Location format: {name}")
                else:
                    patterns['naming_patterns'].append(f"Custom format: {name}")
            
            return patterns
            
        except Exception as e:
            print(f"[SERIES_MAPPING] Pattern detection failed for {league_id}: {e}")
            return {'error': str(e)}
    
    def clear_cache(self):
        """Clear the mapping cache (useful after adding new mappings)"""
        self._cache.clear()
        print("[SERIES_MAPPING] Cache cleared")


# Global instance for easy use throughout the application
series_mapper = SeriesMappingService()


def get_series_mapper():
    """Get the global series mapper instance"""
    return series_mapper


# Convenience functions for common operations
def map_series_name(league_id: str, user_series_name: str) -> Optional[str]:
    """Convenience function to map a series name"""
    return series_mapper.get_mapped_series_name(league_id, user_series_name)


def find_team_with_series_mapping(club: str, user_series: str, league_id: str, league_db_id: int) -> Optional[dict]:
    """Convenience function to find team with series mapping"""
    return series_mapper.find_team_with_mapping(club, user_series, league_id, league_db_id)


def add_league_mapping(league_id: str, user_series_name: str, database_series_name: str) -> bool:
    """Convenience function to add a new mapping"""
    return series_mapper.add_mapping(league_id, user_series_name, database_series_name) 