#!/usr/bin/env python3
"""
Import Stats with Comprehensive Validation and Data Integrity Prevention

This script imports team statistics from series_stats.json files with built-in validation
and ensures all stats are properly mapped to teams and series.

Usage:
    python3 data/etl/import/import_stats.py <LEAGUE_KEY> [--file <JSON_FILE>] [--limit <N>]
"""

import sys
import json
import argparse
import re
from datetime import datetime
import os
import psycopg2
from typing import Optional

# Add the project root to Python path to import database_config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from database_config import get_db_url, get_database_mode, is_local_development

# Club name normalization patterns (shared across all import scripts)
_ROMAN_RE = re.compile(r'\b[IVXLCDM]{1,4}\b', re.IGNORECASE)
_ALNUM_SUFFIX_RE = re.compile(r'\b(\d+[A-Za-z]?|[A-Za-z]?\d+)\b')
_LETTER_PAREN_RE = re.compile(r'\b[A-Za-z]{1,3}\(\d+\)\b')
_ALLCAP_SHORT_RE = re.compile(r'\b[A-Z]{1,3}\b')
_KEEP_SUFFIXES = {"CC", "GC", "RC", "PC", "TC", "AC"}

def normalize_club_name(raw: str) -> str:
    """
    Normalize club names using consistent logic across all import scripts.
    
    Rules:
    1. Trim and normalize internal whitespace
    2. If name contains " - " segments, keep only the first segment
    3. Drop trailing parenthetical segments
    4. Strip trailing team/series suffix tokens
    5. Remove stray punctuation except & and spaces
    6. Collapse multiple spaces and strip ends
    7. Title-case result (preserving club-type abbreviations)
    """
    if not raw:
        return ""
    
    # Trim and normalize whitespace
    name = re.sub(r'\s+', ' ', raw.strip())
    
    # Keep only first segment if " - " exists
    if " - " in name:
        name = name.split(" - ")[0].strip()
    
    # Drop trailing parenthetical segments
    name = re.sub(r'\s*\([^)]*\)\s*$', '', name)
    
    # Strip trailing suffix tokens
    tokens = name.split()
    tokens = _strip_trailing_suffix_tokens(tokens)
    name = ' '.join(tokens)
    
    # Remove stray punctuation except & and spaces
    name = re.sub(r'[^\w\s&]', '', name)
    
    # Collapse spaces and strip
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Title-case while preserving club-type abbreviations
    words = name.split()
    title_words = []
    for word in words:
        if word.upper() in _KEEP_SUFFIXES:
            title_words.append(word.upper())
        else:
            title_words.append(word.title())
    
    return ' '.join(title_words)

def _strip_trailing_suffix_tokens(tokens: list[str]) -> list[str]:
    """Strip trailing series/division/team markers without using hard-coded club maps."""
    while tokens:
        t = tokens[-1]
        
        # Preserve common club-type suffixes
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

def get_conn():
    """Get database connection using database_config for automatic environment detection."""
    try:
        return psycopg2.connect(get_db_url())
    except Exception as e:
        raise ValueError(f"Database connection failed: {e}")

def get_league_id(cur, league_key):
    """Get league ID from database using league_id or league_name."""
    cur.execute(
        "SELECT id FROM leagues WHERE league_id = %s OR league_name = %s LIMIT 1",
        (league_key, league_key)
    )
    result = cur.fetchone()
    if not result:
        raise ValueError(f"League '{league_key}' not found in database")
    return result[0]

def column_exists(cur, table, column):
    """Check if a column exists in a table."""
    cur.execute("""
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = %s AND column_name = %s LIMIT 1
    """, (table, column))
    return cur.fetchone() is not None

def parse_datetime_safe(datetime_str):
    """Parse datetime string safely."""
    if not datetime_str:
        return None
    try:
        return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            return datetime.strptime(datetime_str, "%Y-%m-%d")
        except ValueError:
            return None

def validate_entity_name(name, entity_type):
    """Validate entity names to prevent anomalies."""
    if not name or not isinstance(name, str):
        return False, f"Invalid {entity_type} name: {name}"
    
    name = name.strip()
    if not name:
        return False, f"Empty {entity_type} name"
    
    # Prevent numeric names
    if re.match(r'^[0-9]+\.?[0-9]*$', name):
        return False, f"Invalid {entity_type} name '{name}' - appears to be a numeric value"
    
    # Prevent names that are just numbers
    if re.match(r'^[0-9]+$', name):
        return False, f"Invalid {entity_type} name '{name}' - appears to be just a number"
    
    # Prevent names that are too short
    if len(name) < 2:
        return False, f"Invalid {entity_type} name '{name}' - too short (minimum 2 characters)"
    
    # Prevent names that are too long
    if len(name) > 100:
        return False, f"Invalid {entity_type} name '{name}' - too long (maximum 100 characters)"
    
    return True, name

def validate_stat_data(stat_data):
    """Validate stat data to ensure quality and prevent anomalies."""
    errors = []
    
    # Check required fields
    series = stat_data.get("series", "").strip()
    team = stat_data.get("team", "").strip()
    
    if not series:
        errors.append("Missing series")
    else:
        is_valid, series_error = validate_entity_name(series, "Series")
        if not is_valid:
            errors.append(f"Series: {series_error}")
    
    if not team:
        errors.append("Missing team")
    else:
        is_valid, team_error = validate_entity_name(team, "Team")
        if not is_valid:
            errors.append(f"Team: {team_error}")
    
    # Validate statistics - handle both detailed and simple formats
    if "matches" in stat_data and isinstance(stat_data.get("matches"), dict):
        # Detailed format with nested objects
        matches = stat_data.get("matches", {})
        if not isinstance(matches, dict):
            errors.append("Invalid matches object")
        else:
            # Validate match statistics
            for key in ["won", "lost", "tied"]:
                if key in matches:
                    value = matches[key]
                    if not isinstance(value, (int, float)) or value < 0:
                        errors.append(f"Invalid matches.{key}: {value} (must be non-negative number)")
        
        lines = stat_data.get("lines", {})
        if not isinstance(lines, dict):
            errors.append("Invalid lines object")
        else:
            # Validate line statistics
            for key in ["won", "lost"]:
                if key in lines:
                    value = lines[key]
                    if not isinstance(value, (int, float)) or value < 0:
                        errors.append(f"Invalid lines.{key}: {value} (must be non-negative number)")
        
        sets = stat_data.get("sets", {})
        if not isinstance(sets, dict):
            errors.append("Invalid sets object")
        else:
            # Validate set statistics
            for key in ["won", "lost"]:
                if key in sets:
                    value = sets[key]
                    if not isinstance(value, (int, float)) or value < 0:
                        errors.append(f"Invalid sets.{key}: {value} (must be non-negative number)")
        
        games = stat_data.get("games", {})
        if not isinstance(games, dict):
            errors.append("Invalid games object")
        else:
            # Validate game statistics
            for key in ["won", "lost"]:
                if key in games:
                    value = games[key]
                    if not isinstance(value, (int, float)) or value < 0:
                        errors.append(f"Invalid games.{key}: {value} (must be non-negative number)")
    else:
        # Simple format with wins/losses at top level
        for key in ["wins", "losses", "tied"]:
            if key in stat_data:
                value = stat_data[key]
                if not isinstance(value, (int, float)) or value < 0:
                    errors.append(f"Invalid {key}: {value} (must be non-negative number)")
        
        # Validate optional detailed fields if present
        for key in ["lines_won", "lines_lost", "sets_won", "sets_lost", "games_won", "games_lost"]:
            if key in stat_data:
                value = stat_data[key]
                if not isinstance(value, (int, float)) or value < 0:
                    errors.append(f"Invalid {key}: {value} (must be non-negative number)")
    
    return len(errors) == 0, errors

def parse_team_name(team_name):
    """
    Parse team name to extract club, series, and team number/letter.
    Handles both numeric and letter-based series.
    
    Examples:
    - "Birchwood 12" -> ("Birchwood", "Series 12", "12")
    - "Exmoor I" -> ("Exmoor", "Series I", "I") 
    - "Winnetka D" -> ("Winnetka", "Series D", "D")
    - "Tennaqua A" -> ("Tennaqua", "Series A", "A")
    - "Michigan Shores 3b" -> ("Michigan Shores", "Series 3b", "3b")
    - "Lake Forest 22" -> ("Lake Forest", "Series 22", "22")
    - "Glen Ellyn - 7 SW" -> ("Glen Ellyn", "Chicago 7 SW", "7 SW")
    """
    if not team_name:
        return None, None, None
    
    # Handle special cases with dashes and complex names
    if " - " in team_name:
        parts = team_name.split(" - ")
        if len(parts) == 2:
            club_name = parts[0].strip()
            series_part = parts[1].strip()
            # For cases like "Glen Ellyn - 7 SW", use the full series part
            return club_name, series_part, series_part
    
    # Try to extract numeric series first (e.g., "12", "3b", "14a")
    numeric_match = re.search(r'(\d+[a-z]?)$', team_name)
    if numeric_match:
        team_number = numeric_match.group(1)
        club_name = team_name[:numeric_match.start()].strip()
        series_name = f"Series {team_number}"
        return club_name, series_name, team_number
    
    # Try to extract single letter series (e.g., "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K")
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
    
    # Fallback: try to extract any alphanumeric suffix
    suffix_match = re.search(r'\s([A-Za-z0-9]+)\s*$', team_name)
    if suffix_match:
        team_suffix = suffix_match.group(1)
        club_name = team_name[:suffix_match.start()].strip()
        series_name = f"Series {team_suffix}"
        return club_name, series_name, team_suffix
    
    # If no pattern matches, assume the entire string is the club name
    # and create a generic series
    return team_name.strip(), "Series 1", "1"

def upsert_club(cur, name, league_id):
    """Upsert club and return ID."""
    if not name:
        return None
    
    # Check if clubs table has league_id column
    if column_exists(cur, "clubs", "league_id"):
        # Direct league_id column
        cur.execute("""
            INSERT INTO clubs (name, league_id) 
            VALUES (%s, %s) 
            ON CONFLICT (name, league_id) DO NOTHING 
            RETURNING id
        """, (name, league_id))
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Get existing ID
        cur.execute("SELECT id FROM clubs WHERE name = %s AND league_id = %s", (name, league_id))
        return cur.fetchone()[0]
    else:
        # Use club_leagues junction table
        # First, try to insert the club
        cur.execute("INSERT INTO clubs (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id", (name,))
        result = cur.fetchone()
        
        if result:
            # New club was created
            club_id = result[0]
        else:
            # Club already exists, get its ID
            cur.execute("SELECT id FROM clubs WHERE name = %s", (name,))
            club_id = cur.fetchone()[0]
        
        # Check if club-league relationship already exists
        cur.execute("SELECT 1 FROM club_leagues WHERE club_id = %s AND league_id = %s", (club_id, league_id))
        if not cur.fetchone():
            # Create club-league relationship only if it doesn't exist
            cur.execute("INSERT INTO club_leagues (club_id, league_id) VALUES (%s, %s)", (club_id, league_id))
        
        return club_id

def upsert_series(cur, name, league_id):
    """Upsert series and return ID."""
    if not name:
        return None
    
    # Check if series table has display_name column
    if column_exists(cur, "series", "display_name"):
        cur.execute("""
            INSERT INTO series (name, display_name, league_id) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (name, league_id) DO NOTHING 
            RETURNING id
        """, (name, name, league_id))
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Get existing ID
        cur.execute("SELECT id FROM series WHERE name = %s AND league_id = %s", (name, league_id))
        return cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO series (name, league_id) 
            VALUES (%s, %s) 
            ON CONFLICT (name, league_id) DO NOTHING 
            RETURNING id
        """, (name, league_id))
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Get existing ID
        cur.execute("SELECT id FROM series WHERE name = %s AND league_id = %s", (name, league_id))
        return cur.fetchone()[0]

def upsert_team(cur, league_id, team_name, club_name, series_name):
    """Upsert team and return ID using unified team management logic."""
    if not all([team_name, club_name, series_name]):
        return None
    
    # Normalize club name for consistency
    normalized_club_name = normalize_club_name(club_name)
    
    # Get or create club with normalized name
    club_id = upsert_club(cur, normalized_club_name, league_id)
    if not club_id:
        return None
    
    # Get or create series
    series_id = upsert_series(cur, series_name, league_id)
    if not series_id:
        return None
    
    # Check if team already exists
    existing_team_id = find_existing_team_unified(cur, league_id, team_name, club_id, series_id)
    if existing_team_id:
        return existing_team_id
    
    # Create new team with consistent naming
    return create_team_unified(cur, team_name, club_id, series_id, league_id)

def lookup_existing_team(cur, league_id, team_name):
    """Look up existing team by name in the current league using unified logic."""
    team_id = find_team_by_name_unified(cur, league_id, team_name)
    
    if team_id:
        # Get club_id and series_id for backward compatibility
        cur.execute("""
            SELECT club_id, series_id FROM teams 
            WHERE id = %s
        """, (team_id,))
        result = cur.fetchone()
        if result:
            return team_id, result[0], result[1]
    
    return None, None, None

def find_existing_team_unified(cur, league_id, team_name: str, club_id: int, series_id: int):
    """Find existing team using multiple strategies."""
    # Strategy 1: Exact team name match
    cur.execute("""
        SELECT id FROM teams 
        WHERE team_name = %s AND league_id = %s
    """, (team_name, league_id))
    result = cur.fetchone()
    if result:
        return result[0]
    
    # Strategy 2: Match by club_id and series_id (for teams with same club/series)
    cur.execute("""
        SELECT id, team_name FROM teams 
        WHERE club_id = %s AND series_id = %s AND league_id = %s
    """, (club_id, series_id, league_id))
    results = cur.fetchall()
    
    if len(results) == 1:
        # Only one team for this club/series combination
        return results[0][0]
    elif len(results) > 1:
        # Multiple teams for same club/series - need to match by name pattern
        for team_id, existing_team_name in results:
            if team_names_match_unified(team_name, existing_team_name):
                return team_id
    
    return None

def find_team_by_name_unified(cur, league_id, team_name: str):
    """Find existing team by name using multiple strategies."""
    if not team_name:
        return None
    
    # Strategy 1: Exact match
    cur.execute("""
        SELECT id FROM teams 
        WHERE team_name = %s AND league_id = %s
    """, (team_name, league_id))
    result = cur.fetchone()
    if result:
        return result[0]
    
    # Strategy 2: Parse and match by components
    raw_club_name, series_name, _ = parse_team_name(team_name)
    if raw_club_name and series_name:
        club_name = normalize_club_name(raw_club_name)
        
        cur.execute("""
            SELECT t.id FROM teams t
            JOIN clubs c ON t.club_id = c.id
            JOIN series s ON t.series_id = s.id
            WHERE c.name = %s AND s.name = %s AND t.league_id = %s
        """, (club_name, series_name, league_id))
        
        results = cur.fetchall()
        if len(results) == 1:
            return results[0][0]
        elif len(results) > 1:
            # Multiple teams for same club/series - try to match by name pattern
            for (team_id,) in results:
                cur.execute("SELECT team_name FROM teams WHERE id = %s", (team_id,))
                existing_name = cur.fetchone()[0]
                if team_names_match_unified(team_name, existing_name):
                    return team_id
    
    return None

def team_names_match_unified(name1: str, name2: str) -> bool:
    """Check if two team names refer to the same team."""
    # Normalize both names for comparison
    norm1 = normalize_club_name(name1).lower()
    norm2 = normalize_club_name(name2).lower()
    
    # Extract team identifiers
    _, _, id1 = parse_team_name(name1)
    _, _, id2 = parse_team_name(name2)
    
    # If team identifiers match, they're the same team
    if id1 and id2 and id1.lower() == id2.lower():
        return True
    
    # If normalized names are identical, they're the same team
    if norm1 == norm2:
        return True
    
    return False

def create_team_unified(cur, team_name: str, club_id: int, series_id: int, league_id) -> Optional[int]:
    """Create a new team with consistent naming."""
    try:
        cur.execute("""
            INSERT INTO teams (team_name, display_name, club_id, series_id, league_id) 
            VALUES (%s, %s, %s, %s, %s) 
            RETURNING id
        """, (team_name, team_name, club_id, series_id, league_id))
        
        result = cur.fetchone()
        if result:
            return result[0]
    except Exception as e:
        print(f"Failed to create team '{team_name}': {str(e)}")
    
    return None

def check_existing_stat(cur, league_id, team_id, series_name):
    """Check if a stat record already exists."""
    cur.execute("""
        SELECT id FROM series_stats 
        WHERE league_id = %s AND team_id = %s AND series = %s
    """, (league_id, team_id, series_name))
    
    result = cur.fetchone()
    return result[0] if result else None

def upsert_stat(cur, league_id, stat_data):
    """Upsert a single stat record with comprehensive validation."""
    # Validate data first
    is_valid, validation_errors = validate_stat_data(stat_data)
    if not is_valid:
        return None, f"validation_failed: {', '.join(validation_errors)}"
    
    series_name = stat_data.get("series", "").strip()
    team_name = stat_data.get("team", "").strip()
    
    # Parse team name to get club and series
    club_name, parsed_series_name, team_number = parse_team_name(team_name)
    if not all([club_name, parsed_series_name]):
        return None, f"team_parsing_failed: could not extract club/series from '{team_name}'"
    
    # Use the series from the data, not the parsed one
    if series_name != parsed_series_name:
        print(f"  ⚠️ Series mismatch: data has '{series_name}', parsed '{parsed_series_name}' from team '{team_name}'")
    
    try:
        # Ensure team exists (create if needed)
        team_id, club_id, series_id = lookup_existing_team(cur, league_id, team_name)
        
        if not team_id:
            print(f"  ⚠️ Team '{team_name}' not found. Attempting to create.")
            team_id = upsert_team(cur, league_id, team_name, club_name, series_name)
            if not team_id:
                return None, f"team_creation_failed: could not create team '{team_name}'"
            else:
                print(f"  Team '{team_name}' created.")
        else:
            print(f"  Team '{team_name}' found (ID: {team_id}).")
        
        # Get series_id
        series_id = upsert_series(cur, series_name, league_id)
        if not series_id:
            return None, f"series_creation_failed: could not create series '{series_name}'"
        
        # Extract stat values - handle both detailed and simple formats
        points = stat_data.get("points")
        
        # Check if we have detailed stats (nested objects) or simple stats (flat structure)
        if "matches" in stat_data and isinstance(stat_data.get("matches"), dict):
            # Detailed format with nested objects
            matches_won = stat_data.get("matches", {}).get("won")
            matches_lost = stat_data.get("matches", {}).get("lost")
            matches_tied = stat_data.get("matches", {}).get("tied")
            lines_won = stat_data.get("lines", {}).get("won")
            lines_lost = stat_data.get("lines", {}).get("lost")
            sets_won = stat_data.get("sets", {}).get("won")
            sets_lost = stat_data.get("sets", {}).get("lost")
            games_won = stat_data.get("games", {}).get("won")
            games_lost = stat_data.get("games", {}).get("lost")
        else:
            # Simple format with wins/losses at top level
            matches_won = stat_data.get("wins")
            matches_lost = stat_data.get("losses")
            matches_tied = stat_data.get("tied", 0)  # Default to 0 if not present
            lines_won = stat_data.get("lines_won", 0)  # Default to 0 if not present
            lines_lost = stat_data.get("lines_lost", 0)  # Default to 0 if not present
            sets_won = stat_data.get("sets_won", 0)  # Default to 0 if not present
            sets_lost = stat_data.get("sets_lost", 0)  # Default to 0 if not present
            games_won = stat_data.get("games_won", 0)  # Default to 0 if not present
            games_lost = stat_data.get("games_lost", 0)  # Default to 0 if not present
        
        # Handle None values by converting to 0 for database
        points = points if points is not None else 0
        matches_won = matches_won if matches_won is not None else 0
        matches_lost = matches_lost if matches_lost is not None else 0
        matches_tied = matches_tied if matches_tied is not None else 0
        lines_won = lines_won if lines_won is not None else 0
        lines_lost = lines_lost if lines_lost is not None else 0
        sets_won = sets_won if sets_won is not None else 0
        sets_lost = sets_lost if sets_lost is not None else 0
        games_won = games_won if games_won is not None else 0
        games_lost = games_lost if games_lost is not None else 0
        
        # Check if external_id column exists
        has_external_id = column_exists(cur, "series_stats", "external_id")
        
        if has_external_id:
            # Create a unique external_id from team + series + metric combination
            external_id = f"{team_name}_{series_name}_comprehensive"
            
            # Use external_id for upsert
            cur.execute("""
                INSERT INTO series_stats (league_id, series_id, team_id, series, team, points,
                                        matches_won, matches_lost, matches_tied, 
                                        lines_won, lines_lost, sets_won, sets_lost, games_won, games_lost, external_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (external_id)
                DO UPDATE SET 
                    series_id = EXCLUDED.series_id, 
                    team_id = EXCLUDED.team_id,
                    series = EXCLUDED.series,
                    team = EXCLUDED.team,
                    points = EXCLUDED.points,
                    matches_won = EXCLUDED.matches_won,
                    matches_lost = EXCLUDED.matches_lost,
                    matches_tied = EXCLUDED.matches_tied,
                    lines_won = EXCLUDED.lines_won,
                    lines_lost = EXCLUDED.lines_lost,
                    sets_won = EXCLUDED.sets_won,
                    sets_lost = EXCLUDED.sets_lost,
                    games_won = EXCLUDED.games_won,
                    games_lost = EXCLUDED.games_lost
                RETURNING id
            """, (league_id, series_id, team_id, series_name, team_name, points,
                  matches_won, matches_lost, matches_tied,
                  lines_won, lines_lost, sets_won, sets_lost, games_won, games_lost, external_id))
            
            result = cur.fetchone()
            if result:
                if cur.rowcount > 1:  # UPDATE
                    return result[0], "updated"
                else:  # INSERT
                    return result[0], "inserted"
        else:
            # Use UPSERT with the unique constraint (league_id, series, team)
            cur.execute("""
                INSERT INTO series_stats (league_id, series_id, team_id, series, team, points,
                                        matches_won, matches_lost, matches_tied, 
                                        lines_won, lines_lost, sets_won, sets_lost, games_won, games_lost)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (league_id, series, team)
                DO UPDATE SET 
                    series_id = EXCLUDED.series_id, 
                    team_id = EXCLUDED.team_id,
                    points = EXCLUDED.points,
                    matches_won = EXCLUDED.matches_won,
                    matches_lost = EXCLUDED.matches_lost,
                    matches_tied = EXCLUDED.matches_tied,
                    lines_won = EXCLUDED.lines_won,
                    lines_lost = EXCLUDED.lines_lost,
                    sets_won = EXCLUDED.sets_won,
                    sets_lost = EXCLUDED.sets_lost,
                    games_won = EXCLUDED.games_won,
                    games_lost = EXCLUDED.games_lost
                RETURNING id
            """, (league_id, series_id, team_id, series_name, team_name, points,
                  matches_won, matches_lost, matches_tied,
                  lines_won, lines_lost, sets_won, sets_lost, games_won, games_lost))
            
            result = cur.fetchone()
            if result:
                # Check if this was an insert or update by looking at the row count
                if cur.rowcount == 1:
                    return result[0], "inserted"
                else:
                    return result[0], "updated"
            else:
                return None, "upsert_failed"
        
    except Exception as e:
        raise Exception(f"Failed to upsert stat for team '{team_name}', series '{series_name}': {e}")

def run_integrity_checks(cur, league_id):
    """Run post-import integrity checks."""
    print("\n🔍 Running post-import integrity checks...")
    
    issues_found = 0
    
    # Check for stats with missing team assignments
    cur.execute("""
        SELECT COUNT(*) FROM series_stats s
        LEFT JOIN teams t ON s.team_id = t.id
        WHERE s.league_id = %s AND t.id IS NULL
    """, (league_id,))
    
    missing_teams = cur.fetchone()[0]
    if missing_teams > 0:
        print(f"  ⚠️ Found {missing_teams} stats with missing team assignments")
        issues_found += missing_teams
    else:
        print("  ✅ All stats have proper team assignments")
    
    # Check for stats with missing series assignments
    cur.execute("""
        SELECT COUNT(*) FROM series_stats s
        LEFT JOIN series ser ON s.series_id = ser.id
        WHERE s.league_id = %s AND ser.id IS NULL
    """, (league_id,))
    
    missing_series = cur.fetchone()[0]
    if missing_series > 0:
        print(f"  ⚠️ Found {missing_series} stats with missing series assignments")
        issues_found += missing_series
    else:
        print("  ✅ All stats have proper series assignments")
    
    # Check for duplicate stats
    cur.execute("""
        SELECT team_id, series, COUNT(*) as count
        FROM series_stats 
        WHERE league_id = %s 
        GROUP BY team_id, series 
        HAVING COUNT(*) > 1
        ORDER BY count DESC
    """, (league_id,))
    
    duplicates = cur.fetchall()
    if duplicates:
        print(f"  ❌ Found {len(duplicates)} duplicate stat records")
        for team_id, series, count in duplicates[:5]:  # Show first 5
            print(f"    Team ID {team_id}, Series '{series}': {count} records")
        if len(duplicates) > 5:
            print(f"    ... and {len(duplicates) - 5} more")
        issues_found += len(duplicates)
    else:
        print("  ✅ No duplicate stat records found")
    
    # Check for teams with missing stats
    cur.execute("""
        SELECT COUNT(*) FROM teams t
        LEFT JOIN series_stats s ON t.id = s.team_id
        WHERE t.league_id = %s AND s.id IS NULL
    """, (league_id,))
    
    teams_without_stats = cur.fetchone()[0]
    if teams_without_stats > 0:
        print(f"  ⚠️ Found {teams_without_stats} teams with no stats")
        issues_found += teams_without_stats
    else:
        print("  ✅ All teams have stats")
    
    print(f"\n📊 Integrity check summary: {issues_found} issues found")
    return issues_found

def load_json_file(file_path):
    """Load and validate JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            raise ValueError("JSON data must be a list")
        
        return data
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    except Exception as e:
        raise Exception(f"Error loading file: {e}")

def import_stats(league_key, file_path=None, limit=None):
    """Import stats for a specific league with comprehensive validation."""
    print(f"Importing stats for league: {league_key}")
    
    # Show environment information
    print(f"Environment: {'Local Development' if is_local_development() else 'Railway/Production'}")
    print(f"Database Mode: {get_database_mode()}")
    print(f"Database URL: {get_db_url()}")
    print()
    
    # Determine input file
    if file_path:
        input_file = file_path
    else:
        input_file = f"data/leagues/{league_key}/series_stats.json"
    
    print(f"Input file: {input_file}")
    
    # Load stats data
    print("Loading stats data...")
    stats_data = load_json_file(input_file)
    print(f"Loaded {len(stats_data)} stat records")
    
    if limit:
        stats_data = stats_data[:limit]
        print(f"Limited to {limit} records for testing")
    
    # Get database connection
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # Get league ID
        league_id = get_league_id(cur, league_key)
        if not league_id:
            print(f"❌ League '{league_key}' not found")
            return
        
        print(f"Found league ID: {league_id}")
        
        # Start transaction
        # conn.autocommit = False  # Already set in get_conn()
        
        print("Importing stats...")
        
        # Statistics
        inserted = 0
        updated = 0
        existing = 0
        skipped = 0
        validation_failed = 0
        
        for i, stat_data in enumerate(stats_data):
            try:
                stat_id, action = upsert_stat(cur, league_id, stat_data)
                
                if action == "inserted":
                    inserted += 1
                elif action == "updated":
                    updated += 1
                elif action == "existing":
                    existing += 1
                elif action.startswith("validation_failed"):
                    validation_failed += 1
                    if i < 10:  # Show first 10 validation errors for debugging
                        print(f"  Validation failed: {action}")
                else:
                    skipped += 1
                    if i < 10:  # Show first 10 errors for debugging
                        print(f"  Skipped: {action}")
                        
            except Exception as e:
                print(f"ERROR processing stat {i+1}: {e}")
                skipped += 1
                if i < 10:  # Show first 10 errors for debugging
                    print(f"  Error details: {e}")
                
                # Continue processing instead of failing completely
                continue
        
        # Commit transaction
        conn.commit()
        print("\nImport completed successfully!")
        print(f"Stats: {inserted} inserted, {updated} updated, {existing} existing, {skipped} skipped, {validation_failed} validation failed")
        
        # Run post-import integrity checks
        run_integrity_checks(cur, league_id)
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Import stats with validation and data integrity prevention")
    parser.add_argument("league_key", help="League key (e.g., APTA_CHICAGO)")
    parser.add_argument("--file", help="Custom JSON file path")
    parser.add_argument("--limit", type=int, help="Limit number of records for testing")
    
    args = parser.parse_args()
    
    try:
        import_stats(args.league_key, args.file, args.limit)
    except Exception as e:
        print(f"❌ Import failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
