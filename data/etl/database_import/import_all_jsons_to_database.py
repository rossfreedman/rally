#!/usr/bin/env python3
"""
Comprehensive ETL Script for JSON Data Import
===========================================

This script imports data from JSON files in data/leagues/all/ into the PostgreSQL database
in the correct order based on foreign key constraints.

Order of operations:
1. Extract leagues from players.json -> import to leagues table
2. Extract clubs from players.json -> import to clubs table
3. Extract series from players.json -> import to series table
4. Analyze club-league relationships -> populate club_leagues table
5. Analyze series-league relationships -> populate series_leagues table
6. Import players.json -> players table
7. Import career stats from player_history.json -> update players table career columns
8. Import player_history.json -> player_history table
9. Import match_history.json -> match_scores table
10. Import series_stats.json -> series_stats table
11. Import schedules.json -> schedule table
"""

import json
import os
import re
import sys
import traceback
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.insert(0, project_root)

import psycopg2
from psycopg2.extras import RealDictCursor

from database_config import get_db
from utils.league_utils import (
    get_league_display_name,
    get_league_url,
    normalize_league_id,
)


class ComprehensiveETL:
    def __init__(self):
        # Fix path calculation - script is in data/etl/database_import/, need to go up 3 levels to project root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
        self.data_dir = os.path.join(project_root, "data", "leagues", "all")
        self.imported_counts = {}
        self.errors = []

    def log(self, message: str, level: str = "INFO"):
        """Enhanced logging with timestamps"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def load_json_file(self, filename: str) -> List[Dict]:
        """Load and parse JSON file with error handling"""
        filepath = os.path.join(self.data_dir, filename)
        self.log(f"Loading {filename}...")

        try:
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"File not found: {filepath}")

            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.log(f"✅ Loaded {len(data):,} records from {filename}")
            return data

        except Exception as e:
            self.log(f"❌ Error loading {filename}: {str(e)}", "ERROR")
            raise

    def clear_target_tables(self, conn):
        """Clear existing data from target tables in reverse dependency order"""
        self.log("🗑️  Clearing existing data from target tables...")

        tables_to_clear = [
            "schedule",  # No dependencies
            "series_stats",  # References leagues, teams
            "match_scores",  # References players, leagues, teams
            "player_history",  # References players, leagues
            "players",  # References leagues, clubs, series, teams
            "teams",  # References leagues, clubs, series
            "series_leagues",  # References series, leagues
            "club_leagues",  # References clubs, leagues
            "series",  # Referenced by others
            "clubs",  # Referenced by others
            "leagues",  # Referenced by others
        ]

        try:
            cursor = conn.cursor()

            # Disable foreign key checks temporarily
            cursor.execute("SET session_replication_role = replica;")

            for table in tables_to_clear:
                try:
                    cursor.execute(f"DELETE FROM {table}")
                    deleted_count = cursor.rowcount
                    self.log(f"   ✅ Cleared {deleted_count:,} records from {table}")
                except Exception as e:
                    self.log(f"   ⚠️  Could not clear {table}: {str(e)}", "WARNING")

            # Re-enable foreign key checks
            cursor.execute("SET session_replication_role = DEFAULT;")
            conn.commit()
            self.log("✅ All target tables cleared successfully")

        except Exception as e:
            self.log(f"❌ Error clearing tables: {str(e)}", "ERROR")
            conn.rollback()
            raise

    def extract_leagues(
        self,
        players_data: List[Dict],
        series_stats_data: List[Dict] = None,
        schedules_data: List[Dict] = None,
    ) -> List[Dict]:
        """Extract unique leagues from players data and all other data sources"""
        self.log("🔍 Extracting leagues from all data sources...")

        leagues = set()

        # Extract from players data (original logic)
        for player in players_data:
            league = player.get("League", "").strip()
            if league:
                # Normalize the league ID
                normalized_league = normalize_league_id(league)
                if normalized_league:
                    leagues.add(normalized_league)

        # Extract from series_stats data (new logic to catch all leagues)
        if series_stats_data:
            for record in series_stats_data:
                league = record.get("league_id", "").strip()
                if league:
                    # Normalize the league ID
                    normalized_league = normalize_league_id(league)
                    if normalized_league:
                        leagues.add(normalized_league)

        # Extract from schedules data (new logic to catch all leagues)
        if schedules_data:
            for record in schedules_data:
                league = record.get("League", "").strip()
                if league:
                    # Normalize the league ID
                    normalized_league = normalize_league_id(league)
                    if normalized_league:
                        leagues.add(normalized_league)

        # Convert to standardized format
        league_records = []
        for league_id in sorted(leagues):
            # Create standardized league data using utility functions
            league_record = {
                "league_id": league_id,
                "league_name": get_league_display_name(league_id),
                "league_url": get_league_url(league_id),
            }
            league_records.append(league_record)

        self.log(
            f"✅ Found {len(league_records)} unique leagues: {', '.join([l['league_id'] for l in league_records])}"
        )
        return league_records

    def extract_clubs(self, players_data: List[Dict]) -> List[Dict]:
        """Extract unique clubs from players data with case-insensitive deduplication"""
        self.log("🔍 Extracting clubs from players data...")

        # Use a dict to track normalized names and their preferred capitalization
        clubs_normalized = {}
        case_variants = {}
        
        for player in players_data:
            team_name = player.get(
                "Club", ""
            ).strip()  # This is actually the full team name
            if team_name:
                # Parse the actual club name from the team name
                club_name = self.extract_club_name_from_team(team_name)
                if club_name:
                    # Normalize for case-insensitive comparison
                    normalized_name = club_name.lower().strip()
                    
                    if normalized_name not in clubs_normalized:
                        # First occurrence - use this capitalization
                        clubs_normalized[normalized_name] = club_name
                        case_variants[normalized_name] = [club_name]
                    else:
                        # Track case variants for logging
                        if club_name not in case_variants[normalized_name]:
                            case_variants[normalized_name].append(club_name)
                            
                        # Use the most common capitalization or prefer title case
                        current_name = clubs_normalized[normalized_name]
                        if self._is_better_capitalization(club_name, current_name):
                            clubs_normalized[normalized_name] = club_name

        # Log any case variants detected
        duplicates_detected = 0
        for normalized_name, variants in case_variants.items():
            if len(variants) > 1:
                duplicates_detected += 1
                self.log(f"🔍 Case variants detected for '{clubs_normalized[normalized_name]}': {variants}", "WARNING")

        if duplicates_detected > 0:
            self.log(f"⚠️  Detected {duplicates_detected} clubs with case variants - using normalized names", "WARNING")

        club_records = [{"name": club} for club in sorted(clubs_normalized.values())]

        self.log(f"✅ Found {len(club_records)} unique clubs (after case normalization)")
        return club_records

    def _is_better_capitalization(self, new_name: str, current_name: str) -> bool:
        """Determine if new_name has better capitalization than current_name"""
        # Prefer names with proper title case over all uppercase or all lowercase
        
        # If current is all caps and new is not, prefer new
        if current_name.isupper() and not new_name.isupper():
            return True
            
        # If current is all lowercase and new has proper case, prefer new  
        if current_name.islower() and not new_name.islower():
            return True
            
        # If new has more title case words, prefer it
        current_title_words = sum(1 for word in current_name.split() if word.istitle())
        new_title_words = sum(1 for word in new_name.split() if word.istitle())
        
        if new_title_words > current_title_words:
            return True
            
        return False

    def extract_club_name_from_team(self, team_name: str) -> str:
        """
        Extract club name from team name, matching the logic used in scrapers.

        Args:
            team_name (str): Team name in various formats

        Returns:
            str: Club name

        Examples:
            APTA: "Birchwood - 6" -> "Birchwood"
            CNSWPL: "Birchwood 1" -> "Birchwood"
            NSTF: "Birchwood S1" -> "Birchwood"
            NSTF: "Wilmette Sunday A" -> "Wilmette"
        """
        import re

        if not team_name:
            return "Unknown"

        team_name = team_name.strip()

        # APTA format: "Club - Number"
        if " - " in team_name:
            return team_name.split(" - ")[0].strip()

        # NSTF format: "Club SNumber" or "Club SNumberLetter" (e.g., S1, S2A, S2B)
        elif re.search(r"S\d+[A-Z]*", team_name):
            return re.sub(r"\s+S\d+[A-Z]*.*$", "", team_name).strip()

        # NSTF Sunday format: "Club Sunday A/B"
        elif "Sunday" in team_name:
            club_name = (
                team_name.replace("Sunday A", "").replace("Sunday B", "").strip()
            )
            return club_name if club_name else team_name

        # CNSWPL format: "Club Number" or "Club NumberLetter" (e.g., "Birchwood 1", "Hinsdale PC 1a")
        elif re.search(r"\s+\d+[a-zA-Z]*$", team_name):
            club_part = re.sub(r"\s+\d+[a-zA-Z]*$", "", team_name).strip()
            return club_part if club_part else team_name

        # Fallback: use the team name as-is
        return team_name

    def extract_series(
        self,
        players_data: List[Dict],
        series_stats_data: List[Dict] = None,
        schedules_data: List[Dict] = None,
    ) -> List[Dict]:
        """Extract unique series from players data and team data"""
        self.log("🔍 Extracting series from players data and team data...")

        series = set()

        # Extract from players data (original logic)
        for player in players_data:
            series_name = player.get("Series", "").strip()
            if series_name:
                series.add(series_name)

        # Extract from series_stats data (new logic to fix missing series)
        if series_stats_data:
            for record in series_stats_data:
                series_name = record.get("series", "").strip()
                if series_name:
                    # Clean any malformed series names like "Series eries 16"
                    if "eries " in series_name:
                        series_name = series_name.replace("eries ", "")
                    series.add(series_name)

        # Extract from schedules data by parsing team names (new logic to fix missing series)
        if schedules_data:
            for record in schedules_data:
                home_team = record.get("home_team", "").strip()
                away_team = record.get("away_team", "").strip()

                for team_name in [home_team, away_team]:
                    if team_name and team_name != "BYE":
                        # Parse team name to extract series
                        club_name, series_name = self.parse_schedule_team_name(
                            team_name
                        )
                        if series_name:
                            series.add(series_name)

        series_records = [{"name": series_name} for series_name in sorted(series)]

        self.log(f"✅ Found {len(series_records)} unique series")
        return series_records

    def analyze_club_league_relationships(self, players_data: List[Dict]) -> List[Dict]:
        """Analyze which clubs belong to which leagues"""
        self.log("🔍 Analyzing club-league relationships...")

        club_league_map = {}
        for player in players_data:
            team_name = player.get(
                "Club", ""
            ).strip()  # This is actually the full team name
            club = self.extract_club_name_from_team(
                team_name
            )  # Parse the actual club name
            league = player.get("League", "").strip()

            if club and league:
                # Normalize the league ID
                normalized_league = normalize_league_id(league)
                if normalized_league:
                    if club not in club_league_map:
                        club_league_map[club] = set()
                    club_league_map[club].add(normalized_league)

        relationships = []
        for club, leagues in club_league_map.items():
            for league_id in leagues:
                relationships.append({"club_name": club, "league_id": league_id})

        self.log(f"✅ Found {len(relationships)} club-league relationships")
        return relationships

    def analyze_series_league_relationships(
        self, players_data: List[Dict]
    ) -> List[Dict]:
        """Analyze which series belong to which leagues"""
        self.log("🔍 Analyzing series-league relationships...")

        series_league_map = {}
        for player in players_data:
            series_name = player.get("Series", "").strip()
            league = player.get("League", "").strip()

            if series_name and league:
                # Normalize the league ID
                normalized_league = normalize_league_id(league)
                if normalized_league:
                    if series_name not in series_league_map:
                        series_league_map[series_name] = set()
                    series_league_map[series_name].add(normalized_league)

        relationships = []
        for series_name, leagues in series_league_map.items():
            for league_id in leagues:
                relationships.append(
                    {"series_name": series_name, "league_id": league_id}
                )

        self.log(f"✅ Found {len(relationships)} series-league relationships")
        return relationships

    def extract_teams(
        self, series_stats_data: List[Dict], schedules_data: List[Dict]
    ) -> List[Dict]:
        """Extract unique teams from series stats and schedules data"""
        self.log("🔍 Extracting teams from JSON data...")

        teams = set()

        # Extract from series_stats.json
        for record in series_stats_data:
            series_name = record.get("series", "").strip()
            team_name = record.get("team", "").strip()
            league_id = normalize_league_id(record.get("league_id", "").strip())

            if team_name and series_name and league_id:
                # FIXED: Clean any malformed series names like "Series eries 16"
                if "eries " in series_name:
                    series_name = series_name.replace("eries ", "")

                # FIXED: Apply same series name conversion as in import_series_stats
                # Convert "Series X" to "Division X" for CNSWPL compatibility
                if series_name.startswith("Series ") and league_id == "CNSWPL":
                    series_name = series_name.replace("Series ", "Division ")

                # Parse team name to extract club
                club_name = self.parse_team_name_to_club(team_name, series_name)
                if club_name:
                    teams.add((club_name, series_name, league_id, team_name))

        # Extract from schedules.json (both home and away teams)
        for record in schedules_data:
            league_id = normalize_league_id(record.get("League", "").strip())
            home_team = record.get("home_team", "").strip()
            away_team = record.get("away_team", "").strip()

            for team_name in [home_team, away_team]:
                if team_name and league_id and team_name != "BYE":
                    # Parse team name to extract club and series
                    club_name, series_name = self.parse_schedule_team_name(team_name)
                    if club_name and series_name:
                        # FIXED: Ensure consistent series name format for all sources
                        # Clean any malformed series names like "Series eries 16"
                        if "eries " in series_name:
                            series_name = series_name.replace("eries ", "")
                        teams.add((club_name, series_name, league_id, team_name))

        # Convert to list of dictionaries
        team_records = []
        for club_name, series_name, league_id, team_name in sorted(teams):
            team_records.append(
                {
                    "club_name": club_name,
                    "series_name": series_name,
                    "league_id": league_id,
                    "team_name": team_name,
                }
            )

        self.log(f"✅ Found {len(team_records)} unique teams")
        return team_records

    def parse_team_name_to_club(self, team_name: str, series_name: str) -> str:
        """Parse team name from series_stats to extract club name"""
        # Examples:
        # APTA_CHICAGO: "Tennaqua - 22" with series "Chicago 22" -> "Tennaqua"
        # NSTF: "Tennaqua S2B" with series "Series 2B" -> "Tennaqua"
        # CNSWPL: "Tennaqua 1" with series "Division 16" -> "Tennaqua"

        # Handle APTA_CHICAGO format: "Club - Suffix"
        if " - " in team_name:
            club_part = team_name.split(" - ")[0].strip()
            return club_part

        # Handle NSTF format: "Club SSuffix" (like "Tennaqua S2B")
        # Must be " S" followed by number or number+letter (not words like "Shore")
        import re

        if re.search(r" S\d", team_name):  # " S" followed by a digit
            parts = team_name.split(" S")
            if len(parts) >= 2:
                club_part = parts[0].strip()
                return club_part

        # Handle CNSWPL format: "Club Number" or "Club NumberLetter" (like "Tennaqua 1", "Hinsdale PC 1a")
        # Must end with space + digit + optional letter(s)
        if re.search(r"\s+\d+[a-zA-Z]*$", team_name):
            club_part = re.sub(r"\s+\d+[a-zA-Z]*$", "", team_name).strip()
            if club_part:  # Make sure we didn't remove everything
                return club_part

        # Fallback: return the whole team name as club
        return team_name

    def parse_schedule_team_name(self, team_name: str) -> tuple:
        """Parse team name from schedules to extract club and series"""
        # Examples:
        # APTA_CHICAGO: "Tennaqua - 22" -> ("Tennaqua", "Chicago 22")
        # NSTF: "Tennaqua S2B" -> ("Tennaqua", "Series 2B")
        # CNSWPL: "Tennaqua 1" -> ("Tennaqua", "Division 1")

        # Handle APTA_CHICAGO format: "Club - Suffix"
        if " - " in team_name:
            parts = team_name.split(" - ")
            if len(parts) >= 2:
                club_name = parts[0].strip()
                series_suffix = parts[1].strip()

                # Map series suffix to full series name
                series_name = self.map_series_suffix_to_full_name(series_suffix)
                return club_name, series_name

        # Handle NSTF format: "Club SSuffix" (like "Tennaqua S2B")
        # Must be " S" followed by number or number+letter (not words like "Shore")
        import re

        if re.search(r" S\d", team_name):  # " S" followed by a digit
            parts = team_name.split(" S")
            if len(parts) >= 2:
                club_name = parts[0].strip()
                series_suffix = parts[1].strip()

                # Map series suffix to full series name (for NSTF, this becomes "Series 2B")
                series_name = self.map_series_suffix_to_full_name(f"S{series_suffix}")
                return club_name, series_name

        # Handle CNSWPL format: "Club Number" or "Club NumberLetter" (like "Tennaqua 1", "Hinsdale PC 1a")
        # Must end with space + digit + optional letter(s)
        if re.search(r"\s+\d+[a-zA-Z]*$", team_name):
            club_name = re.sub(r"\s+\d+[a-zA-Z]*$", "", team_name).strip()
            if club_name:
                # Extract the series suffix (number + optional letters)
                series_match = re.search(r"\s+(\d+[a-zA-Z]*)$", team_name)
                if series_match:
                    series_suffix = series_match.group(1)
                    # For CNSWPL, map to "Division N" format to match player data
                    series_name = f"Division {series_suffix}"
                    return club_name, series_name

        # Fallback for edge cases: treat entire name as club with default series
        return team_name, "Series A"

    def map_series_suffix_to_full_name(self, suffix: str) -> str:
        """Map series suffix to full series name"""
        # Examples: "22" -> "Chicago 22", "21 SW" -> "Chicago 21 SW", "S2B" -> "Series 2B"
        try:
            # If it's a pure number, check if it's a small number (likely CNSWPL Division N)
            series_num = int(suffix)
            if (
                series_num <= 20
            ):  # CNSWPL divisions are typically 1-17, with some letters
                return f"Division {series_num}"
            else:
                # Larger numbers are likely APTA Chicago series
                return f"Chicago {series_num}"
        except ValueError:
            # If it's not a pure number, handle special cases
            if suffix.upper().startswith("S"):
                # NSTF format like "S2B" -> "Series 2B"
                return f"Series {suffix[1:]}"
            elif any(char.isdigit() for char in suffix):
                # If it contains numbers but isn't pure number
                # Check if it's CNSWPL format (like "1a", "16b")
                if len(suffix) <= 3 and suffix[0].isdigit():
                    return f"Division {suffix}"
                else:
                    # Otherwise assume Chicago (like "21 SW")
                    return f"Chicago {suffix}"

            # Default: assume it's already a series name
            return suffix

    def import_leagues(self, conn, leagues_data: List[Dict]):
        """Import leagues into database"""
        self.log("📥 Importing leagues...")

        cursor = conn.cursor()
        imported = 0

        for league in leagues_data:
            try:
                cursor.execute(
                    """
                    INSERT INTO leagues (league_id, league_name, league_url, created_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (league_id) DO NOTHING
                """,
                    (league["league_id"], league["league_name"], league["league_url"]),
                )

                if cursor.rowcount > 0:
                    imported += 1

            except Exception as e:
                self.log(
                    f"❌ Error importing league {league['league_id']}: {str(e)}",
                    "ERROR",
                )
                raise

        conn.commit()
        self.imported_counts["leagues"] = imported
        self.log(f"✅ Imported {imported} leagues")

    def import_clubs(self, conn, clubs_data: List[Dict]):
        """Import clubs into database with case-insensitive duplicate prevention"""
        self.log("📥 Importing clubs...")

        cursor = conn.cursor()
        imported = 0
        skipped_duplicates = 0

        for club in clubs_data:
            try:
                club_name = club["name"]
                
                # Check for case-insensitive duplicates in existing database
                cursor.execute(
                    """
                    SELECT id, name FROM clubs 
                    WHERE LOWER(name) = LOWER(%s)
                """,
                    (club_name,),
                )
                
                existing_club = cursor.fetchone()
                
                if existing_club:
                    existing_id, existing_name = existing_club
                    
                    if existing_name != club_name:
                        # Case-insensitive duplicate detected
                        self.log(
                            f"🔍 Case-insensitive duplicate detected: '{club_name}' (existing: '{existing_name}')",
                            "WARNING"
                        )
                        
                        # Update to better capitalization if needed
                        if self._is_better_capitalization(club_name, existing_name):
                            cursor.execute(
                                """
                                UPDATE clubs SET name = %s WHERE id = %s
                                """,
                                (club_name, existing_id),
                            )
                            self.log(f"📝 Updated club capitalization: '{existing_name}' → '{club_name}'")
                    
                    skipped_duplicates += 1
                else:
                    # Insert new club
                    cursor.execute(
                        """
                        INSERT INTO clubs (name)
                        VALUES (%s)
                    """,
                        (club_name,),
                    )
                    imported += 1

            except Exception as e:
                self.log(f"❌ Error importing club {club['name']}: {str(e)}", "ERROR")
                raise

        conn.commit()
        self.imported_counts["clubs"] = imported
        
        if skipped_duplicates > 0:
            self.log(f"✅ Imported {imported} clubs, skipped {skipped_duplicates} case-insensitive duplicates")
        else:
            self.log(f"✅ Imported {imported} clubs")

    def import_series(self, conn, series_data: List[Dict]):
        """Import series into database"""
        self.log("📥 Importing series...")

        cursor = conn.cursor()
        imported = 0

        for series in series_data:
            try:
                cursor.execute(
                    """
                    INSERT INTO series (name)
                    VALUES (%s)
                    ON CONFLICT (name) DO NOTHING
                """,
                    (series["name"],),
                )

                if cursor.rowcount > 0:
                    imported += 1

            except Exception as e:
                self.log(
                    f"❌ Error importing series {series['name']}: {str(e)}", "ERROR"
                )
                raise

        conn.commit()
        self.imported_counts["series"] = imported
        self.log(f"✅ Imported {imported} series")

    def import_club_leagues(self, conn, relationships: List[Dict]):
        """Import club-league relationships"""
        self.log("📥 Importing club-league relationships...")

        cursor = conn.cursor()
        imported = 0

        for rel in relationships:
            try:
                cursor.execute(
                    """
                    INSERT INTO club_leagues (club_id, league_id, created_at)
                    SELECT c.id, l.id, CURRENT_TIMESTAMP
                    FROM clubs c, leagues l
                    WHERE c.name = %s AND l.league_id = %s
                    ON CONFLICT ON CONSTRAINT unique_club_league DO NOTHING
                """,
                    (rel["club_name"], rel["league_id"]),
                )

                if cursor.rowcount > 0:
                    imported += 1

            except Exception as e:
                self.log(
                    f"❌ Error importing club-league relationship {rel['club_name']}-{rel['league_id']}: {str(e)}",
                    "ERROR",
                )
                raise

        conn.commit()
        self.imported_counts["club_leagues"] = imported
        self.log(f"✅ Imported {imported} club-league relationships")

    def import_series_leagues(self, conn, relationships: List[Dict]):
        """Import series-league relationships"""
        self.log("📥 Importing series-league relationships...")

        cursor = conn.cursor()
        imported = 0

        for rel in relationships:
            try:
                cursor.execute(
                    """
                    INSERT INTO series_leagues (series_id, league_id, created_at)
                    SELECT s.id, l.id, CURRENT_TIMESTAMP
                    FROM series s, leagues l
                    WHERE s.name = %s AND l.league_id = %s
                    ON CONFLICT ON CONSTRAINT unique_series_league DO NOTHING
                """,
                    (rel["series_name"], rel["league_id"]),
                )

                if cursor.rowcount > 0:
                    imported += 1

            except Exception as e:
                self.log(
                    f"❌ Error importing series-league relationship {rel['series_name']}-{rel['league_id']}: {str(e)}",
                    "ERROR",
                )
                raise

        conn.commit()
        self.imported_counts["series_leagues"] = imported
        self.log(f"✅ Imported {imported} series-league relationships")

    def import_teams(self, conn, teams_data: List[Dict]):
        """Import teams into database with enhanced duplicate handling"""
        self.log("📥 Importing teams...")

        cursor = conn.cursor()
        imported = 0
        updated = 0
        errors = 0
        skipped = 0

        # First, let's deduplicate the teams_data based on BOTH database constraints:
        # 1. unique_team_club_series_league: (club_id, series_id, league_id)
        # 2. unique_team_name_per_league: (team_name, league_id)

        from collections import defaultdict

        teams_by_club_series_league = defaultdict(list)  # Constraint 1
        teams_by_name_league = defaultdict(list)  # Constraint 2

        for team in teams_data:
            constraint_key_1 = (
                team["club_name"],
                team["series_name"],
                team["league_id"],
            )
            constraint_key_2 = (team["team_name"], team["league_id"])

            teams_by_club_series_league[constraint_key_1].append(team)
            teams_by_name_league[constraint_key_2].append(team)

        # Log any duplicates found for first constraint
        duplicates_found_1 = 0
        for constraint_key, team_list in teams_by_club_series_league.items():
            if len(team_list) > 1:
                duplicates_found_1 += 1
                if duplicates_found_1 <= 5:  # Log first 5 duplicates
                    club_name, series_name, league_id = constraint_key
                    self.log(
                        f"🔍 DUPLICATE CONSTRAINT: {club_name} / {series_name} / {league_id}",
                        "INFO",
                    )
                    for i, team in enumerate(team_list, 1):
                        self.log(f"   {i}. Team name: {team['team_name']}", "INFO")

        # Log any duplicates found for second constraint
        duplicates_found_2 = 0
        for constraint_key, team_list in teams_by_name_league.items():
            if len(team_list) > 1:
                duplicates_found_2 += 1
                if duplicates_found_2 <= 5:  # Log first 5 duplicates
                    team_name, league_id = constraint_key
                    self.log(
                        f"🔍 DUPLICATE CONSTRAINT 2: {team_name} / {league_id}", "INFO"
                    )
                    for i, team in enumerate(team_list, 1):
                        self.log(
                            f"   {i}. Club/Series: {team['club_name']} / {team['series_name']}",
                            "INFO",
                        )

        if duplicates_found_1 > 0:
            self.log(
                f"📊 Found {duplicates_found_1} club/series/league duplicates", "INFO"
            )
        if duplicates_found_2 > 0:
            self.log(
                f"📊 Found {duplicates_found_2} team name/league duplicates", "INFO"
            )

        # Deduplicate by both constraints - use a two-stage approach
        # Stage 1: Deduplicate by club/series/league (first constraint)
        teams_stage_1 = []
        for constraint_key, team_list in teams_by_club_series_league.items():
            teams_stage_1.append(team_list[0])  # Use first occurrence

        # Stage 2: Deduplicate by team name/league (second constraint)
        teams_by_name_league_stage_2 = defaultdict(list)
        for team in teams_stage_1:
            constraint_key_2 = (team["team_name"], team["league_id"])
            teams_by_name_league_stage_2[constraint_key_2].append(team)

        teams_to_process = []
        name_conflicts_resolved = 0
        for constraint_key, team_list in teams_by_name_league_stage_2.items():
            if len(team_list) > 1:
                name_conflicts_resolved += 1
                # For name conflicts, modify the team names to make them unique
                team_name, league_id = constraint_key
                for i, team in enumerate(team_list):
                    if i > 0:  # Keep first one as-is, modify others
                        original_name = team["team_name"]
                        # Make it unique by adding series info
                        team["team_name"] = f"{original_name} ({team['series_name']})"
                        if name_conflicts_resolved <= 3:  # Log first 3 resolutions
                            self.log(
                                f"🔧 Resolved name conflict: {original_name} → {team['team_name']}"
                            )
                    # Add each team to the processing list (all teams in the conflict group)
                    teams_to_process.append(team)
            else:
                # Only one team with this name in this league
                teams_to_process.append(team_list[0])

        if name_conflicts_resolved > 0:
            self.log(f"🔧 Resolved {name_conflicts_resolved} team name conflicts")

        self.log(
            f"📊 Processing {len(teams_to_process)} unique teams (deduplicated from {len(teams_data)})"
        )

        for team in teams_to_process:
            try:
                club_name = team["club_name"]
                series_name = team["series_name"]
                league_id = team["league_id"]
                team_name = team["team_name"]

                # Create team alias for display (optional)
                team_alias = self.generate_team_alias(team_name, series_name)

                # Check if team already exists by constraint (club_id, series_id, league_id)
                cursor.execute(
                    """
                    SELECT t.id, t.team_name FROM teams t
                    JOIN clubs c ON t.club_id = c.id
                    JOIN series s ON t.series_id = s.id
                    JOIN leagues l ON t.league_id = l.id
                    WHERE c.name = %s AND s.name = %s AND l.league_id = %s
                """,
                    (club_name, series_name, league_id),
                )

                existing_team = cursor.fetchone()

                if existing_team:
                    # Team already exists, update it if needed
                    existing_id, existing_name = existing_team
                    cursor.execute(
                        """
                        UPDATE teams SET 
                            team_name = %s,
                            team_alias = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """,
                        (team_name, team_alias, existing_id),
                    )
                    updated += 1

                    if existing_name != team_name:
                        self.log(f"📝 Updated team name: {existing_name} → {team_name}")
                else:
                    # Verify that the club, series, and league exist
                    cursor.execute(
                        """
                        SELECT c.id, s.id, l.id 
                        FROM clubs c, series s, leagues l
                        WHERE c.name = %s AND s.name = %s AND l.league_id = %s
                    """,
                        (club_name, series_name, league_id),
                    )

                    refs = cursor.fetchone()

                    if not refs:
                        self.log(
                            f"⚠️  Skipping team {team_name}: missing references (club: {club_name}, series: {series_name}, league: {league_id})",
                            "WARNING",
                        )
                        skipped += 1
                        continue

                    club_id, series_id, league_db_id = refs

                    # Create new team
                    cursor.execute(
                        """
                        INSERT INTO teams (club_id, series_id, league_id, team_name, team_alias, created_at)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """,
                        (club_id, series_id, league_db_id, team_name, team_alias),
                    )
                    imported += 1

            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.log(
                        f"❌ Error importing team {team.get('team_name', 'Unknown')}: {str(e)}",
                        "ERROR",
                    )

                if errors > 25:  # Reduced threshold since we deduplicated
                    self.log(
                        f"❌ Too many team import errors ({errors}), stopping", "ERROR"
                    )
                    raise Exception(f"Too many team import errors ({errors})")

        conn.commit()
        self.imported_counts["teams"] = imported + updated
        self.log(
            f"✅ Team import complete: {imported} new, {updated} updated, {skipped} skipped, {errors} errors"
        )

        if duplicates_found_1 > 0 or duplicates_found_2 > 0:
            self.log(
                f"🔧 Successfully handled {duplicates_found_1 + duplicates_found_2} total constraint duplicates"
            )

    def generate_team_alias(self, team_name: str, series_name: str) -> str:
        """Generate a user-friendly team alias"""
        # Examples:
        # APTA_CHICAGO: "Tennaqua - 22" -> "Series 22"
        # NSTF: "Tennaqua S2B" -> "Series 2B"

        # Handle APTA_CHICAGO format: "Club - Suffix"
        if " - " in team_name:
            parts = team_name.split(" - ")
            if len(parts) >= 2:
                suffix = parts[1].strip()
                return f"Series {suffix}"

        # Handle NSTF format: "Club SSuffix"
        # Must be " S" followed by number or number+letter (not words like "Shore")
        import re

        if re.search(r" S\d", team_name):  # " S" followed by a digit
            parts = team_name.split(" S")
            if len(parts) >= 2:
                suffix = parts[1].strip()
                return f"Series {suffix}"

        # Fallback: use series name
        return series_name

    def import_players(self, conn, players_data: List[Dict]):
        """Import players data with enhanced conflict detection"""
        self.log("📥 Importing players with enhanced conflict detection...")

        cursor = conn.cursor()
        imported = 0
        updated = 0
        errors = 0
        player_id_tracker = {}  # Track multiple records per Player ID

        # First pass: analyze for potential conflicts
        self.log("🔍 Step 1: Analyzing potential conflicts...")
        conflicts_found = 0
        for player in players_data:
            player_id = player.get("Player ID", "").strip()
            league_id = normalize_league_id(player.get("League", "").strip())
            club_name = player.get("Club", "").strip()
            series_name = player.get("Series", "").strip()

            if player_id and league_id:
                key = f"{league_id}::{player_id}"
                if key not in player_id_tracker:
                    player_id_tracker[key] = []
                player_id_tracker[key].append(
                    {
                        "club": club_name,
                        "series": series_name,
                        "name": f"{player.get('First Name', '')} {player.get('Last Name', '')}",
                    }
                )

        # Log conflicts found
        for key, records in player_id_tracker.items():
            if len(records) > 1:
                conflicts_found += 1
                if conflicts_found <= 5:  # Log first 5 conflicts as examples
                    league, player_id = key.split("::")
                    self.log(
                        f"🔍 CONFLICT DETECTED: Player ID {player_id} in {league}",
                        "INFO",
                    )
                    for i, record in enumerate(records, 1):
                        self.log(
                            f"   {i}. {record['name']} at {record['club']} / {record['series']}",
                            "INFO",
                        )

        if conflicts_found > 0:
            self.log(
                f"📊 Found {conflicts_found} Player IDs with multiple club/series records",
                "INFO",
            )
            self.log("✅ Enhanced constraint will allow all records to coexist", "INFO")

        # Second pass: import players
        self.log("📥 Step 2: Importing player records...")

        for player in players_data:
            try:
                # Extract and clean data
                tenniscores_player_id = player.get("Player ID", "").strip()
                first_name = player.get("First Name", "").strip()
                last_name = player.get("Last Name", "").strip()
                raw_league_id = player.get("League", "").strip()
                league_id = normalize_league_id(raw_league_id) if raw_league_id else ""
                team_name = player.get(
                    "Club", ""
                ).strip()  # This is actually the full team name
                club_name = self.extract_club_name_from_team(
                    team_name
                )  # Parse the actual club name
                series_name = player.get("Series", "").strip()

                # Parse PTI - handle both string and numeric types
                pti_value = player.get("PTI", "")
                pti = None
                if pti_value is not None and pti_value != "":
                    if isinstance(pti_value, (int, float)):
                        pti = float(pti_value)
                    else:
                        pti_str = str(pti_value).strip()
                        if pti_str and pti_str.upper() != "N/A":
                            try:
                                pti = float(pti_str)
                            except ValueError:
                                pass

                # Parse wins/losses
                wins = self._parse_int(player.get("Wins", "0"))
                losses = self._parse_int(player.get("Losses", "0"))

                # Parse win percentage - handle both string and numeric types
                win_pct_value = player.get("Win %", "0.0%")
                win_percentage = 0.0
                if isinstance(win_pct_value, (int, float)):
                    win_percentage = float(win_pct_value)
                else:
                    try:
                        win_pct_str = str(win_pct_value).replace("%", "").strip()
                        win_percentage = float(win_pct_str)
                    except (ValueError, AttributeError):
                        pass

                # Captain status - handle different data types
                captain_value = player.get("Captain", "")
                captain_status = (
                    str(captain_value).strip() if captain_value is not None else ""
                )

                if not all([tenniscores_player_id, first_name, last_name, league_id]):
                    self.log(
                        f"⚠️  Skipping player with missing required data: {player}",
                        "WARNING",
                    )
                    continue

                # Check if this exact combination already exists
                cursor.execute(
                    """
                    SELECT p.id FROM players p
                    JOIN leagues l ON p.league_id = l.id
                    LEFT JOIN clubs c ON p.club_id = c.id
                    LEFT JOIN series s ON p.series_id = s.id
                    WHERE p.tenniscores_player_id = %s 
                    AND l.league_id = %s
                    AND COALESCE(c.name, '') = %s
                    AND COALESCE(s.name, '') = %s
                """,
                    (
                        tenniscores_player_id,
                        league_id,
                        club_name or "",
                        series_name or "",
                    ),
                )

                existing_player = cursor.fetchone()
                is_update = existing_player is not None

                cursor.execute(
                    """
                    INSERT INTO players (
                        tenniscores_player_id, first_name, last_name, 
                        league_id, club_id, series_id, team_id, pti, wins, losses, 
                        win_percentage, captain_status, is_active, created_at
                    )
                    SELECT 
                        %s, %s, %s,
                        l.id, c.id, s.id, t.id, %s, %s, %s,
                        %s, %s, true, CURRENT_TIMESTAMP
                    FROM leagues l
                    LEFT JOIN clubs c ON c.name = %s
                    LEFT JOIN series s ON s.name = %s
                    LEFT JOIN teams t ON t.club_id = c.id AND t.series_id = s.id AND t.league_id = l.id
                    WHERE l.league_id = %s
                    ON CONFLICT ON CONSTRAINT unique_player_in_league_club_series DO UPDATE SET
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        team_id = EXCLUDED.team_id,
                        pti = EXCLUDED.pti,
                        wins = EXCLUDED.wins,
                        losses = EXCLUDED.losses,
                        win_percentage = EXCLUDED.win_percentage,
                        captain_status = EXCLUDED.captain_status,
                        is_active = EXCLUDED.is_active,
                        updated_at = CURRENT_TIMESTAMP
                """,
                    (
                        tenniscores_player_id,
                        first_name,
                        last_name,
                        pti,
                        wins,
                        losses,
                        win_percentage,
                        captain_status,
                        club_name,
                        series_name,
                        league_id,
                    ),
                )

                if is_update:
                    updated += 1
                else:
                    imported += 1

                if (imported + updated) % 1000 == 0:
                    self.log(
                        f"   📊 Processed {imported + updated:,} players so far (New: {imported:,}, Updated: {updated:,})..."
                    )
                    conn.commit()  # Commit in batches

            except Exception as e:
                errors += 1
                if errors <= 10:  # Only log first 10 errors
                    self.log(
                        f"❌ Error importing player {player.get('Player ID', 'Unknown')}: {str(e)}",
                        "ERROR",
                    )

                if errors > 100:  # Stop if too many errors
                    self.log(
                        f"❌ Too many errors ({errors}), stopping player import",
                        "ERROR",
                    )
                    raise Exception(f"Too many player import errors ({errors})")

        conn.commit()
        self.imported_counts["players"] = imported + updated
        self.log(
            f"✅ Player import complete: {imported:,} new, {updated:,} updated, {errors} errors"
        )
        self.log(
            f"🎯 Conflict resolution: {conflicts_found} Player IDs now exist across multiple clubs/series"
        )

    def import_career_stats(self, conn, player_history_data: List[Dict]):
        """Import career stats from player_history.json into players table career columns"""
        self.log("📥 Importing career stats...")

        cursor = conn.cursor()
        updated = 0
        not_found = 0
        errors = 0

        for player_data in player_history_data:
            try:
                # Extract career stats from JSON
                player_name = player_data.get("name", "")
                career_wins = player_data.get("wins", 0)
                career_losses = player_data.get("losses", 0)
                tenniscores_id = player_data.get("player_id", "").strip()

                if not tenniscores_id:
                    continue

                # Calculate derived stats
                career_matches = career_wins + career_losses
                career_win_percentage = (
                    round((career_wins / career_matches) * 100, 2)
                    if career_matches > 0
                    else 0.00
                )

                # Find and update the player in the database
                cursor.execute(
                    """
                    UPDATE players 
                    SET 
                        career_wins = %s,
                        career_losses = %s, 
                        career_matches = %s,
                        career_win_percentage = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE tenniscores_player_id = %s
                """,
                    (
                        career_wins,
                        career_losses,
                        career_matches,
                        career_win_percentage,
                        tenniscores_id,
                    ),
                )

                if cursor.rowcount > 0:
                    updated += 1

                    # Log progress for significant players
                    if career_matches >= 20 and updated % 50 == 0:
                        self.log(f"   📊 Updated {updated:,} career stats so far...")
                else:
                    not_found += 1

            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.log(
                        f"❌ Error updating career stats for {player_name}: {str(e)}",
                        "ERROR",
                    )

                if errors > 100:
                    self.log(
                        f"❌ Too many career stats errors ({errors}), stopping", "ERROR"
                    )
                    raise Exception(f"Too many career stats import errors ({errors})")

        conn.commit()
        self.imported_counts["career_stats"] = updated
        self.log(
            f"✅ Updated {updated:,} players with career stats ({not_found} not found, {errors} errors)"
        )

    def import_player_history(self, conn, player_history_data: List[Dict]):
        """Import player history data"""
        self.log("📥 Importing player history...")

        cursor = conn.cursor()
        imported = 0
        errors = 0

        for player_record in player_history_data:
            try:
                tenniscores_player_id = player_record.get("player_id", "").strip()
                raw_league_id = player_record.get("league_id", "").strip()
                league_id = normalize_league_id(raw_league_id) if raw_league_id else ""
                series = player_record.get("series", "").strip()
                matches = player_record.get("matches", [])

                if not all([tenniscores_player_id, league_id]) or not matches:
                    continue

                # Get the database player ID
                cursor.execute(
                    """
                    SELECT p.id, l.id 
                    FROM players p 
                    JOIN leagues l ON l.league_id = %s
                    WHERE p.tenniscores_player_id = %s AND p.league_id = l.id
                """,
                    (league_id, tenniscores_player_id),
                )

                result = cursor.fetchone()
                if not result:
                    continue

                db_player_id, db_league_id = result

                # Import each match history record
                for match in matches:
                    try:
                        date_str = match.get("date", "").strip()
                        end_pti = match.get("end_pti")
                        match_series = match.get("series", series).strip()

                        # Parse date
                        record_date = None
                        if date_str:
                            try:
                                record_date = datetime.strptime(
                                    date_str, "%m/%d/%Y"
                                ).date()
                            except ValueError:
                                try:
                                    record_date = datetime.strptime(
                                        date_str, "%Y-%m-%d"
                                    ).date()
                                except ValueError:
                                    pass

                        if not record_date:
                            continue

                        cursor.execute(
                            """
                            INSERT INTO player_history (player_id, league_id, series, date, end_pti, created_at)
                            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        """,
                            (
                                db_player_id,
                                db_league_id,
                                match_series,
                                record_date,
                                end_pti,
                            ),
                        )

                        imported += 1

                    except Exception as match_error:
                        errors += 1
                        if errors <= 10:
                            self.log(
                                f"❌ Error importing match for player {tenniscores_player_id}: {str(match_error)}",
                                "ERROR",
                            )

                if imported % 1000 == 0 and imported > 0:
                    self.log(
                        f"   📊 Imported {imported:,} player history records so far..."
                    )
                    conn.commit()

            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.log(
                        f"❌ Error importing player history for {tenniscores_player_id}: {str(e)}",
                        "ERROR",
                    )

                if errors > 100:
                    self.log(
                        f"❌ Too many player history errors ({errors}), stopping",
                        "ERROR",
                    )
                    raise Exception(f"Too many player history import errors ({errors})")

        conn.commit()
        self.imported_counts["player_history"] = imported
        self.log(f"✅ Imported {imported:,} player history records ({errors} errors)")

    def validate_and_correct_winner(
        self,
        scores: str,
        winner: str,
        home_team: str,
        away_team: str,
        league_id: str = None,
    ) -> str:
        """
        Validate winner against score data and correct if needed
        Enhanced with league-specific validation logic
        """
        if not scores or not scores.strip():
            return winner

        # Use the enhanced league-aware validation
        from utils.league_utils import normalize_league_id

        normalized_league = normalize_league_id(league_id) if league_id else None

        # Clean up score string and remove tiebreak info
        scores_clean = scores.strip()
        scores_clean = re.sub(r"\s*\[[^\]]+\]", "", scores_clean)

        # Split by comma to get individual sets
        sets = [s.strip() for s in scores_clean.split(",") if s.strip()]

        # CITA League: Skip validation for problematic data patterns
        if normalized_league == "CITA" and len(sets) >= 1:
            for set_score in sets:
                if "-" in set_score:
                    try:
                        parts = set_score.split("-")
                        if len(parts) == 2:
                            home_games = int(parts[0].strip())
                            away_games = int(parts[1].strip())
                            # Skip incomplete CITA matches (like 2-2, 3-3, etc.)
                            if (
                                home_games < 6
                                and away_games < 6
                                and abs(home_games - away_games) <= 2
                                and not (home_games == 0 and away_games == 0)
                            ):
                                return winner  # Don't correct problematic CITA data
                    except (ValueError, IndexError):
                        pass

        home_sets_won = 0
        away_sets_won = 0

        for i, set_score in enumerate(sets):
            if "-" not in set_score:
                continue

            try:
                parts = set_score.split("-")
                if len(parts) != 2:
                    continue

                home_games = int(parts[0].strip())
                away_games = int(parts[1].strip())

                # Handle super tiebreak format (NSTF, CITA)
                if (
                    i == 2
                    and len(sets) == 3
                    and (
                        normalized_league in ["NSTF", "CITA"]
                        or home_games >= 10
                        or away_games >= 10
                    )
                ):
                    # This is a super tiebreak
                    if home_games > away_games:
                        home_sets_won += 1
                    elif away_games > home_games:
                        away_sets_won += 1
                    continue

                # Standard set scoring
                if home_games > away_games:
                    home_sets_won += 1
                elif away_games > home_games:
                    away_sets_won += 1

            except (ValueError, IndexError):
                continue

        # Determine overall winner
        calculated_winner = None
        if home_sets_won > away_sets_won:
            calculated_winner = "home"
        elif away_sets_won > home_sets_won:
            calculated_winner = "away"

        # Return corrected winner if mismatch found
        if calculated_winner and winner.lower() not in ["home", "away"]:
            return calculated_winner
        elif (
            calculated_winner
            and winner.lower() in ["home", "away"]
            and winner.lower() != calculated_winner
        ):
            return calculated_winner
        else:
            return winner

    def import_match_history(self, conn, match_history_data: List[Dict]):
        """Import match history data into match_scores table with winner validation"""
        self.log("📥 Importing match history...")

        cursor = conn.cursor()
        imported = 0
        errors = 0
        winner_corrections = 0

        for record in match_history_data:
            try:
                # Extract data using the actual field names from the JSON
                match_date_str = (record.get("Date") or "").strip()
                home_team = (record.get("Home Team") or "").strip()
                away_team = (record.get("Away Team") or "").strip()
                scores = record.get("Scores") or ""
                winner = (record.get("Winner") or "").strip()
                raw_league_id = (record.get("league_id") or "").strip()
                league_id = normalize_league_id(raw_league_id) if raw_league_id else ""

                # Extract player IDs
                home_player_1_id = (record.get("Home Player 1 ID") or "").strip()
                home_player_2_id = (record.get("Home Player 2 ID") or "").strip()
                away_player_1_id = (record.get("Away Player 1 ID") or "").strip()
                away_player_2_id = (record.get("Away Player 2 ID") or "").strip()

                # Parse date (format appears to be DD-Mon-YY)
                match_date = None
                if match_date_str:
                    try:
                        # Try DD-Mon-YY format first
                        match_date = datetime.strptime(
                            match_date_str, "%d-%b-%y"
                        ).date()
                    except ValueError:
                        try:
                            match_date = datetime.strptime(
                                match_date_str, "%m/%d/%Y"
                            ).date()
                        except ValueError:
                            try:
                                match_date = datetime.strptime(
                                    match_date_str, "%Y-%m-%d"
                                ).date()
                            except ValueError:
                                pass

                if not all([match_date, home_team, away_team]):
                    continue

                # ENHANCED: Validate winner against score data with league-specific logic
                original_winner = winner
                winner = self.validate_and_correct_winner(
                    scores, winner, home_team, away_team, league_id
                )
                if winner != original_winner:
                    winner_corrections += 1
                    if winner_corrections <= 5:  # Log first 5 corrections
                        self.log(
                            f"🔧 Corrected winner for {home_team} vs {away_team} ({match_date_str}, {league_id}): {original_winner} → {winner}"
                        )

                # Validate winner field - only allow 'home', 'away', or None
                if winner and winner.lower() not in ["home", "away"]:
                    winner = None  # Set to None for invalid values like 'unknown'

                # Get league database ID
                cursor.execute(
                    "SELECT id FROM leagues WHERE league_id = %s", (league_id,)
                )
                league_row = cursor.fetchone()
                league_db_id = league_row[0] if league_row else None

                # Get team IDs from teams table
                home_team_id = None
                away_team_id = None

                if home_team and home_team != "BYE":
                    cursor.execute(
                        """
                        SELECT t.id FROM teams t
                        JOIN leagues l ON t.league_id = l.id
                        WHERE l.league_id = %s AND t.team_name = %s
                    """,
                        (league_id, home_team),
                    )
                    home_team_row = cursor.fetchone()
                    home_team_id = home_team_row[0] if home_team_row else None

                if away_team and away_team != "BYE":
                    cursor.execute(
                        """
                        SELECT t.id FROM teams t
                        JOIN leagues l ON t.league_id = l.id
                        WHERE l.league_id = %s AND t.team_name = %s
                    """,
                        (league_id, away_team),
                    )
                    away_team_row = cursor.fetchone()
                    away_team_id = away_team_row[0] if away_team_row else None

                cursor.execute(
                    """
                    INSERT INTO match_scores (
                        match_date, home_team, away_team, home_team_id, away_team_id,
                        home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id, 
                        scores, winner, league_id, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                    (
                        match_date,
                        home_team,
                        away_team,
                        home_team_id,
                        away_team_id,
                        home_player_1_id,
                        home_player_2_id,
                        away_player_1_id,
                        away_player_2_id,
                        str(scores),
                        winner,
                        league_db_id,
                    ),
                )

                imported += 1

                if imported % 1000 == 0:
                    self.log(f"   📊 Imported {imported:,} match records so far...")
                    conn.commit()

            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.log(f"❌ Error importing match record: {str(e)}", "ERROR")

                if errors > 100:
                    self.log(
                        f"❌ Too many match history errors ({errors}), stopping",
                        "ERROR",
                    )
                    raise Exception(f"Too many match history import errors ({errors})")

        conn.commit()
        self.imported_counts["match_scores"] = imported
        if winner_corrections > 0:
            self.log(
                f"✅ Imported {imported:,} match history records ({errors} errors, {winner_corrections} winner corrections)"
            )
        else:
            self.log(
                f"✅ Imported {imported:,} match history records ({errors} errors)"
            )

    def import_series_stats(self, conn, series_stats_data: List[Dict]):
        """Import series stats data with validation and calculation fallback"""
        self.log("📥 Importing series stats...")

        cursor = conn.cursor()
        imported = 0
        errors = 0
        league_not_found_count = 0
        skipped_count = 0

        # Debug: Check what leagues exist in the database
        cursor.execute("SELECT league_id FROM leagues ORDER BY league_id")
        existing_leagues = [row[0] for row in cursor.fetchall()]
        self.log(
            f"🔍 Debug: Found {len(existing_leagues)} leagues in database: {existing_leagues}"
        )

        for record in series_stats_data:
            try:
                series = record.get("series", "").strip()
                team = record.get("team", "").strip()
                raw_league_id = record.get("league_id", "").strip()
                league_id = normalize_league_id(raw_league_id) if raw_league_id else ""
                # FIXED: Don't trust imported points - calculate from match performance
                # points = record.get('points', 0)  # This data is often incorrect
                points = 0  # We'll calculate proper points from match data later

                # Extract match stats
                matches = record.get("matches", {})
                matches_won = matches.get("won", 0)
                matches_lost = matches.get("lost", 0)
                matches_tied = matches.get("tied", 0)

                # Extract line stats
                lines = record.get("lines", {})
                lines_won = lines.get("won", 0)
                lines_lost = lines.get("lost", 0)
                lines_for = lines.get("for", 0)
                lines_ret = lines.get("ret", 0)

                # Extract set stats
                sets = record.get("sets", {})
                sets_won = sets.get("won", 0)
                sets_lost = sets.get("lost", 0)

                # Extract game stats
                games = record.get("games", {})
                games_won = games.get("won", 0)
                games_lost = games.get("lost", 0)

                if not all([series, team, league_id]):
                    skipped_count += 1
                    continue

                # FIX: Handle series name format mismatches
                # Convert "Series X" to "Division X" for CNSWPL compatibility
                original_series = series
                if series.startswith("Series ") and league_id == "CNSWPL":
                    series = series.replace("Series ", "Division ")
                    self.log(
                        f"🔧 Converted series name: {record.get('series')} → {series} for team {team}"
                    )

                # Get league database ID with better error handling
                cursor.execute(
                    "SELECT id FROM leagues WHERE league_id = %s", (league_id,)
                )
                league_row = cursor.fetchone()

                if not league_row:
                    league_not_found_count += 1
                    if league_not_found_count <= 5:  # Only log first 5 missing leagues
                        self.log(
                            f"⚠️  League not found: {league_id} for team {team} (raw: {raw_league_id})",
                            "WARNING",
                        )
                    continue

                league_db_id = league_row[0]

                # Get team_id from teams table
                cursor.execute(
                    """
                    SELECT t.id FROM teams t
                    JOIN leagues l ON t.league_id = l.id
                    JOIN series s ON t.series_id = s.id
                    WHERE l.league_id = %s AND s.name = %s AND t.team_name = %s
                """,
                    (league_id, series, team),
                )

                team_row = cursor.fetchone()
                team_db_id = team_row[0] if team_row else None

                cursor.execute(
                    """
                    INSERT INTO series_stats (
                        series, team, team_id, points, matches_won, matches_lost, matches_tied,
                        lines_won, lines_lost, lines_for, lines_ret,
                        sets_won, sets_lost, games_won, games_lost,
                        league_id, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                    (
                        series,
                        team,
                        team_db_id,
                        points,
                        matches_won,
                        matches_lost,
                        matches_tied,
                        lines_won,
                        lines_lost,
                        lines_for,
                        lines_ret,
                        sets_won,
                        sets_lost,
                        games_won,
                        games_lost,
                        league_db_id,
                    ),
                )

                if cursor.rowcount > 0:
                    imported += 1

                # Commit more frequently to prevent transaction rollback issues
                if imported % 100 == 0:
                    conn.commit()

            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.log(
                        f"❌ Error importing series stats record: {str(e)}", "ERROR"
                    )

                if errors > 100:
                    self.log(
                        f"❌ Too many series stats errors ({errors}), stopping", "ERROR"
                    )
                    raise Exception(f"Too many series stats import errors ({errors})")

        conn.commit()
        self.imported_counts["series_stats"] = imported

        # Summary logging
        if league_not_found_count > 0:
            self.log(
                f"⚠️  {league_not_found_count} series stats records skipped due to missing leagues",
                "WARNING",
            )
        if skipped_count > 0:
            self.log(
                f"⚠️  {skipped_count} series stats records skipped due to missing data",
                "WARNING",
            )

        self.log(
            f"✅ Imported {imported:,} series stats records ({errors} errors, {league_not_found_count} missing leagues, {skipped_count} skipped)"
        )

        # CRITICAL: Always recalculate points after import to ensure accuracy
        self.recalculate_all_team_points(conn)

        # Validate the import results
        self.validate_series_stats_import(conn)

    def validate_series_stats_import(self, conn):
        """Validate series stats import and trigger calculation fallback if needed"""
        self.log("🔍 Validating series stats import...")

        cursor = conn.cursor()

        # Check total teams imported
        cursor.execute("SELECT COUNT(*) FROM series_stats")
        total_teams = cursor.fetchone()[0]

        # Check teams with matches in match_scores that should have series stats
        cursor.execute(
            """
            SELECT COUNT(DISTINCT COALESCE(home_team, away_team))
            FROM (
                SELECT home_team, NULL as away_team FROM match_scores WHERE home_team IS NOT NULL
                UNION ALL
                SELECT NULL as home_team, away_team FROM match_scores WHERE away_team IS NOT NULL
            ) all_teams
            WHERE COALESCE(home_team, away_team) IS NOT NULL
        """
        )
        expected_teams = cursor.fetchone()[0]

        # Calculate coverage percentage
        coverage_percentage = (
            (total_teams / expected_teams * 100) if expected_teams > 0 else 0
        )

        self.log(f"📊 Series stats validation:")
        self.log(f"   Imported teams: {total_teams:,}")
        self.log(f"   Expected teams: {expected_teams:,}")
        self.log(f"   Coverage: {coverage_percentage:.1f}%")

        # CRITICAL: If coverage is too low, trigger calculation fallback
        if coverage_percentage < 90:
            self.log(
                f"⚠️  WARNING: Series stats coverage ({coverage_percentage:.1f}%) is below 90% threshold",
                "WARNING",
            )
            self.log(
                f"🔧 Triggering calculation fallback to ensure data completeness..."
            )

            # Clear existing data and recalculate from match results
            self.calculate_series_stats_from_matches(conn)
        else:
            self.log(
                f"✅ Series stats validation passed ({coverage_percentage:.1f}% coverage)"
            )

    def recalculate_all_team_points(self, conn):
        """Recalculate points for all teams based on actual match performance"""
        self.log("🔧 Recalculating team points from match performance...")

        cursor = conn.cursor()

        # Get all teams in series_stats
        cursor.execute("SELECT id, team, league_id FROM series_stats")
        teams = cursor.fetchall()

        updated_count = 0

        for team_row in teams:
            team_id = team_row[0]  # id is first column
            team_name = team_row[1]  # team is second column
            league_id = team_row[2]  # league_id is third column

            # Calculate correct points from match history
            cursor.execute(
                """
                SELECT home_team, away_team, winner, scores
                FROM match_scores
                WHERE (home_team = %s OR away_team = %s)
                AND league_id = %s
            """,
                [team_name, team_name, league_id],
            )

            matches = cursor.fetchall()
            total_points = 0

            for match in matches:
                home_team = match[0]  # home_team is first column
                away_team = match[1]  # away_team is second column
                winner = match[2]  # winner is third column
                scores_str = match[3]  # scores is fourth column

                is_home = home_team == team_name
                won_match = (is_home and winner == "home") or (
                    not is_home and winner == "away"
                )

                # 1 point for winning the match
                if won_match:
                    total_points += 1

                # Additional points for sets won (even in losing matches)
                scores = scores_str.split(", ") if scores_str else []
                for score_str in scores:
                    if "-" in score_str:
                        try:
                            # Extract just the numbers before any tiebreak info
                            clean_score = score_str.split("[")[0].strip()
                            our_score, their_score = map(int, clean_score.split("-"))
                            if not is_home:  # Flip scores if we're away team
                                our_score, their_score = their_score, our_score
                            if our_score > their_score:
                                total_points += 1
                        except (ValueError, IndexError):
                            continue

            # Update the points in series_stats
            cursor.execute(
                """
                UPDATE series_stats 
                SET points = %s
                WHERE id = %s
            """,
                [total_points, team_id],
            )

            updated_count += 1

        conn.commit()
        self.log(f"✅ Recalculated points for {updated_count:,} teams")

    def calculate_series_stats_from_matches(self, conn):
        """Calculate series stats from match_scores data as fallback"""
        self.log("🧮 Calculating series stats from match results...")

        cursor = conn.cursor()

        # Clear existing series_stats data
        cursor.execute("DELETE FROM series_stats")
        self.log("   Cleared existing series_stats data")

        # Get all matches and calculate team statistics
        matches = cursor.execute(
            """
            SELECT home_team, away_team, winner, scores, league_id
            FROM match_scores
            WHERE home_team IS NOT NULL AND away_team IS NOT NULL
        """
        ).fetchall()

        from collections import defaultdict

        team_stats = defaultdict(
            lambda: {
                "matches_won": 0,
                "matches_lost": 0,
                "matches_tied": 0,
                "lines_won": 0,
                "lines_lost": 0,
                "sets_won": 0,
                "sets_lost": 0,
                "games_won": 0,
                "games_lost": 0,
                "points": 0,
                "league_id": None,
                "series": None,
            }
        )

        # Process each match to calculate team stats
        for match in matches:
            home_team = match[0]  # home_team is first column
            away_team = match[1]  # away_team is second column
            winner = match[2]  # winner is third column
            scores = match[3] or ""  # scores is fourth column
            league_id = match[4]  # league_id is fifth column

            # Determine series from team name
            def extract_series_from_team(team_name):
                if not team_name:
                    return "Division 1"
                parts = team_name.split()
                if parts:
                    last_part = parts[-1]
                    if last_part.isdigit():
                        return f"Division {last_part}"
                    elif len(last_part) >= 2 and last_part[:-1].isdigit():
                        return f"Division {last_part[:-1]}"
                return "Division 1"

            # Initialize team data
            if "series" not in team_stats[home_team]:
                team_stats[home_team]["series"] = extract_series_from_team(home_team)
                team_stats[home_team]["league_id"] = league_id
            if "series" not in team_stats[away_team]:
                team_stats[away_team]["series"] = extract_series_from_team(away_team)
                team_stats[away_team]["league_id"] = league_id

            # Parse scores for detailed statistics
            def parse_scores(scores_str, is_home_perspective):
                if not scores_str:
                    return 0, 0, 0, 0
                sets = scores_str.split(", ")
                team_sets = opponent_sets = 0
                team_games = opponent_games = 0

                for set_score in sets:
                    if "-" in set_score:
                        try:
                            score1, score2 = map(int, set_score.split("-"))
                            if is_home_perspective:
                                team_games += score1
                                opponent_games += score2
                                if score1 > score2:
                                    team_sets += 1
                                else:
                                    opponent_sets += 1
                            else:
                                team_games += score2
                                opponent_games += score1
                                if score2 > score1:
                                    team_sets += 1
                                else:
                                    opponent_sets += 1
                        except ValueError:
                            continue

                return team_sets, opponent_sets, team_games, opponent_games

            # Calculate stats for both teams
            home_sets, away_sets, home_games, away_games = parse_scores(scores, True)
            away_sets, home_sets_check, away_games, home_games_check = parse_scores(
                scores, False
            )

            # Determine match winner and update stats
            if winner and winner.lower() == "home":
                team_stats[home_team]["matches_won"] += 1
                team_stats[away_team]["matches_lost"] += 1
                team_stats[home_team]["points"] += 1  # 1 point for match win
            elif winner and winner.lower() == "away":
                team_stats[away_team]["matches_won"] += 1
                team_stats[home_team]["matches_lost"] += 1
                team_stats[away_team]["points"] += 1  # 1 point for match win
            else:
                team_stats[home_team]["matches_tied"] += 1
                team_stats[away_team]["matches_tied"] += 1

            # FIXED: Add points for sets won (even in losing matches)
            team_stats[home_team]["points"] += home_sets  # Points for sets won
            team_stats[away_team]["points"] += away_sets  # Points for sets won

            # Update detailed stats
            team_stats[home_team]["sets_won"] += home_sets
            team_stats[home_team]["sets_lost"] += away_sets
            team_stats[home_team]["games_won"] += home_games
            team_stats[home_team]["games_lost"] += away_games
            team_stats[home_team]["lines_won"] += home_sets
            team_stats[home_team]["lines_lost"] += away_sets

            team_stats[away_team]["sets_won"] += away_sets
            team_stats[away_team]["sets_lost"] += home_sets
            team_stats[away_team]["games_won"] += away_games
            team_stats[away_team]["games_lost"] += home_games
            team_stats[away_team]["lines_won"] += away_sets
            team_stats[away_team]["lines_lost"] += home_sets

        # Insert calculated stats into database
        calculated_count = 0
        for team_name, stats in team_stats.items():
            try:
                cursor.execute(
                    """
                    INSERT INTO series_stats (
                        series, team, league_id, points,
                        matches_won, matches_lost, matches_tied,
                        lines_won, lines_lost,
                        sets_won, sets_lost,
                        games_won, games_lost,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                    [
                        stats["series"],
                        team_name,
                        stats["league_id"],
                        stats["points"],
                        stats["matches_won"],
                        stats["matches_lost"],
                        stats["matches_tied"],
                        stats["lines_won"],
                        stats["lines_lost"],
                        stats["sets_won"],
                        stats["sets_lost"],
                        stats["games_won"],
                        stats["games_lost"],
                    ],
                )
                calculated_count += 1
            except Exception as e:
                self.log(
                    f"❌ Error inserting calculated stats for {team_name}: {e}", "ERROR"
                )

        conn.commit()
        self.log(
            f"✅ Calculated and inserted {calculated_count:,} team statistics from match data"
        )
        self.imported_counts["series_stats"] = calculated_count

    def import_schedules(self, conn, schedules_data: List[Dict]):
        """Import schedules data"""
        self.log("📥 Importing schedules...")

        cursor = conn.cursor()
        imported = 0
        errors = 0

        for record in schedules_data:
            try:
                date_str = record.get("date", "").strip()
                time_str = record.get("time", "").strip()
                home_team = record.get("home_team", "").strip()
                away_team = record.get("away_team", "").strip()
                location = record.get("location", "").strip()
                raw_league_id = record.get("League", "").strip()
                league_id = normalize_league_id(raw_league_id) if raw_league_id else ""

                # Parse date
                match_date = None
                if date_str:
                    try:
                        match_date = datetime.strptime(date_str, "%m/%d/%Y").date()
                    except ValueError:
                        try:
                            match_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        except ValueError:
                            pass

                # Handle empty time fields - convert to None for PostgreSQL TIME column
                match_time = None
                if time_str:
                    match_time = time_str

                if not all([match_date, home_team, away_team]):
                    continue

                # Get league database ID
                cursor.execute(
                    "SELECT id FROM leagues WHERE league_id = %s", (league_id,)
                )
                league_row = cursor.fetchone()
                league_db_id = league_row[0] if league_row else None

                # Get team IDs from teams table
                home_team_id = None
                away_team_id = None

                if home_team and home_team != "BYE":
                    cursor.execute(
                        """
                        SELECT t.id FROM teams t
                        JOIN leagues l ON t.league_id = l.id
                        WHERE l.league_id = %s AND t.team_name = %s
                    """,
                        (league_id, home_team),
                    )
                    home_team_row = cursor.fetchone()
                    home_team_id = home_team_row[0] if home_team_row else None

                if away_team and away_team != "BYE":
                    cursor.execute(
                        """
                        SELECT t.id FROM teams t
                        JOIN leagues l ON t.league_id = l.id
                        WHERE l.league_id = %s AND t.team_name = %s
                    """,
                        (league_id, away_team),
                    )
                    away_team_row = cursor.fetchone()
                    away_team_id = away_team_row[0] if away_team_row else None

                cursor.execute(
                    """
                    INSERT INTO schedule (
                        match_date, match_time, home_team, away_team, home_team_id, away_team_id,
                        location, league_id, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                    (
                        match_date,
                        match_time,
                        home_team,
                        away_team,
                        home_team_id,
                        away_team_id,
                        location,
                        league_db_id,
                    ),
                )

                if cursor.rowcount > 0:
                    imported += 1

                if imported % 1000 == 0:
                    self.log(f"   📊 Imported {imported:,} schedule records so far...")
                    conn.commit()

            except Exception as e:
                errors += 1
                if errors <= 10:
                    self.log(f"❌ Error importing schedule record: {str(e)}", "ERROR")

                if errors > 100:
                    self.log(
                        f"❌ Too many schedule errors ({errors}), stopping", "ERROR"
                    )
                    raise Exception(f"Too many schedule import errors ({errors})")

        conn.commit()
        self.imported_counts["schedule"] = imported
        self.log(f"✅ Imported {imported:,} schedule records ({errors} errors)")

    def _parse_int(self, value: str) -> int:
        """Parse integer with error handling"""
        if not value or value.strip() == "":
            return 0
        try:
            return int(str(value).strip())
        except (ValueError, TypeError):
            return 0

    def print_summary(self):
        """Print import summary"""
        self.log("=" * 60)
        self.log("📊 IMPORT SUMMARY")
        self.log("=" * 60)

        total_imported = 0
        for table, count in self.imported_counts.items():
            self.log(f"   {table:<20}: {count:>10,} records")
            total_imported += count

        self.log("-" * 60)
        self.log(f"   {'TOTAL':<20}: {total_imported:>10,} records")

        if self.errors:
            self.log(f"\n⚠️  {len(self.errors)} errors encountered during import")

    def run(self):
        """Run the complete ETL process"""
        start_time = datetime.now()

        try:
            self.log("🚀 Starting Comprehensive JSON ETL Process")
            self.log("=" * 60)

            # Step 1: Load all JSON files
            self.log("📂 Step 1: Loading JSON files...")
            players_data = self.load_json_file("players.json")
            player_history_data = self.load_json_file("player_history.json")
            match_history_data = self.load_json_file("match_history.json")
            series_stats_data = self.load_json_file("series_stats.json")
            schedules_data = self.load_json_file("schedules.json")

            # Step 2: Extract reference data from players.json
            self.log("\n📋 Step 2: Extracting reference data...")
            leagues_data = self.extract_leagues(
                players_data, series_stats_data, schedules_data
            )
            clubs_data = self.extract_clubs(players_data)
            series_data = self.extract_series(
                players_data, series_stats_data, schedules_data
            )
            club_league_rels = self.analyze_club_league_relationships(players_data)
            series_league_rels = self.analyze_series_league_relationships(players_data)

            # Step 2b: Extract teams from series stats and schedules
            self.log("\n🏗️  Step 2b: Extracting teams...")
            teams_data = self.extract_teams(series_stats_data, schedules_data)

            # Step 3: Connect to database and import
            self.log("\n🗄️  Step 3: Connecting to database...")
            with get_db() as conn:
                try:
                    # Clear existing data
                    self.clear_target_tables(conn)

                    # Import in correct order
                    self.log("\n📥 Step 4: Importing data in dependency order...")

                    self.import_leagues(conn, leagues_data)
                    self.import_clubs(conn, clubs_data)
                    self.import_series(conn, series_data)
                    self.import_club_leagues(conn, club_league_rels)
                    self.import_series_leagues(conn, series_league_rels)
                    self.import_teams(
                        conn, teams_data
                    )  # NEW: Import teams before players
                    self.import_players(conn, players_data)
                    self.import_career_stats(conn, player_history_data)
                    self.import_player_history(conn, player_history_data)
                    self.import_match_history(conn, match_history_data)
                    self.import_series_stats(conn, series_stats_data)
                    self.import_schedules(conn, schedules_data)

                    # Success!
                    self.log("\n✅ ETL process completed successfully!")

                except Exception as e:
                    self.log(f"\n❌ ETL process failed: {str(e)}", "ERROR")
                    self.log("🔄 Rolling back all changes...", "WARNING")
                    conn.rollback()
                    raise

        except Exception as e:
            self.log(f"\n💥 CRITICAL ERROR: {str(e)}", "ERROR")
            self.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            return False

        finally:
            end_time = datetime.now()
            duration = end_time - start_time

            self.log(f"\n⏱️  Total execution time: {duration}")
            self.print_summary()

        return True


def main():
    """Main entry point"""
    etl = ComprehensiveETL()
    success = etl.run()

    if success:
        print("\n🎉 ETL process completed successfully!")
        return 0
    else:
        print("\n💥 ETL process failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
