"""
Import previous season match history data into match_scores_previous_seasons table.

This script imports data from data/leagues/APTA_CHICAGO/match_history_2024_2025.json
into the match_scores_previous_seasons table with season = "2024-2025".
"""

import json
import sys
import os
from datetime import datetime
from dateutil import parser

# Add parent directory to path to import from Rally modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database_config import get_db
from psycopg2.extras import RealDictCursor
from database_utils import execute_query, execute_query_one


def parse_match_date(date_str):
    """Parse date string in DD-Mon-YY format to datetime.date"""
    if not date_str:
        return None
    try:
        # Handle DD-Mon-YY format like "11-Feb-25"
        parsed_date = datetime.strptime(date_str, "%d-%b-%y")
        return parsed_date.date()
    except ValueError:
        try:
            # Try more general parsing
            parsed_date = parser.parse(date_str)
            return parsed_date.date()
        except Exception:
            print(f"Warning: Could not parse date: {date_str}")
            return None


def get_league_id(league_identifier):
    """Get database league ID from league identifier"""
    query = "SELECT id FROM leagues WHERE league_id = %s OR league_name = %s"
    result = execute_query_one(query, [league_identifier, league_identifier])
    if result:
        return result['id']
    return None


def get_team_id(team_name, league_id):
    """Get team ID from team name and league ID"""
    if not team_name or not league_id:
        return None
    
    query = """
        SELECT id FROM teams 
        WHERE team_name = %s AND league_id = %s
        LIMIT 1
    """
    result = execute_query_one(query, [team_name.strip(), league_id])
    if result:
        return result['id']
    return None


def check_duplicate_match(cur, tenniscores_match_id, season):
    """Check if match already exists in previous seasons table"""
    cur.execute(
        """
        SELECT id FROM match_scores_previous_seasons 
        WHERE tenniscores_match_id = %s AND season = %s
        """,
        (tenniscores_match_id, season)
    )
    result = cur.fetchone()
    return result is not None


def import_match_record(cur, match_data, league_id, season):
    """Import a single match record into match_scores_previous_seasons"""
    
    # Extract match data
    match_date_str = match_data.get("Date", "").strip()
    match_date = parse_match_date(match_date_str)
    
    home_team = match_data.get("Home Team", "").strip()
    away_team = match_data.get("Away Team", "").strip()
    
    # Extract player IDs
    home_player_1_id = match_data.get("Home Player 1 ID", "").strip() or None
    home_player_2_id = match_data.get("Home Player 2 ID", "").strip() or None
    away_player_1_id = match_data.get("Away Player 1 ID", "").strip() or None
    away_player_2_id = match_data.get("Away Player 2 ID", "").strip() or None
    
    # Extract player names
    home_player_1_name = match_data.get("Home Player 1", "").strip() or None
    home_player_2_name = match_data.get("Home Player 2", "").strip() or None
    away_player_1_name = match_data.get("Away Player 1", "").strip() or None
    away_player_2_name = match_data.get("Away Player 2", "").strip() or None
    
    scores = match_data.get("Scores", "").strip()
    winner = match_data.get("Winner", "").strip().lower() or None
    
    # Get tenniscores_match_id (use match_id from JSON)
    tenniscores_match_id = match_data.get("match_id", "").strip() or None
    
    # Skip if no match ID (required for deduplication)
    if not tenniscores_match_id:
        return None, "no_match_id"
    
    # Check for duplicate
    if check_duplicate_match(cur, tenniscores_match_id, season):
        return None, "duplicate"
    
    # Get team IDs
    home_team_id = get_team_id(home_team, league_id) if home_team else None
    away_team_id = get_team_id(away_team, league_id) if away_team else None
    
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
        if result:
            return result[0], "inserted"
        return None, "insert_failed"
    except Exception as e:
        # Silently track errors - they'll be counted in the summary
        # Most common cause: foreign key constraint on team_id (team doesn't exist in staging)
        return None, f"error: {type(e).__name__}"


def main():
    """Main import function"""
    print("=" * 80)
    print("IMPORTING PREVIOUS SEASON MATCH HISTORY (2024-2025)")
    print("=" * 80)
    
    # Configuration
    json_file = "data/leagues/APTA_CHICAGO/match_history_2024_2025.json"
    league_identifier = "APTA_CHICAGO"
    season = "2024-2025"
    
    # Check if file exists
    if not os.path.exists(json_file):
        print(f"ERROR: File not found: {json_file}")
        return 1
    
    # Get league ID
    print(f"\nLooking up league: {league_identifier}")
    league_id = get_league_id(league_identifier)
    if not league_id:
        print(f"ERROR: Could not find league ID for {league_identifier}")
        return 1
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
    
    try:
        with get_db() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            for idx, match in enumerate(match_data, 1):
                if idx % 1000 == 0:
                    print(f"  Processing match {idx}/{len(match_data)}...")
                
                match_id, status = import_match_record(cur, match, league_id, season)
                
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
            cur.close()
        
    except Exception as e:
        print(f"\nERROR: Transaction failed due to error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Print summary
    print("\n" + "=" * 80)
    print("IMPORT SUMMARY")
    print("=" * 80)
    print(f"Total records processed: {len(match_data)}")
    print(f"Successfully inserted:   {stats['inserted']}")
    print(f"Duplicates skipped:      {stats['duplicate']}")
    print(f"No match ID:             {stats['no_match_id']}")
    print(f"Missing required fields: {stats['missing_required_fields']}")
    print(f"Errors:                  {stats['errors']}")
    print("=" * 80)
    
    # Verify import
    print("\nVerifying import...")
    verify_query = """
        SELECT COUNT(*) as total_count, 
               COUNT(DISTINCT tenniscores_match_id) as unique_matches,
               MIN(match_date) as earliest_date,
               MAX(match_date) as latest_date
        FROM match_scores_previous_seasons
        WHERE season = %s AND league_id = %s
    """
    verify_result = execute_query_one(verify_query, [season, league_id])
    if verify_result:
        print(f"Total records in database: {verify_result['total_count']}")
        print(f"Unique matches:            {verify_result['unique_matches']}")
        print(f"Date range:                {verify_result['earliest_date']} to {verify_result['latest_date']}")
    
    print("\n✅ Import complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

