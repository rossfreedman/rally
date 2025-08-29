#!/usr/bin/env python3
"""
Import Match Scores Script for Rally App

Imports match scores into match_scores table, mapping:
- league name → league_id
- home_team → home_team_id (via club/series lookup)
- away_team → away_team_id (via club/series lookup)
- player names → player IDs
- match_id → tenniscores_match_id

No duplicates, comprehensive validation, and data integrity checks.

Usage: python data/etl/import/import_match_scores.py <LEAGUE_KEY> [--file <JSON_FILE>]
Example: python data/etl/import/import_match_scores.py APTA_CHICAGO
"""

import argparse
import json
import os
import sys
import re
from datetime import datetime
import os
import psycopg2

# Add the project root to Python path to import database_config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from database_config import get_db_url, get_database_mode, is_local_development

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


def load_json_file(file_path):
    """Load and parse JSON file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            raise ValueError(f"Expected JSON array, got {type(data)}")
        
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def validate_entity_name(name, entity_type):
    """Validate entity names (clubs, series, teams)."""
    if not name or not isinstance(name, str):
        return False, f"{entity_type} name is required and must be a string"
    
    name = name.strip()
    if not name:
        return False, f"{entity_type} name cannot be empty"
    
    if len(name) > 100:
        return False, f"{entity_type} name too long (max 100 chars)"
    
    # Prevent numeric-only names
    if re.match(r'^[0-9]+$', name):
        return False, f"{entity_type} name cannot be numeric only"
    
    return True, name


def validate_match_data(match_data):
    """Validate match data for required fields and data quality."""
    errors = []
    
    # Required fields
    required_fields = ["Home Team", "Away Team", "Scores", "Winner"]
    for field in required_fields:
        if not match_data.get(field):
            errors.append(f"Missing required field: {field}")
    
    # Validate winner field
    winner = match_data.get("Winner", "").strip().lower()
    if winner and winner not in ["home", "away"]:
        errors.append(f"Invalid winner value: {winner} (must be 'home' or 'away')")
    
    # Validate scores format
    scores = match_data.get("Scores", "").strip()
    if scores and not re.match(r'^[\d\-,\s]+$', scores):
        errors.append(f"Invalid scores format: {scores}")
    
    # Validate date if present
    date_str = match_data.get("Date", "").strip()
    if date_str:
        try:
            # Try DD-Mon-YY format first
            datetime.strptime(date_str, "%d-%b-%y")
        except ValueError:
            try:
                # Try MM/DD/YYYY format
                datetime.strptime(date_str, "%m/%d/%Y")
            except ValueError:
                try:
                    # Try YYYY-MM-DD format
                    datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    errors.append(f"Invalid date format: {date_str}")
    
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


def lookup_existing_team(cur, league_id, team_name):
    """Look up existing team by name in the current league."""
    # Try to find team by exact name match
    cur.execute("""
        SELECT id, club_id, series_id FROM teams 
        WHERE league_id = %s AND team_name = %s
        LIMIT 1
    """, (league_id, team_name))
    
    result = cur.fetchone()
    if result:
        return result[0], result[1], result[2]  # team_id, club_id, series_id
    
    # If not found, try to find by similar name patterns
    # This handles cases where the team name might be slightly different
    cur.execute("""
        SELECT id, club_id, series_id FROM teams 
        WHERE league_id = %s AND team_name LIKE %s
        LIMIT 1
    """, (league_id, f"%{team_name.split()[-1]}%"))  # Try to match the last part (e.g., "22")
    
    result = cur.fetchone()
    if result:
        return result[0], result[1], result[2]
    
    return None, None, None


def upsert_club(cur, club_name, league_id):
    """Upsert club and return ID."""
    if not club_name:
        return None
    
    # Check if teams table has display_name column
    if column_exists(cur, "teams", "display_name"):
        cur.execute("""
            INSERT INTO clubs (name) 
            VALUES (%s) 
            ON CONFLICT (name) DO NOTHING 
            RETURNING id
        """, (club_name,))
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Get existing ID
        cur.execute("SELECT id FROM clubs WHERE name = %s", (club_name,))
        return cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO clubs (name) 
            VALUES (%s) 
            ON CONFLICT (name) DO NOTHING 
            RETURNING id
        """, (club_name,))
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Get existing ID
        cur.execute("SELECT id FROM clubs WHERE name = %s", (club_name,))
        return cur.fetchone()[0]


def upsert_series(cur, series_name, league_id):
    """Upsert series and return ID."""
    if not series_name:
        return None
    
    # Check if teams table has display_name column
    if column_exists(cur, "teams", "display_name"):
        cur.execute("""
            INSERT INTO series (name, league_id) 
            VALUES (%s, %s) 
            ON CONFLICT (name, league_id) DO NOTHING 
            RETURNING id
        """, (series_name, league_id))
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Get existing ID
        cur.execute("SELECT id FROM series WHERE name = %s AND league_id = %s", (series_name, league_id))
        return cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO series (name, league_id) 
            VALUES (%s, %s) 
            ON CONFLICT (name, league_id) DO NOTHING 
            RETURNING id
        """, (series_name, league_id))
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Get existing ID
        cur.execute("SELECT id FROM series WHERE name = %s AND league_id = %s", (series_name, league_id))
        return cur.fetchone()[0]


def upsert_team(cur, league_id, team_name, club_name, series_name):
    """Upsert team and return ID. Requires club and series names."""
    if not all([team_name, club_name, series_name]):
        return None
    
    club_id = upsert_club(cur, club_name, league_id)
    series_id = upsert_series(cur, series_name, league_id)
    
    # Create a unique team identifier that combines club and series
    # This prevents unique constraint violations
    unique_team_name = f"{club_name} - {series_name}"
    
    # Check if teams table has display_name column
    if column_exists(cur, "teams", "display_name"):
        cur.execute("""
            INSERT INTO teams (team_name, display_name, club_id, series_id, league_id) 
            VALUES (%s, %s, %s, %s, %s) 
            ON CONFLICT (team_name, league_id) DO NOTHING 
            RETURNING id
        """, (unique_team_name, team_name, club_id, series_id, league_id))
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Get existing ID
        cur.execute("SELECT id FROM teams WHERE team_name = %s AND league_id = %s", (unique_team_name, league_id))
        return cur.fetchone()[0]
    else:
        cur.execute("""
            INSERT INTO teams (name, club_id, series_id, league_id) 
            VALUES (%s, %s, %s, %s) 
            ON CONFLICT (name, league_id) DO NOTHING 
            RETURNING id
        """, (unique_team_name, club_id, series_id, league_id))
        result = cur.fetchone()
        if result:
            return result[0]
        
        # Get existing ID
        cur.execute("SELECT id FROM teams WHERE name = %s AND league_id = %s", (unique_team_name, league_id))
        return cur.fetchone()[0]


def check_existing_match(cur, league_id, tenniscores_match_id):
    """Check if a match record already exists."""
    if not tenniscores_match_id:
        return None
    
    cur.execute("""
        SELECT id FROM match_scores 
        WHERE league_id = %s AND tenniscores_match_id = %s
        LIMIT 1
    """, (league_id, tenniscores_match_id))
    
    result = cur.fetchone()
    return result[0] if result else None


def upsert_match_score(cur, league_id, match_data):
    """Upsert a single match score record with comprehensive validation."""
    # Validate data first
    is_valid, validation_errors = validate_match_data(match_data)
    if not is_valid:
        return None, f"validation_failed: {', '.join(validation_errors)}"
    
    # Extract required fields
    home_team_name = match_data.get("Home Team", "").strip()
    away_team_name = match_data.get("Away Team", "").strip()
    scores = match_data.get("Scores", "").strip()
    winner = match_data.get("Winner", "").strip().lower() or None
    
    # Extract optional fields
    match_date_str = match_data.get("Date", "").strip() or None
    match_id = match_data.get("match_id", "").strip() or None
    line = match_data.get("Line", "").strip() or None
    
    # Extract player information
    home_player_1 = match_data.get("Home Player 1", "").strip() or None
    home_player_2 = match_data.get("Home Player 2", "").strip() or None
    away_player_1 = match_data.get("Away Player 1", "").strip() or None
    away_player_2 = match_data.get("Away Player 2", "").strip() or None
    
    # Extract player IDs
    home_player_1_id = match_data.get("Home Player 1 ID", "").strip() or None
    home_player_2_id = match_data.get("Home Player 2 ID", "").strip() or None
    away_player_1_id = match_data.get("Away Player 1 ID", "").strip() or None
    away_player_2_id = match_data.get("Away Player 2 ID", "").strip() or None
    
    # Parse match_date if provided
    match_date = None
    if match_date_str:
        try:
            # Try DD-Mon-YY format first
            match_date = datetime.strptime(match_date_str, "%d-%b-%y").date()
        except ValueError:
            try:
                # Try MM/DD/YYYY format
                match_date = datetime.strptime(match_date_str, "%m/%d/%Y").date()
            except ValueError:
                try:
                    # Try YYYY-MM-DD format
                    match_date = datetime.strptime(match_date_str, "%Y-%m-%d").date()
                except ValueError:
                    return None, f"date_parsing_failed: {match_date_str}"
    
    # Parse team names to get club and series
    home_club, home_series, home_number = parse_team_name(home_team_name)
    away_club, away_series, away_number = parse_team_name(away_team_name)
    
    if not all([home_club, home_series, away_club, away_series]):
        return None, f"team_parsing_failed: could not extract club/series from teams"
    
    try:
        # Look up existing teams first
        home_team_id, home_club_id, home_series_id = lookup_existing_team(cur, league_id, home_team_name)
        away_team_id, away_club_id, away_series_id = lookup_existing_team(cur, league_id, away_team_name)
        
        # If teams not found, create them
        if not home_team_id:
            print(f"  ⚠️ Team '{home_team_name}' not found. Creating...")
            home_team_id = upsert_team(cur, league_id, home_team_name, home_club, home_series)
            if not home_team_id:
                return None, f"home_team_creation_failed: could not create team '{home_team_name}'"
            print(f"  Team '{home_team_name}' created (ID: {home_team_id})")
        else:
            print(f"  Team '{home_team_name}' found (ID: {home_team_id})")
        
        if not away_team_id:
            print(f"  ⚠️ Team '{away_team_name}' not found. Creating...")
            away_team_id = upsert_team(cur, league_id, away_team_name, away_club, away_series)
            if not away_team_id:
                return None, f"away_team_creation_failed: could not create team '{away_team_name}'"
            print(f"  Team '{away_team_name}' created (ID: {away_team_id})")
        else:
            print(f"  Team '{away_team_name}' found (ID: {away_team_id})")
        
        # Check for existing match record
        existing_id = check_existing_match(cur, league_id, match_id)
        
        if existing_id:
            # Update existing record
            cur.execute("""
                UPDATE match_scores 
                SET match_date = %s, home_team = %s, away_team = %s, 
                    home_team_id = %s, away_team_id = %s, scores = %s, winner = %s,
                    home_player_1_id = %s, home_player_2_id = %s, 
                    away_player_1_id = %s, away_player_2_id = %s
                WHERE id = %s
                RETURNING id
            """, (match_date, home_team_name, away_team_name, home_team_id, away_team_id, scores, winner,
                  home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id, existing_id))
            return existing_id, "updated"
        else:
            # Insert new record
            cur.execute("""
                INSERT INTO match_scores (
                    league_id, match_date, home_team, away_team, home_team_id, away_team_id,
                    scores, winner, tenniscores_match_id,
                    home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (league_id, match_date, home_team_name, away_team_name, home_team_id, away_team_id, scores, winner, match_id,
                  home_player_1_id, home_player_2_id, away_player_1_id, away_player_2_id))
            result = cur.fetchone()
            if result:
                return result[0], "inserted"
            else:
                return None, "insert_failed"
                
    except Exception as e:
        raise Exception(f"Failed to upsert match score for {home_team_name} vs {away_team_name}: {e}")


def run_integrity_checks(cur, league_id):
    """Run post-import integrity checks."""
    print("\n🔍 Running post-import integrity checks...")
    
    # Check for matches without team assignments
    cur.execute("""
        SELECT COUNT(*) FROM match_scores 
        WHERE league_id = %s AND (home_team_id IS NULL OR away_team_id IS NULL)
    """, (league_id,))
    
    missing_teams = cur.fetchone()[0]
    if missing_teams == 0:
        print("  ✅ All matches have proper team assignments")
    else:
        print(f"  ⚠️ Found {missing_teams} matches with missing team assignments")
    
    # Check for duplicate matches
    cur.execute("""
        SELECT tenniscores_match_id, COUNT(*) 
        FROM match_scores 
        WHERE league_id = %s AND tenniscores_match_id IS NOT NULL
        GROUP BY tenniscores_match_id 
        HAVING COUNT(*) > 1
    """, (league_id,))
    
    duplicates = cur.fetchall()
    if not duplicates:
        print("  ✅ No duplicate match records found")
    else:
        print(f"  ⚠️ Found {len(duplicates)} duplicate match records")
        for match_id, count in duplicates[:5]:  # Show first 5
            print(f"    {match_id}: {count} copies")
    
    # Check for matches without dates
    cur.execute("""
        SELECT COUNT(*) FROM match_scores 
        WHERE league_id = %s AND match_date IS NULL
    """, (league_id,))
    
    missing_dates = cur.fetchone()[0]
    if missing_dates == 0:
        print("  ✅ All matches have dates")
    else:
        print(f"  ⚠️ Found {missing_dates} matches without dates")
    
    # Summary
    total_issues = missing_teams + len(duplicates) + missing_dates
    print(f"\n📊 Integrity check summary: {total_issues} issues found")
    
    return total_issues


def import_match_scores(cur, league_id, matches_data):
    """Import match scores from JSON data."""
    inserted, updated, existing, skipped, validation_failed = 0, 0, 0, 0, 0
    
    for i, match_data in enumerate(matches_data):
        try:
            match_id, action = upsert_match_score(cur, league_id, match_data)
            
            if action == "inserted":
                inserted += 1
            elif action == "updated":
                updated += 1
            elif action == "existing":
                existing += 1
            else:
                skipped += 1
                
            # Progress indicator for large imports
            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{len(matches_data)} records...")
                
        except Exception as e:
            print(f"ERROR processing match {i + 1}: {e}")
            skipped += 1
    
    return inserted, updated, existing, skipped, validation_failed


def main():
    parser = argparse.ArgumentParser(description="Import match scores for a league")
    parser.add_argument("league_key", help="League key (e.g., CNSWPL, APTA_CHICAGO)")
    parser.add_argument("--file", help="Custom JSON file path (optional)")
    parser.add_argument("--limit", type=int, help="Limit number of records to process (for testing)")
    args = parser.parse_args()
    
    league_key = args.league_key.strip()
    if not league_key:
        print("ERROR: League key cannot be empty")
        sys.exit(1)
    
    # Determine input file path
    if args.file:
        json_path = args.file
    else:
        json_path = f"data/leagues/{league_key}/match_history.json"
    
    print(f"Importing match scores for league: {league_key}")
    
    # Show environment information
    print(f"Environment: {'Local Development' if is_local_development() else 'Railway/Production'}")
    print(f"Database Mode: {get_database_mode()}")
    print(f"Database URL: {get_db_url()}")
    print()
    
    print(f"Input file: {json_path}")
    
    try:
        # Load JSON data
        print("Loading match scores data...")
        matches_data = load_json_file(json_path)
        print(f"Loaded {len(matches_data)} match records")
        
        # Apply limit if specified
        if args.limit:
            matches_data = matches_data[:args.limit]
            print(f"Limited to {len(matches_data)} records for testing")
        
        # Database connection
        conn = get_conn()
        cur = conn.cursor()
        
        try:
            # Get league ID
            league_id = get_league_id(cur, league_key)
            print(f"Found league ID: {league_id}")
            
            # Import match scores
            print("Importing match scores...")
            inserted, updated, existing, skipped, validation_failed = import_match_scores(cur, league_id, matches_data)
            
            # Run integrity checks
            integrity_issues = run_integrity_checks(cur, league_id)
            
            # Commit transaction
            conn.commit()
            print(f"\nImport completed successfully!")
            print(f"Match scores: {inserted} inserted, {updated} updated, {existing} existing, {skipped} skipped, {validation_failed} validation failed")
            
        except Exception as e:
            conn.rollback()
            print(f"ERROR: Failed to import match scores: {e}")
            sys.exit(1)
        finally:
            cur.close()
            conn.close()
            
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
