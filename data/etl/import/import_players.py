#!/usr/bin/env python3
"""
Import Players with Comprehensive Validation and Team Assignment Prevention

This script imports player data from JSON files with built-in validation and
ensures all players get proper team assignments to prevent missing team_id issues.

Usage:
    python3 data/etl/import/import_players.py <LEAGUE_KEY> [--file <JSON_FILE>] [--limit <N>]
"""

import sys
import json
import argparse
import re
import os
from datetime import datetime
from typing import Optional, Tuple, Dict, Set, List
from import_utils import get_league_id, column_exists, parse_datetime_safe, lookup_team_id
# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '..', '..', '..')
sys.path.insert(0, project_root)
from database_config import get_db

# Club name normalization patterns (shared across all import scripts)
_ROMAN_RE = re.compile(r'\b[IVXLCDM]{1,4}\b', re.IGNORECASE)
_ALNUM_SUFFIX_RE = re.compile(r'\b(\d+[A-Za-z]?|[A-Za-z]?\d+)\b')
_LETTER_PAREN_RE = re.compile(r'\b[A-Za-z]{1,3}\(\d+\)\b')
_ALLCAP_SHORT_RE = re.compile(r'\b[A-Z]{1,3}\b')
_KEEP_SUFFIXES: Set[str] = {"CC", "GC", "RC", "PC", "TC", "AC"}

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

def validate_entity_name(name, entity_type):
    """Validate entity names to prevent anomalies like numeric club names."""
    if not name or not isinstance(name, str):
        return False, f"Invalid {entity_type} name: {name}"
    
    name = name.strip()
    if not name:
        return False, f"Empty {entity_type} name"
    
    # Prevent numeric names (like PTI being imported as club names)
    if re.match(r'^[0-9]+\.?[0-9]*$', name):
        return False, f"Invalid {entity_type} name '{name}' - appears to be a numeric value (PTI rating?)"
    
    # Prevent names that are just numbers
    if re.match(r'^[0-9]+$', name):
        return False, f"Invalid {entity_type} name '{name}' - appears to be just a number"
    
    # Prevent names that are too short
    if len(name) < 2:
        return False, f"Invalid {entity_type} name '{name}' - too short (minimum 2 characters)"
    
    # Prevent names that are too long
    if len(name) > 100:
        return False, f"Invalid {entity_type} name '{name}' - too long (maximum 100 characters)"
    
    # Prevent names that are just punctuation or whitespace
    if re.match(r'^[^\w\s]+$', name):
        return False, f"Invalid {entity_type} name '{name}' - contains only punctuation/symbols"
    
    # Prevent names that start/end with punctuation
    if re.match(r'^[^\w]|[^\w]$', name):
        return False, f"Invalid {entity_type} name '{name}' - starts or ends with punctuation"
    
    return True, name

def validate_player_data(player_data):
    """Validate player data to ensure quality and prevent anomalies."""
    errors = []
    
    # Check required fields
    first_name = player_data.get("First Name", "").strip()
    last_name = player_data.get("Last Name", "").strip()
    club = player_data.get("Club", "").strip()
    series = player_data.get("Series", "").strip()
    
    # Handle both "Team" and "Series Mapping ID" fields for different data formats
    team = player_data.get("Team", "").strip() or player_data.get("Series Mapping ID", "").strip()
    
    if not first_name:
        errors.append("Missing First Name")
    elif len(first_name) < 1:
        errors.append("First Name too short")
    elif len(first_name) > 50:
        errors.append("First Name too long")
    
    if not last_name:
        errors.append("Missing Last Name")
    elif len(last_name) < 1:
        errors.append("Last Name too short")
    elif len(last_name) > 50:
        errors.append("Last Name too long")
    
    if not club:
        errors.append("Missing Club")
    else:
        is_valid, club_error = validate_entity_name(club, "Club")
        if not is_valid:
            errors.append(f"Club: {club_error}")
    
    if not series:
        errors.append("Missing Series")
    else:
        is_valid, series_error = validate_entity_name(series, "Series")
        if not is_valid:
            errors.append(f"Series: {series_error}")
    
    if not team:
        errors.append("Missing Team")
    else:
        is_valid, team_error = validate_entity_name(team, "Team")
        if not is_valid:
            errors.append(f"Team: {team_error}")
    
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
    """
    if not team_name:
        return None, None, None
    
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
    existing_team_id = find_existing_team(cur, league_id, team_name, club_id, series_id)
    if existing_team_id:
        return existing_team_id
    
    # Create new team with consistent naming
    return create_team(cur, team_name, club_id, series_id, league_id)

def find_existing_team(cur, league_id, team_name: str, club_id: int, series_id: int) -> Optional[int]:
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
            if team_names_match(team_name, existing_team_name):
                return team_id
    
    return None

def team_names_match(name1: str, name2: str) -> bool:
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

def create_team(cur, team_name: str, club_id: int, series_id: int, league_id) -> Optional[int]:
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

def upsert_player(cur, league_id, player_data):
    """
    Upsert a single player with comprehensive validation and team assignment.
    
    FIXED: Handles series movement correctly - when a player moves from one series 
    to another within the same league/club, updates their existing record instead 
    of creating duplicates.
    """
    # Validate player data first
    is_valid, validation_errors = validate_player_data(player_data)
    if not is_valid:
        return None, f"validation_failed: {', '.join(validation_errors)}"
    
    first_name = player_data.get("First Name", "").strip()
    last_name = player_data.get("Last Name", "").strip()
    team_name = player_data.get("Team", "").strip() or player_data.get("Series Mapping ID", "").strip()
    external_id = player_data.get("Player ID", "").strip()
    
    # Extract PTI and win/loss data
    pti_raw = player_data.get("PTI", "")
    wins_raw = player_data.get("Wins", "0")
    losses_raw = player_data.get("Losses", "0")
    
    # Extract career stats data
    career_wins_raw = player_data.get("Career Wins", "0")
    career_losses_raw = player_data.get("Career Losses", "0")
    career_win_pct_raw = player_data.get("Career Win %", "0.0%")
    
    # Parse PTI value (handle "N/A" and convert to numeric)
    pti_value = None
    if pti_raw and pti_raw != "N/A" and pti_raw != "0":
        try:
            pti_value = float(pti_raw)
        except (ValueError, TypeError):
            pti_value = None
    
    # Parse win/loss values
    wins_value = None
    losses_value = None
    try:
        wins_value = int(wins_raw) if wins_raw and wins_raw != "N/A" else 0
        losses_value = int(losses_raw) if losses_raw and losses_raw != "N/A" else 0
    except (ValueError, TypeError):
        wins_value = 0
        losses_value = 0
    
    # Calculate win percentage
    win_percentage_value = None
    if wins_value > 0 or losses_value > 0:
        try:
            win_percentage_value = (wins_value / (wins_value + losses_value)) * 100
        except (ValueError, TypeError, ZeroDivisionError):
            win_percentage_value = None
    
    # Parse career stats values
    career_wins_value = None
    career_losses_value = None
    career_win_percentage_value = None
    
    try:
        career_wins_value = int(career_wins_raw) if career_wins_raw and career_wins_raw != "N/A" else 0
        career_losses_value = int(career_losses_raw) if career_losses_raw and career_losses_raw != "N/A" else 0
    except (ValueError, TypeError):
        career_wins_value = 0
        career_losses_value = 0
    
    # Parse career win percentage (handle "0.0%" format)
    if career_win_pct_raw and career_win_pct_raw != "N/A":
        try:
            # Remove % sign and convert to float
            career_win_pct_clean = career_win_pct_raw.replace("%", "").strip()
            career_win_percentage_value = float(career_win_pct_clean)
        except (ValueError, TypeError):
            career_win_percentage_value = None
    else:
        career_win_percentage_value = None
    
    # Calculate career matches
    career_matches_value = career_wins_value + career_losses_value
    
    # Parse team name to get club and series
    club_name, series_name, team_number = parse_team_name(team_name)
    if not all([club_name, series_name]):
        return None, f"team_parsing_failed: could not extract club/series from '{team_name}'"
    
    try:
        # Ensure team exists (create if needed)
        team_id = upsert_team(cur, league_id, team_name, club_name, series_name)
        if not team_id:
            return None, f"team_creation_failed: could not create team '{team_name}'"
        
        # Get club_id and series_id for player
        cur.execute("SELECT club_id, series_id FROM teams WHERE id = %s", (team_id,))
        team_info = cur.fetchone()
        if not team_info:
            return None, f"team_info_failed: could not get club/series for team '{team_name}'"
        
        club_id, series_id = team_info
        
        # Check if tenniscores_player_id column exists
        has_tenniscores_id = column_exists(cur, "players", "tenniscores_player_id")
        
        if has_tenniscores_id and external_id:
            # FIXED: Handle series movement correctly
            # First check if player exists in same league/club (regardless of series)
            cur.execute("""
                SELECT id, series_id, team_id FROM players 
                WHERE tenniscores_player_id = %s AND league_id = %s AND club_id = %s
                LIMIT 1
            """, (external_id, league_id, club_id))
            
            existing_player = cur.fetchone()
            
            if existing_player:
                # Player exists in same league/club - this is series movement, UPDATE the record
                existing_id, old_series_id, old_team_id = existing_player
                
                cur.execute("""
                    UPDATE players SET 
                        first_name = %s, 
                        last_name = %s,
                        series_id = %s,
                        team_id = %s,
                        pti = %s,
                        wins = %s,
                        losses = %s,
                        win_percentage = %s,
                        career_wins = %s,
                        career_losses = %s,
                        career_matches = %s,
                        career_win_percentage = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING id
                """, (first_name, last_name, series_id, team_id, pti_value, wins_value, losses_value, win_percentage_value, career_wins_value, career_losses_value, career_matches_value, career_win_percentage_value, existing_id))
                
                result = cur.fetchone()
                if result:
                    return result[0], "updated_series_movement"
            else:
                # New player - use original upsert logic with series included in conflict
                cur.execute("""
                    INSERT INTO players (first_name, last_name, league_id, club_id, series_id, team_id, tenniscores_player_id, pti, wins, losses, win_percentage, career_wins, career_losses, career_matches, career_win_percentage) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                    ON CONFLICT (tenniscores_player_id, league_id, club_id, series_id)
                    DO UPDATE SET 
                        first_name = EXCLUDED.first_name, 
                        last_name = EXCLUDED.last_name,
                        team_id = EXCLUDED.team_id,
                        pti = EXCLUDED.pti,
                        wins = EXCLUDED.wins,
                        losses = EXCLUDED.losses,
                        win_percentage = EXCLUDED.win_percentage,
                        career_wins = EXCLUDED.career_wins,
                        career_losses = EXCLUDED.career_losses,
                        career_matches = EXCLUDED.career_matches,
                        career_win_percentage = EXCLUDED.career_win_percentage
                    RETURNING id
                """, (first_name, last_name, league_id, club_id, series_id, team_id, external_id, pti_value, wins_value, losses_value, win_percentage_value, career_wins_value, career_losses_value, career_matches_value, career_win_percentage_value))
            
            result = cur.fetchone()
            if result:
                # This was a new player insertion (no conflict occurred)
                return result[0], "inserted"
        else:
            # Fallback to name + league_id + club_id + series_id - NOW INCLUDING PTI, WIN/LOSS DATA, AND CAREER STATS
            cur.execute("""
                INSERT INTO players (first_name, last_name, league_id, club_id, series_id, team_id, pti, wins, losses, win_percentage, career_wins, career_losses, career_matches, career_win_percentage) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                ON CONFLICT (first_name, last_name, league_id, club_id, series_id) 
                DO UPDATE SET 
                    team_id = EXCLUDED.team_id,
                    pti = EXCLUDED.pti,
                    wins = EXCLUDED.wins,
                    losses = EXCLUDED.losses,
                    win_percentage = EXCLUDED.win_percentage,
                    career_wins = EXCLUDED.career_wins,
                    career_losses = EXCLUDED.career_losses,
                    career_matches = EXCLUDED.career_matches,
                    career_win_percentage = EXCLUDED.career_win_percentage
                RETURNING id
            """, (first_name, last_name, league_id, club_id, series_id, team_id, pti_value, wins_value, losses_value, win_percentage_value, career_wins_value, career_losses_value, career_matches_value, career_win_percentage_value))
            
            result = cur.fetchone()
            if result:
                # Check if this was an INSERT or UPDATE by examining the RETURNING result
                # For INSERT: new row is returned
                # For UPDATE: existing row is returned
                # We can't easily distinguish between INSERT and UPDATE with ON CONFLICT DO UPDATE
                # So we'll return "upserted" to indicate the operation succeeded
                return result[0], "upserted"
        
        # If we get here, the player already exists
        return None, "existing"
        
    except Exception as e:
        raise Exception(f"Failed to upsert player {first_name} {last_name}: {e}")

def assign_players_to_teams(cur, league_id):
    """Assign all players to their correct teams based on club_id and series_id."""
    print("\n🔗 Assigning players to teams...")
    
    assigned = 0
    failed = 0
    
    # Find all players without team assignments
    cur.execute("""
        SELECT p.id, p.first_name, p.last_name, p.club_id, p.series_id
        FROM players p
        WHERE p.league_id = %s AND p.team_id IS NULL
    """, (league_id,))
    
    unassigned_players = cur.fetchall()
    
    if not unassigned_players:
        print("  ✅ All players already have team assignments")
        return 0, 0
    
    print(f"  📊 Found {len(unassigned_players)} players without team assignments")
    
    for player_id, first_name, last_name, club_id, series_id in unassigned_players:
        try:
            # Find the team that matches this player's club and series
            cur.execute("""
                SELECT id FROM teams 
                WHERE league_id = %s AND club_id = %s AND series_id = %s
                LIMIT 1
            """, (league_id, club_id, series_id))
            
            team_result = cur.fetchone()
            if team_result:
                team_id = team_result[0]
                
                # Update the player with the team_id
                cur.execute("""
                    UPDATE players 
                    SET team_id = %s 
                    WHERE id = %s
                """, (team_id, player_id))
                
                assigned += 1
                if assigned % 100 == 0:  # Progress indicator
                    print(f"    Assigned {assigned} players to teams...")
            else:
                print(f"    ⚠️ No team found for {first_name} {last_name} (club_id: {club_id}, series_id: {series_id})")
                failed += 1
                
        except Exception as e:
            print(f"    ❌ Failed to assign {first_name} {last_name}: {e}")
            failed += 1
    
    print(f"  📊 Team assignment complete:")
    print(f"    ✅ Assigned: {assigned}")
    print(f"    ⚠️ Failed: {failed}")
    
    return assigned, failed

def run_integrity_checks(cur, league_id):
    """Run post-import integrity checks."""
    print("\n🔍 Running post-import integrity checks...")
    
    issues_found = 0
    
    # Check for players with missing team assignments
    cur.execute("""
        SELECT COUNT(*) FROM players 
        WHERE league_id = %s AND team_id IS NULL
    """, (league_id,))
    
    missing_teams = cur.fetchone()[0]
    if missing_teams > 0:
        print(f"  ⚠️ Found {missing_teams} players with missing team assignments")
        issues_found += missing_teams
    else:
        print("  ✅ All players have team assignments")
    
    # Check for orphaned teams (teams without clubs or series)
    cur.execute("""
        SELECT COUNT(*) FROM teams t
        LEFT JOIN clubs c ON t.club_id = c.id
        LEFT JOIN series s ON t.series_id = s.id
        WHERE t.league_id = %s AND (c.id IS NULL OR s.id IS NULL)
    """, (league_id,))
    
    orphaned_teams = cur.fetchone()[0]
    if orphaned_teams > 0:
        print(f"  ⚠️ Found {orphaned_teams} orphaned teams")
        issues_found += orphaned_teams
    else:
        print("  ✅ All teams have proper club and series relationships")
    
    # Check for duplicate team names
    cur.execute("""
        SELECT team_name, COUNT(*) as count
        FROM teams 
        WHERE league_id = %s 
        GROUP BY team_name 
        HAVING COUNT(*) > 1
        ORDER BY count DESC
    """, (league_id,))
    
    duplicates = cur.fetchall()
    if duplicates:
        print(f"  ❌ Found {len(duplicates)} duplicate team names")
        for team_name, count in duplicates[:5]:  # Show first 5
            print(f"    {team_name}: {count} records")
        if len(duplicates) > 5:
            print(f"    ... and {len(duplicates) - 5} more")
        issues_found += len(duplicates)
    else:
        print("  ✅ No duplicate team names found")
    
    # Check for teams with missing players
    cur.execute("""
        SELECT COUNT(*) FROM teams t
        LEFT JOIN players p ON t.id = p.team_id
        WHERE t.league_id = %s AND p.id IS NULL
    """, (league_id,))
    
    empty_teams = cur.fetchone()[0]
    if empty_teams > 0:
        print(f"  ⚠️ Found {empty_teams} teams with no players")
        issues_found += empty_teams
    else:
        print("  ✅ All teams have players")
    
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

def import_players(league_key, file_path=None, limit=None):
    """Import players for a specific league with comprehensive validation."""
    print(f"Importing players for league: {league_key}")
    
    # Determine input file
    if file_path:
        input_file = file_path
    else:
        input_file = f"data/leagues/{league_key}/players.json"
    
    print(f"Input file: {input_file}")
    
    # Load players data
    print("Loading players data...")
    players_data = load_json_file(input_file)
    print(f"Loaded {len(players_data)} player records")
    
    if limit:
        players_data = players_data[:limit]
        print(f"Limited to {limit} records for testing")
    
        # Get database connection using our database configuration
    with get_db() as conn:
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
            
            print("Importing players...")
            
            # Statistics
            inserted = 0
            updated = 0
            existing = 0
            skipped = 0
            validation_failed = 0
            
            for i, player_data in enumerate(players_data):
                try:
                    player_id, action = upsert_player(cur, league_id, player_data)
                    
                    if action == "inserted":
                        inserted += 1
                    elif action == "updated":
                        updated += 1
                    elif action == "updated_series_movement":
                        updated += 1
                        if i < 10:  # Show first 10 series movements for visibility
                            player_name = f"{player_data.get('First Name', '')} {player_data.get('Last Name', '')}"
                            new_series = player_data.get('Series', 'Unknown')
                            print(f"  🔄 Series movement: {player_name} moved to {new_series}")
                    elif action == "upserted":
                        # For upserted records, we can't distinguish between insert and update
                        # so we'll count them as updated since they were processed successfully
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
                    print(f"ERROR processing player {i+1}: {e}")
                    skipped += 1
                    if i < 10:  # Show first 10 errors for debugging
                        print(f"  Error details: {e}")
                    
                    # Continue processing instead of failing completely
                    continue
            
            # Assign players to teams
            assigned, failed = assign_players_to_teams(cur, league_id)
            
            # Commit transaction
            conn.commit()
            print("\nImport completed successfully!")
            print(f"Players: {inserted} inserted, {updated} updated, {existing} existing, {skipped} skipped, {validation_failed} validation failed")
            print(f"Team assignments: {assigned} assigned, {failed} failed")
            
            # Run post-import integrity checks
            run_integrity_checks(cur, league_id)
            
        except Exception as e:
            print(f"❌ Import failed: {e}")
            conn.rollback()
            raise

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Import players with validation and team assignment prevention")
    parser.add_argument("league_key", help="League key (e.g., APTA_CHICAGO)")
    parser.add_argument("--file", help="Custom JSON file path")
    parser.add_argument("--limit", type=int, help="Limit number of records for testing")
    
    args = parser.parse_args()
    
    try:
        import_players(args.league_key, args.file, args.limit)
    except Exception as e:
        print(f"❌ Import failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
