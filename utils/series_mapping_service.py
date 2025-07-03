#!/usr/bin/env python3

"""
Simplified Series Mapping Service
===============================

Uses the series.display_name column for UI display when available, 
keeping the original name for database operations.
Handles cases where display_name column doesn't exist (backward compatibility).
"""

from typing import Optional
from database_utils import execute_query_one


# Global cache for column existence check
_HAS_DISPLAY_NAME_COLUMN = None


def _check_display_name_column_exists() -> bool:
    """
    Check if the display_name column exists in the series table.
    Cache the result to avoid repeated checks.
    """
    global _HAS_DISPLAY_NAME_COLUMN
    
    if _HAS_DISPLAY_NAME_COLUMN is not None:
        return _HAS_DISPLAY_NAME_COLUMN
        
    try:
        query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'series' 
            AND column_name = 'display_name'
        """
        
        result = execute_query_one(query, [])
        _HAS_DISPLAY_NAME_COLUMN = bool(result)
        
    except Exception as e:
        print(f"[SERIES_MAPPING] Error checking display_name column: {e}")
        _HAS_DISPLAY_NAME_COLUMN = False
        
    return _HAS_DISPLAY_NAME_COLUMN


class SeriesMappingService:
    """
    Simplified series mapping service that uses the display_name column when available.
    """

    @staticmethod
    def get_display_name(series_name: str) -> str:
        """
        Get the display name for a series from the database.
        Falls back to original name if display_name column doesn't exist.
        
        Args:
            series_name: Database series name
            
        Returns:
            Display name for UI
        """
        if not series_name:
            return ""
            
        if not _check_display_name_column_exists():
            print(f"[SERIES_MAPPING] display_name column not found, using original name: {series_name}")
            return series_name
            
        try:
            query = """
                SELECT display_name 
                FROM series 
                WHERE name = %s
                LIMIT 1
            """
            
            result = execute_query_one(query, [series_name])
            
            if result and result["display_name"]:
                return result["display_name"]
                
        except Exception as e:
            print(f"[SERIES_MAPPING] Error getting display name: {e}")
            
        return series_name  # Fallback to database name
    
    @staticmethod
    def get_database_name(display_name: str) -> Optional[str]:
        """
        Get the database name for a display name.
        Falls back to direct matching if display_name column doesn't exist.
        
        Args:
            display_name: UI display name
            
        Returns:
            Database series name if found, None otherwise
        """
        if not display_name:
            return None
            
        if not _check_display_name_column_exists():
            print(f"[SERIES_MAPPING] display_name column not found, trying direct name match for: {display_name}")
            # When display_name column doesn't exist, try direct name matching
            try:
                query = """
                    SELECT name 
                    FROM series 
                    WHERE name = %s
                    LIMIT 1
                """
                
                result = execute_query_one(query, [display_name])
                
                if result:
                    return result["name"]
                    
            except Exception as e:
                print(f"[SERIES_MAPPING] Error with direct name match: {e}")
                
            return display_name  # Return as-is if no exact match found
            
        try:
            query = """
                SELECT name 
                FROM series 
                WHERE display_name = %s
                LIMIT 1
            """
            
            result = execute_query_one(query, [display_name])
            
            if result:
                return result["name"]
                
        except Exception as e:
            print(f"[SERIES_MAPPING] Error getting database name: {e}")
            
        return None
    
    @staticmethod
    def series_match(series1: str, series2: str) -> bool:
        """
        Check if two series names refer to the same series.
        Compares either database names or display names when available.
        
        Args:
            series1: First series name
            series2: Second series name
            
        Returns:
            True if they represent the same series
        """
        if not series1 or not series2:
            return False
            
        try:
            # Try exact match first
            if series1 == series2:
                return True
                
            if not _check_display_name_column_exists():
                # When display_name column doesn't exist, only exact matching is possible
                return False
                
            # Check if either is a database name matching the other's display name
            query = """
                SELECT 1 
                FROM series 
                WHERE (name = %s AND display_name = %s)
                   OR (name = %s AND display_name = %s)
                LIMIT 1
            """
            
            result = execute_query_one(query, [series1, series2, series2, series1])
            
            return bool(result)
            
        except Exception as e:
            print(f"[SERIES_MAPPING] Error comparing series: {e}")
            return False


# Singleton instance for easy importing
series_mapper = SeriesMappingService()

# Backward compatibility functions
def get_display_name(series_name: str) -> str:
    """Backward compatibility function"""
    return series_mapper.get_display_name(series_name)

def get_database_name(display_name: str) -> Optional[str]:
    """Backward compatibility function"""
    return series_mapper.get_database_name(display_name)

def series_match(series1: str, series2: str) -> bool:
    """Backward compatibility function"""
    return series_mapper.series_match(series1, series2)
