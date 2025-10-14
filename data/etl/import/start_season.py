#!/usr/bin/env python3
"""
Start Season Script for Rally App

Bootstraps league data (clubs, series, teams, players) from a JSON file.
Uses upserts to prevent duplicates and handles both numeric and letter-based series.
Automatically updates club addresses from data/club_addresses.csv during club creation.

Usage: python3 data/etl/import/start_season.py <LEAGUE_KEY> [--test-file <JSON_FILE>] [--skip-addresses]
"""

import argparse
import csv
import json
import os
import re
import sys
from typing import List, Tuple, Dict, Any, Set, Optional
from difflib import SequenceMatcher

from import_utils import (
    get_conn, get_league_id, check_tenniscores_player_id_column,
    upsert_club, upsert_series, upsert_player, column_exists
)

# Club normalization tracking
_seen_variants: Dict[str, Set[str]] = {}

# Club normalization regex patterns
_ROMAN_RE = re.compile(r'\b[IVXLCDM]{1,4}\b', re.IGNORECASE)
_ALNUM_SUFFIX_RE = re.compile(r'\b(\d+[A-Za-z]?|[A-Za-z]?\d+)\b')
_LETTER_PAREN_RE = re.compile(r'\b[A-Za-z]{1,3}\(\d+\)\b')
_ALLCAP_SHORT_RE = re.compile(r'\b[A-Z]{1,3}\b')
_KEEP_SUFFIXES: Set[str] = {"CC", "GC", "RC", "PC", "TC", "AC"}  # preserve common club types

# Club address matching
_club_addresses: Dict[str, str] = {}


def _strip_trailing_suffix_tokens(tokens: list[str]) -> list[str]:
    """Strip trailing series/division/team markers without using hard-coded club maps."""
    while tokens:
        t = tokens[-1]

        # Preserve common club-type suffixes (e.g., 'Lake Shore CC')
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
        # Generic short all-caps trailing marker (e.g., PD, H, B, F)
        if _ALLCAP_SHORT_RE.fullmatch(t) and len(t) <= 3:
            tokens.pop()
            continue
        break
    return tokens


def normalize_club_name(raw: str) -> str:
    """
    Normalize club names by removing series/division/team markers while preserving 
    canonical club names and expanding common club-type abbreviations for better matching.
    
    Examples:
    - "Prairie Club II" -> "Prairie Club"
    - "Wilmette PD I" -> "Wilmette"
    - "Winnetka 99 B" -> "Winnetka"
    - "Midtown - Chicago - 23" -> "Midtown"
    - "Lake Shore CC" -> "Lake Shore Country Club" (CC expanded)
    - "Hinsdale GC" -> "Hinsdale Golf Club" (GC expanded)
    """
    if not raw:
        return raw

    s = raw.strip()

    # Keep only the first segment if the name contains ' - ' separators (e.g., 'Midtown - Chicago - 23')
    if ' - ' in s:
        s = s.split(' - ')[0].strip()

    # Drop one trailing parenthetical segment if present
    s = re.sub(r'\s*\([^)]*\)\s*$', '', s).strip()

    # Normalize whitespace
    s = re.sub(r'\s+', ' ', s)

    # Tokenize and strip trailing suffix tokens according to our rules
    tokens = s.split(' ')
    tokens = _strip_trailing_suffix_tokens(tokens)

    # Remove stray punctuation from the remaining body (keep &)
    base = ' '.join(tokens)
    base = re.sub(r'[^\w\s&]', ' ', base)
    base = re.sub(r'\s+', ' ', base).strip()

    # Title case for display consistency and expand club type abbreviations
    words = base.split()
    title_words = []
    for word in words:
        if word.upper() in _KEEP_SUFFIXES:
            # Expand common club type abbreviations for better matching
            expanded = _expand_club_abbreviation(word.upper())
            title_words.append(expanded)
        else:
            title_words.append(word.title())
    base = ' '.join(title_words)

    return base


def _expand_club_abbreviation(abbrev: str) -> str:
    """
    Expand common club type abbreviations to their full forms for better matching.
    
    Args:
        abbrev: The abbreviation to expand (e.g., 'GC', 'CC')
        
    Returns:
        The expanded form (e.g., 'Golf Club', 'Country Club')
    """
    expansions = {
        'CC': 'Country Club',
        'GC': 'Golf Club', 
        'RC': 'Racquet Club',
        'PC': 'Paddle Club',
        'TC': 'Tennis Club',
        'AC': 'Athletic Club',
        'PD': 'Paddle',  # Common in some leagues
        'S&F': 'Sports & Fitness'  # Handle special cases
    }
    
    return expansions.get(abbrev, abbrev)


def load_club_addresses(csv_file: str = "data/club_addresses.csv") -> Dict[str, str]:
    """
    Load club addresses from CSV file and return a mapping of club names to addresses.
    Uses fuzzy matching to handle variations in club names.
    """
    global _club_addresses
    
    if _club_addresses:
        return _club_addresses
    
    if not os.path.exists(csv_file):
        print(f"⚠️  Club addresses CSV file not found: {csv_file}")
        return {}
    
    addresses = {}
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                raw_name = row.get('Raw Name', '').strip()
                full_name = row.get('Full Name', '').strip()
                address = row.get('Address', '').strip()
                
                # Use raw name if available, otherwise use full name
                club_name = raw_name if raw_name else full_name
                
                if club_name and address:
                    # Normalize the club name for matching
                    normalized_name = normalize_club_name(club_name)
                    addresses[normalized_name] = address
                    
                    # Also store the original name for exact matches
                    addresses[club_name] = address
        
        _club_addresses = addresses
        print(f"📊 Loaded {len(addresses)} club addresses from CSV")
        return addresses
        
    except Exception as e:
        print(f"❌ Error loading club addresses from CSV: {e}")
        return {}


def find_club_address(club_name: str, addresses: Dict[str, str]) -> Optional[str]:
    """
    Find the address for a club using fuzzy matching.
    Returns the address if found, None otherwise.
    """
    if not club_name or not addresses:
        return None
    
    # First try exact match
    if club_name in addresses:
        return addresses[club_name]
    
    # Try normalized name match
    normalized_name = normalize_club_name(club_name)
    if normalized_name in addresses:
        return addresses[normalized_name]
    
    # Try fuzzy matching with similarity threshold
    best_match = None
    best_score = 0.0
    similarity_threshold = 0.6
    
    for csv_name, address in addresses.items():
        # Calculate similarity
        similarity = SequenceMatcher(None, club_name.lower(), csv_name.lower()).ratio()
        
        if similarity > best_score and similarity >= similarity_threshold:
            best_score = similarity
            best_match = address
    
    if best_match:
        print(f"    📍 Found address for '{club_name}' via fuzzy match (score: {best_score:.2f})")
    
    return best_match


def upsert_club_with_address(cur, name: str, league_id: int, addresses: Dict[str, str]) -> int:
    """
    Upsert club with address from CSV data.
    Returns the club ID.
    """
    if not name:
        return None
    
    # Get the club address if available
    club_address = find_club_address(name, addresses)
    
    # Check if clubs table has league_id column
    if column_exists(cur, "clubs", "league_id"):
        # Direct league_id column
        if club_address:
            cur.execute("""
                INSERT INTO clubs (name, league_id, club_address) 
                VALUES (%s, %s, %s) 
                ON CONFLICT (name, league_id) DO UPDATE SET 
                    club_address = EXCLUDED.club_address
                RETURNING id
            """, (name, league_id, club_address))
        else:
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
        if club_address:
            cur.execute("""
                INSERT INTO clubs (name, club_address) 
                VALUES (%s, %s) 
                ON CONFLICT (name) DO UPDATE SET 
                    club_address = EXCLUDED.club_address
                RETURNING id
            """, (name, club_address))
        else:
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


def validate_entity_name(name, entity_type):
    """Validate entity names to prevent anomalies like numeric club names."""
    if not name or not isinstance(name, str):
        return False, f"Invalid {entity_type} name: {name}"
    
    name = name.strip()
    if not name:
        return False, f"Empty {entity_type} name"
    
    # Prevent numeric names (like PTI ratings being imported as club names)
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
        errors.append("Missing Team/Series Mapping ID")
    else:
        is_valid, team_error = validate_entity_name(team, "Team")
        if not is_valid:
            errors.append(f"Team: {team_error}")
    
    # Validate Player ID if present
    player_id = player_data.get("Player ID", "").strip()
    if player_id and len(player_id) > 100:
        errors.append("Player ID too long")
    
    # Validate PTI if present (should be numeric or "N/A")
    pti = player_data.get("PTI", "").strip()
    if pti and pti != "N/A":
        try:
            float(pti)
        except ValueError:
            errors.append(f"Invalid PTI value: {pti}")
    
    return len(errors) == 0, errors


def get_league_id(cur, league_key):
    """Get league ID from database."""
    cur.execute("SELECT id FROM leagues WHERE league_id = %s OR league_name = %s LIMIT 1", (league_key, league_key))
    result = cur.fetchone()
    if not result:
        print(f"ERROR: League '{league_key}' not found in database")
        sys.exit(1)
    return result[0]


def load_players_json(league_key):
    """Load and parse players.json file with validation."""
    json_path = f"data/leagues/{league_key}/players.json"
    if not os.path.exists(json_path):
        print(f"ERROR: Players file not found: {json_path}")
        sys.exit(1)
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        if not isinstance(data, list):
            print(f"ERROR: Invalid JSON format - expected array, got {type(data)}")
            sys.exit(1)
        return data
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {json_path}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to load {json_path}: {e}")
        sys.exit(1)


def normalize_club_name_for_team_matching(club_name):
    """
    Normalize club names to match the format expected by team parsing.
    This handles cases where club names have dashes but team names don't.
    
    Examples:
    - "Midtown - Chicago - 10" -> "Midtown Chicago"
    - "Midtown - Chicago - 14" -> "Midtown Chicago"
    - "LifeSport-Lshire" -> "LifeSport"
    - "Park RIdge CC" -> "Park Ridge CC"
    """
    if not club_name:
        return club_name
    
    normalized = club_name
    
    # Handle Midtown Chicago special case
    # "Midtown - Chicago - X" -> "Midtown Chicago"
    if re.match(r'^Midtown\s*-\s*Chicago\s*-\s*\d+$', normalized):
        normalized = "Midtown Chicago"
    
    # Handle other special cases
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


def extract_unique_entities(players_data):
    """Extract unique clubs, series, teams, and players from JSON data with validation."""
    clubs, series, teams, players = set(), set(), set(), set()
    validation_errors = []
    skipped_records = 0
    
    for i, player in enumerate(players_data):
        # Validate player data
        is_valid, errors = validate_player_data(player)
        if not is_valid:
            validation_errors.append(f"Record {i+1}: {', '.join(errors)}")
            skipped_records += 1
            continue
        
        raw_club = player.get("Club", "").strip()
        series_name = player.get("Series", "").strip()
        
        # Handle both "Team" and "Series Mapping ID" fields
        team_name = player.get("Team", "").strip() or player.get("Series Mapping ID", "").strip()
        
        player_id = player.get("Player ID", "").strip()
        first_name = player.get("First Name", "").strip()
        last_name = player.get("Last Name", "").strip()
        
        # Build player name
        if first_name and last_name:
            player_name = f"{first_name} {last_name}".strip()
        elif first_name:
            player_name = first_name
        elif last_name:
            player_name = last_name
        else:
            player_name = ""
        
        # Normalize club name and track variants
        club = normalize_club_name(raw_club)
        if club and raw_club:
            _seen_variants.setdefault(club, set()).add(raw_club)
        
        # Add to sets if valid
        if club: clubs.add(club)
        if series_name: series.add(series_name)
        if team_name: teams.add(team_name)
        if player_name: players.add((player_name, player_id if player_id else None))
    
    # Report validation results
    if validation_errors:
        print(f"⚠️  Data validation warnings ({len(validation_errors)} issues found):")
        for error in validation_errors[:10]:  # Show first 10 errors
            print(f"    {error}")
        if len(validation_errors) > 10:
            print(f"    ... and {len(validation_errors) - 10} more validation issues")
        print(f"    Skipped {skipped_records} invalid records")
    
    if skipped_records > len(players_data) * 0.1:  # More than 10% invalid
        print(f"⚠️  WARNING: High number of invalid records ({skipped_records}/{len(players_data)}). Consider reviewing data quality.")
    
    return list(clubs), list(series), list(teams), list(players), validation_errors


def upsert_entity(cur, table, values, league_id):
    """Generic upsert function for clubs and series with validation."""
    inserted, existing, name_to_id = 0, 0, {}
    
    for name in values:
        # Validate name before upserting
        is_valid, error_msg = validate_entity_name(name, table.rstrip('s'))  # Remove 's' for singular
        if not is_valid:
            print(f"    ⚠️  Skipping invalid {table.rstrip('s')} name: {error_msg}")
            continue
        
        try:
            if table == "clubs":
                # Clubs don't have league_id, use club_leagues junction table
                cur.execute("INSERT INTO clubs (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id", (name,))
                result = cur.fetchone()
                if result:
                    inserted += 1
                    club_id = result[0]
                    name_to_id[name] = club_id
                    # Create club-league relationship
                    cur.execute("INSERT INTO club_leagues (club_id, league_id) VALUES (%s, %s) ON CONFLICT (club_id, league_id) DO NOTHING", (club_id, league_id))
                else:
                    # Get existing ID
                    cur.execute("SELECT id FROM clubs WHERE name = %s", (name,))
                    existing_id = cur.fetchone()[0]
                    name_to_id[name] = existing_id
                    existing += 1
                    # Ensure club-league relationship exists
                    cur.execute("INSERT INTO club_leagues (club_id, league_id) VALUES (%s, %s) ON CONFLICT (club_id, league_id) DO NOTHING", (existing_id, league_id))
            else:
                # Series have league_id column
                cur.execute(f"INSERT INTO {table} (name, display_name, league_id) VALUES (%s, %s, %s) ON CONFLICT (name, league_id) DO NOTHING RETURNING id", (name, name, league_id))
                result = cur.fetchone()
                if result:
                    inserted += 1
                    name_to_id[name] = result[0]
                else:
                    # Get existing ID
                    cur.execute(f"SELECT id FROM {table} WHERE name = %s AND league_id = %s", (name, league_id))
                    existing_id = cur.fetchone()[0]
                    name_to_id[name] = existing_id
                    existing += 1
        except Exception as e:
            print(f"ERROR: Failed to upsert {table} '{name}': {e}")
            raise
    
    return inserted, existing, name_to_id


def upsert_teams_and_players(cur, league_id, clubs, series, teams):
    """Upsert teams and associate them with clubs and series."""
    inserted, existing, skipped = 0, 0, 0
    
    for team_name in teams:
        # Parse team name to extract club and series
        raw_club_name, series_name, team_number = parse_team_name(team_name)
        
        if not raw_club_name or not series_name:
            print(f"    Skipping team '{team_name}' - could not parse club or series")
            skipped += 1
            continue
        
        # Normalize the club name extracted from team name
        club_name = normalize_club_name(raw_club_name)
        
        # Look up club_id with normalized name
        cur.execute("SELECT id FROM clubs WHERE name = %s", (club_name,))
        club_result = cur.fetchone()
        
        if not club_result:
            # Since we're now using normalized names, this fallback should rarely be needed
            # But keep it for edge cases where team parsing might extract a different club name
            print(f"    Club '{club_name}' not found - this may indicate a data inconsistency")
        
        if not club_result:
            print(f"    Skipping team '{team_name}' - club '{club_name}' not found")
            skipped += 1
            continue
        club_id = club_result[0]
        
        # Look up series_id
        cur.execute("SELECT id FROM series WHERE name = %s AND league_id = %s", (series_name, league_id))
        series_result = cur.fetchone()
        if not series_result:
            print(f"    Skipping team '{team_name}' - series '{series_name}' not found")
            skipped += 1
            continue
        series_id = series_result[0]
        
        try:
            # Check if a team with this club/series combination already exists
            cur.execute("""
                SELECT id, team_name FROM teams 
                WHERE club_id = %s AND series_id = %s AND league_id = %s
            """, (club_id, series_id, league_id))
            
            existing_team = cur.fetchone()
            if existing_team:
                print(f"    Team with club '{club_name}' and series '{series_name}' already exists: {existing_team[1]}")
                existing += 1
                continue
            
            # Upsert team
            cur.execute("""
                INSERT INTO teams (team_name, display_name, league_id, club_id, series_id) 
                VALUES (%s, %s, %s, %s, %s) 
                ON CONFLICT (team_name, league_id) 
                DO UPDATE SET club_id = EXCLUDED.club_id, series_id = EXCLUDED.series_id 
                RETURNING id
            """, (team_name, team_name, league_id, club_id, series_id))
            
            result = cur.fetchone()
            if result:
                if cur.rowcount == 1:  # INSERT
                    print(f"    Creating team: {team_name} (club: {club_name}, series: {series_name})")
                    inserted += 1
                else:  # UPDATE
                    existing += 1
            else:
                existing += 1
                
        except Exception as e:
            print(f"ERROR: Failed to upsert team '{team_name}': {e}")
            raise
    
    return inserted, existing, skipped

def parse_team_name(team_name):
    """
    Parse team name to extract club, series, and team number/letter.
    Handles both numeric and letter-based series, including SW (Southwest) teams.
    
    Examples:
    - "Birchwood 12" -> ("Birchwood", "Series 12", "12")
    - "Exmoor I" -> ("Exmoor", "Series I", "I") 
    - "Winnetka D" -> ("Winnetka", "Series D", "D")
    - "Tennaqua A" -> ("Tennaqua", "Series A", "A")
    - "Michigan Shores 3b" -> ("Michigan Shores", "Series 3b", "3b")
    - "Chicago Highlands 11 SW" -> ("Chicago Highlands", "Series 11 SW", "11 SW")
    - "Medinah 9 SW" -> ("Medinah", "Series 9 SW", "9 SW")
    """
    if not team_name:
        return None, None, None
    
    # Try to extract SW series first (e.g., "11 SW", "9 SW", "15 SW")
    # This must come before numeric series to avoid conflicts
    sw_match = re.search(r'(\d+)\s+SW$', team_name)
    if sw_match:
        team_number = sw_match.group(1)
        club_name = team_name[:sw_match.start()].strip()
        series_name = f"Series {team_number} SW"
        return club_name, series_name, f"{team_number} SW"
    
    # Try to extract numeric series (e.g., "12", "3b", "14a")
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
    
    # If no pattern matches, return None to indicate parsing failure
    # This prevents creation of generic series that cause data integrity issues
    return None, None, None


def assign_players_to_teams(cur, league_id):
    """Assign all players to their correct teams based on club_id and series_id."""
    print("\n🔗 Assigning players to teams...")
    
    assigned = 0
    already_assigned = 0
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
        return 0, 0, 0
    
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
    
    return assigned, already_assigned, failed

def upsert_players(cur, league_id, players_data, has_external_id):
    """Upsert players with proper team association for club_id and series_id and validation."""
    inserted, updated, existing, skipped = 0, 0, 0, 0
    
    for player_data in players_data:
        first_name = player_data.get("First Name", "").strip()
        last_name = player_data.get("Last Name", "").strip()
        
        # Handle both "Team" and "Series Mapping ID" fields
        team_name = player_data.get("Team", "").strip() or player_data.get("Series Mapping ID", "").strip()
        
        external_id = player_data.get("Player ID", "").strip()
        
        # Extract PTI and win/loss data
        pti_raw = player_data.get("PTI", "")
        wins_raw = player_data.get("Wins", "0")
        losses_raw = player_data.get("Losses", "0")
        
        # Extract career stats data - ONLY use explicit Career fields, DO NOT fall back to current season
        # Career stats should be calculated from match history, not copied from current season stats
        career_wins_raw = player_data.get("Career Wins", None)
        career_losses_raw = player_data.get("Career Losses", None)
        career_win_pct_raw = player_data.get("Career Win %", None)
        
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
            # CRITICAL FIX: Only parse career stats if they exist in the JSON, otherwise keep as None
            career_wins_value = int(career_wins_raw) if career_wins_raw and career_wins_raw != "N/A" else None
            career_losses_value = int(career_losses_raw) if career_losses_raw and career_losses_raw != "N/A" else None
        except (ValueError, TypeError):
            career_wins_value = None
            career_losses_value = None
        
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
        
        # Validate player data
        is_valid, errors = validate_player_data(player_data)
        if not is_valid:
            skipped += 1
            continue
        
        player_name = f"{first_name} {last_name}".strip()
        
        try:
            # FIXED: Extract club and series from team name instead of looking up team
            # This avoids the team lookup failure and defers team assignment to assign_players_to_teams()
            raw_club_name, series_name, team_number = parse_team_name(team_name)
            
            if not raw_club_name or not series_name:
                print(f"    Skipping player '{player_name}' - could not parse team '{team_name}'")
                skipped += 1
                continue
            
            # Normalize club name to match what was created
            club_name = normalize_club_name(raw_club_name)
            
            # Look up club_id
            cur.execute("SELECT id FROM clubs WHERE name = %s", (club_name,))
            club_result = cur.fetchone()
            if not club_result:
                print(f"    Skipping player '{player_name}' - club '{club_name}' not found")
                skipped += 1
                continue
            club_id = club_result[0]
            
            # Look up series_id
            cur.execute("SELECT id FROM series WHERE name = %s AND league_id = %s", (series_name, league_id))
            series_result = cur.fetchone()
            if not series_result:
                print(f"    Skipping player '{player_name}' - series '{series_name}' not found")
                skipped += 1
                continue
            series_id = series_result[0]
            
            # Don't assign team_id here - let assign_players_to_teams() handle it
            team_id = None
            
            if has_external_id and external_id:
                # Use tenniscores_player_id for upsert - NOW INCLUDING PTI, WIN/LOSS DATA, AND CAREER STATS
                # CRITICAL FIX: Only update career stats if they are provided (not None)
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
                        career_wins = COALESCE(EXCLUDED.career_wins, players.career_wins),
                        career_losses = COALESCE(EXCLUDED.career_losses, players.career_losses),
                        career_matches = COALESCE(EXCLUDED.career_matches, players.career_matches),
                        career_win_percentage = COALESCE(EXCLUDED.career_win_percentage, players.career_win_percentage)
                    RETURNING id
                """, (first_name, last_name, league_id, club_id, series_id, team_id, external_id, pti_value, wins_value, losses_value, win_percentage_value, career_wins_value, career_losses_value, career_matches_value, career_win_percentage_value))
                
                result = cur.fetchone()
                if result:
                    if cur.rowcount == 1:  # INSERT
                        inserted += 1
                    else:  # UPDATE
                        updated += 1
                else:
                    existing += 1
            else:
                # Fallback to name + league_id + club_id + series_id - NOW INCLUDING PTI, WIN/LOSS DATA, AND CAREER STATS
                # CRITICAL FIX: Only update career stats if they are provided (not None)
                cur.execute("""
                    INSERT INTO players (first_name, last_name, league_id, club_id, series_id, team_id, pti, wins, losses, win_percentage, career_wins, career_losses, career_matches, career_win_percentage) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                    ON CONFLICT (first_name, league_id, club_id, series_id) 
                    DO UPDATE SET 
                        team_id = EXCLUDED.team_id,
                        pti = EXCLUDED.pti,
                        wins = EXCLUDED.wins,
                        losses = EXCLUDED.losses,
                        win_percentage = EXCLUDED.win_percentage,
                        career_wins = COALESCE(EXCLUDED.career_wins, players.career_wins),
                        career_losses = COALESCE(EXCLUDED.career_losses, players.career_losses),
                        career_matches = COALESCE(EXCLUDED.career_matches, players.career_matches),
                        career_win_percentage = COALESCE(EXCLUDED.career_win_percentage, players.career_win_percentage)
                    RETURNING id
                """, (first_name, last_name, league_id, club_id, series_id, team_id, pti_value, wins_value, losses_value, win_percentage_value, career_wins_value, career_losses_value, career_matches_value, career_win_percentage_value))
                
                result = cur.fetchone()
                if result:
                    inserted += 1
                else:
                    # Check if player already exists
                    cur.execute("""
                        SELECT id FROM players 
                        WHERE first_name = %s AND last_name = %s AND league_id = %s AND club_id = %s AND series_id = %s
                    """, (first_name, last_name, league_id, club_id, series_id))
                    
                    existing_player = cur.fetchone()
                    if existing_player:
                        # Update existing player with team_id if missing
                        if team_id:
                            cur.execute("""
                                UPDATE players 
                                SET team_id = %s 
                                WHERE id = %s
                            """, (team_id, existing_player[0]))
                        existing += 1
                    else:
                        skipped += 1
                        
        except Exception as e:
            print(f"ERROR: Failed to upsert player '{player_name}': {e}")
            raise
    
    return inserted, updated, existing, skipped


def check_external_id_column(cur):
    """Check if players table has tenniscores_player_id column."""
    cur.execute("SELECT 1 FROM information_schema.columns WHERE table_name = 'players' AND column_name = 'tenniscores_player_id' LIMIT 1")
    return cur.fetchone() is not None


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


def fix_existing_team_assignments(cur, league_id):
    """Fix any existing players that still have missing team assignments."""
    print("\n🔧 Fixing existing team assignments...")
    
    fixed = 0
    failed = 0
    
    # Find all players without team assignments
    cur.execute("""
        SELECT p.id, p.first_name, p.last_name, p.club_id, p.series_id
        FROM players p
        WHERE p.league_id = %s AND p.team_id IS NULL
    """, (league_id,))
    
    unassigned_players = cur.fetchall()
    
    if not unassigned_players:
        print("  ✅ All existing players have team assignments")
        return 0, 0
    
    print(f"  📊 Found {len(unassigned_players)} existing players without team assignments")
    
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
                
                fixed += 1
                if fixed % 100 == 0:  # Progress indicator
                    print(f"    Fixed {fixed} team assignments...")
            else:
                print(f"    ⚠️ No team found for {first_name} {last_name} (club_id: {club_id}, series_id: {series_id})")
                failed += 1
                
        except Exception as e:
            print(f"    ❌ Failed to fix {first_name} {last_name}: {e}")
            failed += 1
    
    print(f"  📊 Team assignment fixes complete:")
    print(f"    ✅ Fixed: {fixed}")
    print(f"    ⚠️ Failed: {failed}")
    
    return fixed, failed


def update_existing_clubs_with_addresses(cur, addresses: Dict[str, str]) -> int:
    """
    Update existing clubs in the database with addresses from CSV file.
    This ensures that clubs that were created without addresses get updated
    with addresses when the CSV data is available.
    
    Args:
        cur: Database cursor
        addresses: Dictionary of club names to addresses from CSV
        
    Returns:
        Number of clubs updated with addresses
    """
    if not addresses:
        return 0
    
    print("\n🔄 Updating existing clubs with addresses...")
    
    # Get all clubs without addresses
    cur.execute("SELECT id, name FROM clubs WHERE club_address IS NULL OR club_address = ''")
    clubs_without_addresses = cur.fetchall()
    
    if not clubs_without_addresses:
        print("  ✅ All clubs already have addresses")
        return 0
    
    print(f"  📊 Found {len(clubs_without_addresses)} clubs without addresses")
    
    updated_count = 0
    
    for club_id, club_name in clubs_without_addresses:
        # Try to find address using enhanced normalization
        address = find_club_address(club_name, addresses)
        
        if address:
            # Update the club with the address
            cur.execute("""
                UPDATE clubs 
                SET club_address = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (address, club_id))
            
            normalized_name = normalize_club_name(club_name)
            print(f"    ✅ Updated: {club_name} -> {normalized_name} -> {address[:60]}...")
            updated_count += 1
    
    print(f"  🎉 Updated {updated_count} existing clubs with addresses")
    return updated_count


def main():
    """Main function to start a season for a league."""
    parser = argparse.ArgumentParser(description="Start a season for a league by importing players data")
    parser.add_argument("league_key", help="League key (e.g., CNSWPL, APTA_CHICAGO)")
    parser.add_argument("--test-file", help="Test with a specific JSON file instead of the default players.json")
    parser.add_argument("--skip-addresses", action="store_true", help="Skip loading club addresses from CSV")
    args = parser.parse_args()
    
    league_key = args.league_key.upper()
    
    print(f"Starting season for league: {league_key}")
    
    # Load players data
    print("Loading players data...")
    if args.test_file:
        # Test mode - use specified file
        json_path = args.test_file
        if not os.path.exists(json_path):
            print(f"ERROR: Test file {json_path} not found")
            exit(1)
        with open(json_path, 'r') as f:
            players_data = json.load(f)
        print(f"TEST MODE: Loaded {len(players_data)} player records from {json_path}")
    else:
        # Normal mode - use default players.json
        players_data = load_players_json(league_key)
        print(f"Loaded {len(players_data)} player records")
    
    # Extract unique entities with validation
    clubs, series, teams, players, validation_errors = extract_unique_entities(players_data)
    print(f"Found {len(clubs)} clubs, {len(series)} series, {len(teams)} teams, {len(players)} players")
    
    # If in test mode, just show validation results and exit
    if args.test_file:
        print(f"\n🧪 TEST MODE - Validation Results:")
        print(f"    Total records processed: {len(players_data)}")
        print(f"    Valid records: {len(players_data) - len(validation_errors)}")
        print(f"    Invalid records: {len(validation_errors)}")
        if validation_errors:
            print(f"    Success rate: {((len(players_data) - len(validation_errors)) / len(players_data) * 100):.1f}%")
            print(f"\n    Validation errors found:")
            for error in validation_errors:
                print(f"      {error}")
        else:
            print(f"    Success rate: 100.0%")
        print(f"\n✅ Test completed successfully!")
        return
    
    # Get database connection
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # Get league ID
        league_id = get_league_id(cur, league_key)
        if not league_id:
            print(f"ERROR: League '{league_key}' not found")
            exit(1)
        print(f"Found league ID: {league_id}")
        
        # Check if players table has tenniscores_player_id column
        has_external_id = check_tenniscores_player_id_column(cur)
        print(f"Players table has tenniscores_player_id column: {has_external_id}")
        
        # Load club addresses from CSV
        club_addresses = {}
        if not args.skip_addresses:
            print("\nLoading club addresses from CSV...")
            club_addresses = load_club_addresses()
        else:
            print("\nSkipping club address loading (--skip-addresses flag)")
        
        print("\nUpserting clubs...")
        club_map = {}
        clubs_with_addresses = 0
        for club_name in clubs:
            print(f"    Processing club: {club_name}")
            if club_addresses:
                club_id = upsert_club_with_address(cur, club_name, league_id, club_addresses)
                if find_club_address(club_name, club_addresses):
                    clubs_with_addresses += 1
            else:
                club_id = upsert_club(cur, club_name, league_id)
            club_map[club_name] = club_id
            print(f"      -> Club ID: {club_id}")
        print(f"  Clubs: {len(clubs)} processed")
        if club_addresses:
            print(f"  Clubs with addresses: {clubs_with_addresses}")
            
            # Update existing clubs with addresses
            updated_existing = update_existing_clubs_with_addresses(cur, club_addresses)
            if updated_existing > 0:
                print(f"  📈 Total clubs with addresses after update: {clubs_with_addresses + updated_existing}")
        
        print("Upserting series...")
        series_map = {}
        for series_name in series:
            series_id = upsert_series(cur, series_name, league_id)
            series_map[series_name] = series_id
        
        # Create additional letter-based series that might be needed for teams
        letter_series_created = create_letter_based_series(cur, league_id, teams)
        if letter_series_created:
            print(f"  Created {letter_series_created} additional letter-based series")
        
        print(f"  Series: {len(series)} processed")
        
        print("Upserting teams and players...")
        team_inserted, team_existing, team_skipped = upsert_teams_and_players(cur, league_id, clubs, series, teams)
        print(f"  Teams: {team_inserted} inserted, {team_existing} existing, {team_skipped} skipped")
        
        print("Upserting players...")
        player_inserted, player_updated, player_existing, player_skipped = upsert_players(cur, league_id, players_data, has_external_id)
        print(f"  Players: {player_inserted} inserted, {player_updated} updated, {player_existing} existing, {player_skipped} skipped")
        
        # Assign players to teams
        assigned, already_assigned, failed = assign_players_to_teams(cur, league_id)
        print(f"  Players assigned to teams: {assigned} inserted, {already_assigned} already assigned, {failed} failed")
        
        # Fix any existing players with missing team assignments
        fixed, fix_failed = fix_existing_team_assignments(cur, league_id)
        if fixed > 0:
            print(f"  Fixed existing team assignments: {fixed} fixed, {fix_failed} failed")
        
        # Commit transaction
        conn.commit()
        print("\nSeason started successfully!")
        
        # Run integrity checks
        run_integrity_checks(cur, league_id)
        
        # Log club normalization variants
        if _seen_variants:
            print("\n[club-normalizer] Variants observed:")
            for base, raws in sorted(_seen_variants.items()):
                if len(raws) > 1:
                    print(f"  {base}: {sorted(raws)}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

def create_letter_based_series(cur, league_id, teams):
    """Create additional letter-based series that might be needed for teams."""
    created_count = 0
    
    # Get league string ID to check if this is APTA
    cur.execute("SELECT league_id FROM leagues WHERE id = %s", (league_id,))
    league_result = cur.fetchone()
    league_string_id = league_result[0] if league_result else ""
    is_apta = league_string_id.startswith('APTA')
    
    # Extract all potential series names from team names
    needed_series = set()
    for team_name in teams:
        _, series_name, _ = parse_team_name(team_name)
        if series_name and series_name not in needed_series:
            needed_series.add(series_name)
    
    # Check which series already exist and create missing ones
    for series_name in needed_series:
        # VALIDATION: Prevent letter series (A, B, C, D, E, F, etc.) in APTA league
        # Letter series are only for CNSWPL and NSTF Sunday leagues
        if is_apta and re.match(r'^Series [A-Z]$', series_name):
            print(f"    ⚠️ Skipping letter series '{series_name}' for APTA league (not allowed)")
            continue
        
        cur.execute("SELECT id FROM series WHERE name = %s AND league_id = %s", (series_name, league_id))
        if not cur.fetchone():
            try:
                cur.execute("""
                    INSERT INTO series (name, display_name, league_id) 
                    VALUES (%s, %s, %s) 
                    ON CONFLICT (name, league_id) DO NOTHING
                """, (series_name, series_name, league_id))
                if cur.rowcount > 0:
                    created_count += 1
                    print(f"    Created series: {series_name}")
            except Exception as e:
                print(f"    Warning: Could not create series {series_name}: {e}")
    
    return created_count

if __name__ == "__main__":
    main()
