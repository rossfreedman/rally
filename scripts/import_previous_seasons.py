"""
Import previous season data with player names.
This script imports both APTA Chicago and CNSWPL data.
Uses DATABASE_URL environment variable to connect to the appropriate database.
"""

import json
import sys
import os
from datetime import datetime
from dateutil import parser
import psycopg2
from psycopg2.extras import RealDictCursor

# Get database URL from environment variable
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)


def parse_match_date(date_str):
    """Parse date string in DD-Mon-YY format to datetime.date"""
    if not date_str:
        return None
    try:
        parsed_date = datetime.strptime(date_str, "%d-%b-%y")
        return parsed_date.date()
    except ValueError:
        try:
            parsed_date = parser.parse(date_str)
            return parsed_date.date()
        except Exception:
            print(f"Warning: Could not parse date: {date_str}")
            return None


def get_league_id(conn, league_identifier):
    """Get database league ID from league identifier"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id FROM leagues WHERE league_id = %s OR league_name = %s",
            [league_identifier, league_identifier]
        )
        result = cur.fetchone()
        return result['id'] if result else None


def get_team_id(conn, team_name, league_id):
    """Get team ID from team name and league ID"""
    if not team_name or not league_id:
        return None
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id FROM teams WHERE team_name = %s AND league_id = %s LIMIT 1",
            [team_name.strip(), league_id]
        )
        result = cur.fetchone()
        return result['id'] if result else None


def check_duplicate_match(cur, tenniscores_match_id, season):
    """Check if match already exists in previous seasons table"""
    cur.execute(
        "SELECT id FROM match_scores_previous_seasons WHERE tenniscores_match_id = %s AND season = %s",
        (tenniscores_match_id, season)
    )
    return cur.fetchone() is not None


def import_match_record(conn, cur, match_data, league_id, season):
    """Import a single match record into match_scores_previous_seasons"""
    
    # Extract match data
    match_date_str = (match_data.get("Date") or "").strip()
    match_date = parse_match_date(match_date_str)
    
    home_team = (match_data.get("Home Team") or "").strip()
    away_team = (match_data.get("Away Team") or "").strip()
    
    # Extract player IDs
    home_player_1_id = (match_data.get("Home Player 1 ID") or "").strip() or None
    home_player_2_id = (match_data.get("Home Player 2 ID") or "").strip() or None
    away_player_1_id = (match_data.get("Away Player 1 ID") or "").strip() or None
    away_player_2_id = (match_data.get("Away Player 2 ID") or "").strip() or None
    
    # Extract player names
    home_player_1_name = (match_data.get("Home Player 1") or "").strip() or None
    home_player_2_name = (match_data.get("Home Player 2") or "").strip() or None
    away_player_1_name = (match_data.get("Away Player 1") or "").strip() or None
    away_player_2_name = (match_data.get("Away Player 2") or "").strip() or None
    
    scores = (match_data.get("Scores") or "").strip()
    winner_val = (match_data.get("Winner") or "").strip().lower()
    winner = winner_val if winner_val else None
    
    # Get tenniscores_match_id
    tenniscores_match_id = (match_data.get("match_id") or "").strip() or None
    
    # Skip if no match ID
    if not tenniscores_match_id:
        return None, "no_match_id"
    
    # Check for duplicate
    if check_duplicate_match(cur, tenniscores_match_id, season):
        return None, "duplicate"
    
    # Get team IDs
    home_team_id = get_team_id(conn, home_team, league_id) if home_team else None
    away_team_id = get_team_id(conn, away_team, league_id) if away_team else None
    
    # Validate required fields
    if not home_team or not away_team or not scores:
        return None, "missing_required_fields"
    
    # Insert record
    try:
        cur.execute(
            """
            INSERT INTO match_scores_previous_seasons (
                league_id, match_date, home_team, away_team, 
                home_team_id, away_team_id,
                home_player_1_id, home_player_2_id, 
                away_player_1_id, away_player_2_id,
                home_player_1_name, home_player_2_name,
                away_player_1_name, away_player_2_name,
                scores, winner, tenniscores_match_id, season
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                league_id, match_date, home_team, away_team,
                home_team_id, away_team_id,
                home_player_1_id, home_player_2_id,
                away_player_1_id, away_player_2_id,
                home_player_1_name, home_player_2_name,
                away_player_1_name, away_player_2_name,
                scores, winner, tenniscores_match_id, season
            )
        )
        result = cur.fetchone()
        return result[0] if result else None, "inserted"
    except Exception as e:
        return None, f"error: {type(e).__name__}"


def import_league_data(conn, json_file, league_identifier, season):
    """Import data for a specific league"""
    print(f"\n{'='*80}")
    print(f"Importing {league_identifier} Previous Season Data")
    print(f"{'='*80}")
    
    # Check if file exists
    if not os.path.exists(json_file):
        print(f"ERROR: File not found: {json_file}")
        return False
    
    # Get league ID
    print(f"\nLooking up league: {league_identifier}")
    league_id = get_league_id(conn, league_identifier)
    if not league_id:
        print(f"ERROR: Could not find league ID for {league_identifier}")
        return False
    print(f"Found league ID: {league_id}")
    
    # Load JSON data
    print(f"\nLoading match history from: {json_file}")
    with open(json_file, 'r') as f:
        match_data = json.load(f)
    print(f"Loaded {len(match_data)} match records from JSON")
    
    # Import matches
    stats = {
        'inserted': 0,
        'duplicate': 0,
        'no_match_id': 0,
        'missing_required_fields': 0,
        'errors': 0
    }
    
    print(f"\nImporting matches with season = '{season}'...")
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        for idx, match in enumerate(match_data, 1):
            if idx % 1000 == 0:
                print(f"  Processing match {idx}/{len(match_data)}...")
            
            match_id, status = import_match_record(conn, cur, match, league_id, season)
            
            if status == "inserted":
                stats['inserted'] += 1
            elif status == "duplicate":
                stats['duplicate'] += 1
            elif status == "no_match_id":
                stats['no_match_id'] += 1
            elif status == "missing_required_fields":
                stats['missing_required_fields'] += 1
            elif status.startswith("error"):
                stats['errors'] += 1
        
        # Commit transaction
        conn.commit()
        print("\nTransaction committed successfully!")
    
    # Print summary
    print(f"\n{'='*80}")
    print("IMPORT SUMMARY")
    print(f"{'='*80}")
    print(f"Total records processed: {len(match_data)}")
    print(f"Successfully inserted:   {stats['inserted']}")
    print(f"Duplicates skipped:      {stats['duplicate']}")
    print(f"No match ID:             {stats['no_match_id']}")
    print(f"Missing required fields: {stats['missing_required_fields']}")
    print(f"Errors:                  {stats['errors']}")
    print(f"{'='*80}")
    
    return True


def main():
    """Main import function"""
    print("="*80)
    print("IMPORTING PREVIOUS SEASON DATA")
    print("="*80)
    
    season = "2024-2025"
    
    # Configuration
    leagues = [
        {
            "name": "APTA_CHICAGO",
            "file": "data/leagues/APTA_CHICAGO/match_history_2024_2025.json"
        },
        {
            "name": "CNSWPL",
            "file": "data/leagues/CNSWPL/cnswpl_match_history_2024_2025.json"
        }
    ]
    
    # Connect to database using environment variable
    print(f"\nConnecting to database...")
    print(f"Using DATABASE_URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'unknown'}")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        print("✅ Connected to database!")
    except Exception as e:
        print(f"ERROR: Could not connect to database: {e}")
        return 1
    
    try:
        # Import each league
        for league in leagues:
            success = import_league_data(conn, league["file"], league["name"], season)
            if not success:
                print(f"⚠️  Warning: Failed to import {league['name']}")
        
        # Verify total import
        print(f"\n{'='*80}")
        print("VERIFICATION")
        print(f"{'='*80}")
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT l.league_name, 
                       COUNT(*) as total_matches,
                       COUNT(home_player_1_name) + COUNT(home_player_2_name) + 
                       COUNT(away_player_1_name) + COUNT(away_player_2_name) as total_player_names
                FROM match_scores_previous_seasons msps
                JOIN leagues l ON msps.league_id = l.id
                WHERE season = %s
                GROUP BY l.league_name
                ORDER BY l.league_name
            """, [season])
            
            results = cur.fetchall()
            for row in results:
                print(f"\n{row['league_name']}:")
                print(f"  Total matches: {row['total_matches']}")
                print(f"  Total player names: {row['total_player_names']}")
        
        print(f"\n{'='*80}")
        print("✅ ALL IMPORTS COMPLETE!")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"\nERROR: Import failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

