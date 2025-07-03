#!/usr/bin/env python3

"""
Simplified Series Mapping Service
===============================

Uses the series.display_name column for UI display, keeping the original name for database operations.
No more complex mapping table or transformations needed.
"""

from typing import Optional
from database_utils import execute_query_one


class SeriesMappingService:
    """
    Simplified series mapping service that uses the display_name column.
    """

    @staticmethod
    def get_display_name(series_name: str) -> str:
        """
        Get the display name for a series from the database.
        
        Args:
            series_name: Database series name
            
        Returns:
            Display name for UI
        """
        if not series_name:
            return ""
            
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
        
        Args:
            display_name: UI display name
            
        Returns:
            Database series name if found, None otherwise
        """
        if not display_name:
            return None
            
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
        Compares either database names or display names.
        
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
