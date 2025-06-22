#!/usr/bin/env python3

"""
Comprehensive Team Format Mapping Service

Provides scalable, database-driven team format mapping for all leagues.
This replaces hardcoded mapping logic and supports easy addition of new leagues.

Updated to use the comprehensive team_format_mappings table.
"""

import re
from typing import Optional, Tuple

from database_utils import execute_query, execute_query_one, execute_update


class ComprehensiveTeamFormatMappingService:
    """Service for mapping user-facing team/series formats to database formats"""

    def __init__(self):
        self._cache = {}  # Cache mappings for performance

    def get_mapped_series_name(
        self, league_id: str, user_series_name: str
    ) -> Optional[str]:
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

        # Query database for mapping using new comprehensive table
        mapping_query = """
            SELECT database_series_format 
            FROM team_format_mappings 
            WHERE league_id = %s AND user_input_format = %s AND is_active = true
        """

        try:
            result = execute_query_one(mapping_query, [league_id, user_series_name])
            if result:
                mapped_name = result["database_series_format"]
                self._cache[cache_key] = mapped_name
                return mapped_name

        except Exception as e:
            print(f"[TEAM_FORMAT_MAPPING] Database query failed: {e}")

        # Cache negative results to avoid repeated queries
        self._cache[cache_key] = None
        return None

    def find_team_with_mapping(
        self, club: str, user_series: str, league_id: str, league_db_id: int
    ) -> Optional[dict]:
        """
        Find a team using comprehensive format mapping if direct lookup fails.

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
            team_record = execute_query_one(
                team_query, [club, user_series, league_db_id]
            )
            if team_record:
                print(
                    f"[TEAM_FORMAT_MAPPING] Direct match found: {team_record['team_name']}"
                )
                return team_record

            # Try with mapped series name using new comprehensive table
            mapped_series = self.get_mapped_series_name(league_id, user_series)
            if mapped_series:
                print(
                    f"[TEAM_FORMAT_MAPPING] {league_id} mapping: '{user_series}' -> '{mapped_series}'"
                )
                team_record = execute_query_one(
                    team_query, [club, mapped_series, league_db_id]
                )
                if team_record:
                    print(
                        f"[TEAM_FORMAT_MAPPING] Found team with mapped series: {team_record['team_name']}"
                    )
                    return team_record

            # If no specific mapping found, try fuzzy matching with all possible formats
            print(
                f"[TEAM_FORMAT_MAPPING] No direct mapping found, trying fuzzy matching..."
            )
            fuzzy_result = self._try_fuzzy_matching(
                club, user_series, league_id, league_db_id
            )
            if fuzzy_result:
                return fuzzy_result

        except Exception as e:
            print(f"[TEAM_FORMAT_MAPPING] Team lookup failed: {e}")

        return None

    def _try_fuzzy_matching(
        self, club: str, user_series: str, league_id: str, league_db_id: int
    ) -> Optional[dict]:
        """
        Try fuzzy matching by looking for partial matches in series names.
        """
        try:
            # Get all possible mappings for this league
            all_mappings_query = """
                SELECT user_input_format, database_series_format
                FROM team_format_mappings
                WHERE league_id = %s AND is_active = true
                ORDER BY LENGTH(user_input_format) DESC
            """

            all_mappings = execute_query(all_mappings_query, [league_id])

            # Try each mapping to see if user input contains the pattern
            for mapping in all_mappings:
                user_format = mapping["user_input_format"]
                db_format = mapping["database_series_format"]

                # Check if user series contains the user format (case insensitive)
                if (
                    user_format.lower() in user_series.lower()
                    or user_series.lower() in user_format.lower()
                ):
                    print(
                        f"[TEAM_FORMAT_MAPPING] Fuzzy match: '{user_series}' contains '{user_format}' -> '{db_format}'"
                    )

                    # Try this mapping
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

                    team_record = execute_query_one(
                        team_query, [club, db_format, league_db_id]
                    )
                    if team_record:
                        print(
                            f"[TEAM_FORMAT_MAPPING] Fuzzy match success: {team_record['team_name']}"
                        )
                        return team_record

        except Exception as e:
            print(f"[TEAM_FORMAT_MAPPING] Fuzzy matching failed: {e}")

        return None

    def add_mapping(
        self,
        league_id: str,
        user_input_format: str,
        database_series_format: str,
        description: str = None,
    ) -> bool:
        """
        Add a new team format mapping (useful for new leagues).

        Args:
            league_id: League identifier
            user_input_format: User-facing format
            database_series_format: Database format
            description: Optional description

        Returns:
            True if mapping was added successfully
        """
        insert_query = """
            INSERT INTO team_format_mappings (league_id, user_input_format, database_series_format, description)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (league_id, user_input_format) 
            DO UPDATE SET 
                database_series_format = EXCLUDED.database_series_format,
                description = EXCLUDED.description,
                updated_at = CURRENT_TIMESTAMP
        """

        try:
            execute_update(
                insert_query,
                [league_id, user_input_format, database_series_format, description],
            )
            # Update cache
            cache_key = f"{league_id}:{user_input_format}"
            self._cache[cache_key] = database_series_format
            print(
                f"[TEAM_FORMAT_MAPPING] Added mapping: {league_id} '{user_input_format}' -> '{database_series_format}'"
            )
            return True
        except Exception as e:
            print(f"[TEAM_FORMAT_MAPPING] Failed to add mapping: {e}")
            return False

    def get_all_mappings_for_league(self, league_id: str) -> list:
        """Get all team format mappings for a specific league"""
        query = """
            SELECT user_input_format, database_series_format, description, created_at, updated_at
            FROM team_format_mappings 
            WHERE league_id = %s AND is_active = true
            ORDER BY user_input_format
        """

        try:
            return execute_query(query, [league_id])
        except Exception as e:
            print(f"[TEAM_FORMAT_MAPPING] Failed to get mappings for {league_id}: {e}")
            return []

    def auto_detect_mapping_pattern(self, league_id: str) -> dict:
        """
        Auto-detect series naming patterns for a league by analyzing existing data.
        Useful when adding new leagues.
        """
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

            # Get existing mappings
            existing_mappings = self.get_all_mappings_for_league(league_id)
            mapped_formats = {m["database_series_format"] for m in existing_mappings}

            # Analyze patterns
            patterns = {
                "series_count": len(series_data),
                "existing_mappings": len(existing_mappings),
                "unmapped_series": [],
                "naming_patterns": [],
                "suggestions": [],
            }

            for series in series_data:
                name = series["series_name"]

                if name not in mapped_formats:
                    patterns["unmapped_series"].append(name)

                # Detect common patterns
                if re.match(r"^S\d+[A-Z]*$", name):  # S1, S2A, S2B pattern (NSTF)
                    patterns["naming_patterns"].append(f"Short format: {name}")
                elif re.match(
                    r"^Series \d+[A-Z]*$", name
                ):  # Series 1, Series 2A pattern
                    patterns["naming_patterns"].append(f"Long format: {name}")
                elif re.match(
                    r"^Division \d+[A-Z]*$", name
                ):  # Division 1, Division 2A pattern
                    patterns["naming_patterns"].append(f"Division format: {name}")
                elif re.match(r"^Chicago \d+", name):  # Chicago 30, Chicago 4.0 pattern
                    patterns["naming_patterns"].append(f"Location format: {name}")
                else:
                    patterns["naming_patterns"].append(f"Custom format: {name}")

            return patterns

        except Exception as e:
            print(
                f"[TEAM_FORMAT_MAPPING] Pattern detection failed for {league_id}: {e}"
            )
            return {"error": str(e)}

    def clear_cache(self):
        """Clear the mapping cache (useful after adding new mappings)"""
        self._cache.clear()
        print("[TEAM_FORMAT_MAPPING] Cache cleared")

    def debug_lookup(
        self, club: str, user_series: str, league_id: str, league_db_id: int
    ) -> dict:
        """
        Debug function to show all steps of the lookup process.
        """
        debug_info = {
            "input": {
                "club": club,
                "user_series": user_series,
                "league_id": league_id,
                "league_db_id": league_db_id,
            },
            "steps": [],
            "result": None,
        }

        # Step 1: Direct lookup
        debug_info["steps"].append("Step 1: Direct series lookup")
        try:
            team_query = """
                SELECT t.id, t.team_name
                FROM teams t
                JOIN clubs c ON t.club_id = c.id
                JOIN series s ON t.series_id = s.id
                JOIN leagues l ON t.league_id = l.id
                WHERE c.name = %s AND s.name = %s AND l.id = %s
            """
            direct_result = execute_query_one(
                team_query, [club, user_series, league_db_id]
            )
            if direct_result:
                debug_info["steps"].append(
                    f"✅ Direct match found: {direct_result['team_name']}"
                )
                debug_info["result"] = direct_result
                return debug_info
            else:
                debug_info["steps"].append("❌ No direct match found")
        except Exception as e:
            debug_info["steps"].append(f"❌ Direct lookup error: {e}")

        # Step 2: Mapped lookup
        debug_info["steps"].append("Step 2: Mapped series lookup")
        mapped_series = self.get_mapped_series_name(league_id, user_series)
        if mapped_series:
            debug_info["steps"].append(
                f"✅ Found mapping: '{user_series}' -> '{mapped_series}'"
            )
            try:
                mapped_result = execute_query_one(
                    team_query, [club, mapped_series, league_db_id]
                )
                if mapped_result:
                    debug_info["steps"].append(
                        f"✅ Mapped match found: {mapped_result['team_name']}"
                    )
                    debug_info["result"] = mapped_result
                    return debug_info
                else:
                    debug_info["steps"].append("❌ No team found with mapped series")
            except Exception as e:
                debug_info["steps"].append(f"❌ Mapped lookup error: {e}")
        else:
            debug_info["steps"].append("❌ No mapping found")

        # Step 3: Show available series for this league
        debug_info["steps"].append("Step 3: Available series in this league")
        try:
            available_query = """
                SELECT DISTINCT s.name
                FROM series s
                JOIN teams t ON t.series_id = s.id
                JOIN leagues l ON t.league_id = l.id
                WHERE l.id = %s
                ORDER BY s.name
            """
            available_series = execute_query(available_query, [league_db_id])
            debug_info["steps"].append(
                f"Available series: {[s['name'] for s in available_series]}"
            )
        except Exception as e:
            debug_info["steps"].append(f"❌ Error getting available series: {e}")

        return debug_info


# Global instance
_comprehensive_team_format_mapper = ComprehensiveTeamFormatMappingService()


def get_comprehensive_team_format_mapper():
    """Get the global comprehensive team format mapper instance"""
    return _comprehensive_team_format_mapper


def find_team_with_series_mapping(
    club: str, series: str, league_id: str, league_db_id: int
) -> Optional[dict]:
    """Convenience function to find team with comprehensive mapping"""
    return _comprehensive_team_format_mapper.find_team_with_mapping(
        club, series, league_id, league_db_id
    )


def add_team_format_mapping(
    league_id: str,
    user_input_format: str,
    database_series_format: str,
    description: str = None,
) -> bool:
    """Convenience function to add a new mapping"""
    return _comprehensive_team_format_mapper.add_mapping(
        league_id, user_input_format, database_series_format, description
    )


def debug_team_lookup(
    club: str, series: str, league_id: str, league_db_id: int
) -> dict:
    """Convenience function to debug team lookup"""
    return _comprehensive_team_format_mapper.debug_lookup(
        club, series, league_id, league_db_id
    )


# Backward compatibility - keep the old function names but use new service
def get_series_mapper():
    """Backward compatibility function"""
    return _comprehensive_team_format_mapper


# Legacy SeriesMappingService class for backward compatibility
class SeriesMappingService(ComprehensiveTeamFormatMappingService):
    """Legacy class name for backward compatibility"""

    pass
