#!/usr/bin/env python3

"""
Rally Series Stats Import Script

This script imports series statistics from JSON files with upsert functionality.
Handles both new imports and updates to existing records safely.
"""

import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
sys.path.insert(0, project_root)

from database_utils import execute_query, execute_query_one


def normalize_league_id(league_id: str) -> str:
    """Normalize league ID to standard format"""
    if not league_id:
        return ""
    
    league_id = league_id.strip()
    
    # Map common variations to standard IDs (case-sensitive)
    league_mapping = {
        "APTA": "aptachicago",
        "APTA CHICAGO": "aptachicago",
        "APTA_CHICAGO": "aptachicago",
        "aptachicago": "aptachicago",
        "APTACHICAGO": "aptachicago",
        "NORTH SHORE TENNIS FOUNDATION": "nstf",
        "NSTF": "nstf",
        "nstf": "nstf",
        "CNSWPL": "CNSWPL",
        "cnswpl": "CNSWPL",
    }
    
    return league_mapping.get(league_id, league_id)


def load_series_stats_json(league_id: str) -> List[Dict]:
    """Load series stats JSON file for a specific league"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    
    # Map league names to directory names
    league_dir_mapping = {
        "aptachicago": "APTA_CHICAGO",
        "nstf": "NSTF",
        "CNSWPL": "CNSWPL",
        # Keep backward compatibility
        "APTA CHICAGO": "APTA_CHICAGO",
        "APTA_CHICAGO": "APTA_CHICAGO",
        "NORTH SHORE TENNIS FOUNDATION": "NORTH SHORE TENNIS FOUNDATION",
        "NSTF": "NSTF",
    }
    
    # Get the correct directory name
    league_dir = league_dir_mapping.get(league_id, league_id)
    
    # Build path to league data directory
    league_data_dir = os.path.join(project_root, "data", "leagues", league_dir)
    json_path = os.path.join(league_data_dir, "series_stats.json")
    
    if not os.path.exists(json_path):
        print(f"❌ Series stats file not found: {json_path}")
        print(f"🔍 Tried directory: {league_data_dir}")
        return []
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Loaded {len(data)} series stats records from {json_path}")
        return data
    except Exception as e:
        print(f"❌ Error loading series stats: {str(e)}")
        return []


def get_league_db_id(league_id: str) -> Optional[int]:
    """Get database ID for league"""
    # Map lowercase league IDs to database league_ids
    league_db_mapping = {
        "aptachicago": "APTA_CHICAGO",
        "nstf": "NSTF",
        "cnswpl": "CNSWPL",
    }
    
    # Use mapped league_id for database lookup
    db_league_id = league_db_mapping.get(league_id, league_id)
    
    result = execute_query_one(
        "SELECT id FROM leagues WHERE league_id = %s",
        (db_league_id,)
    )
    return result["id"] if result else None


def get_series_db_id(series_name: str, league_db_id: int) -> Optional[int]:
    """Get database ID for series"""
    result = execute_query_one("""
        SELECT s.id FROM series s
        JOIN series_leagues sl ON s.id = sl.series_id
        WHERE s.name = %s AND sl.league_id = %s
    """, (series_name, league_db_id))
    return result["id"] if result else None


def get_team_db_id(team_name: str, league_db_id: int, series_db_id: int) -> Optional[int]:
    """Get database ID for team"""
    result = execute_query_one("""
        SELECT id FROM teams 
        WHERE team_name = %s AND league_id = %s AND series_id = %s
    """, (team_name, league_db_id, series_db_id))
    return result["id"] if result else None


def import_series_stats(series_stats_data: List[Dict], league_id: str) -> Dict:
    """Import series stats with upsert functionality"""
    print(f"📥 Importing series stats for {league_id}...")
    
    # Get league database ID
    league_db_id = get_league_db_id(league_id)
    if not league_db_id:
        print(f"❌ League not found in database: {league_id}")
        return {"imported": 0, "updated": 0, "errors": 0, "skipped": 0}
    
    print(f"🔍 Found league database ID: {league_db_id}")
    
    imported = 0
    updated = 0
    errors = 0
    skipped = 0
    
    for record in series_stats_data:
        try:
            series = record.get("series", "").strip()
            team = record.get("team", "").strip()
            points = record.get('points', 0)
            
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
            
            if not all([series, team]):
                skipped += 1
                continue
            

            
            # Get series and team database IDs
            series_db_id = get_series_db_id(series, league_db_id)
            team_db_id = get_team_db_id(team, league_db_id, series_db_id) if series_db_id else None
            
            # Insert with upsert logic
            result = execute_query("""
                INSERT INTO series_stats (
                    series, team, series_id, team_id, points, matches_won, matches_lost, matches_tied,
                    lines_won, lines_lost, lines_for, lines_ret,
                    sets_won, sets_lost, games_won, games_lost,
                    league_id, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (league_id, series, team) DO UPDATE SET
                    points = EXCLUDED.points,
                    matches_won = EXCLUDED.matches_won,
                    matches_lost = EXCLUDED.matches_lost,
                    matches_tied = EXCLUDED.matches_tied,
                    lines_won = EXCLUDED.lines_won,
                    lines_lost = EXCLUDED.lines_lost,
                    lines_for = EXCLUDED.lines_for,
                    lines_ret = EXCLUDED.lines_ret,
                    sets_won = EXCLUDED.sets_won,
                    sets_lost = EXCLUDED.sets_lost,
                    games_won = EXCLUDED.games_won,
                    games_lost = EXCLUDED.games_lost,
                    series_id = EXCLUDED.series_id,
                    team_id = EXCLUDED.team_id,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id, (xmax = 0) as is_insert
            """, (
                series, team, series_db_id, team_db_id, points,
                matches_won, matches_lost, matches_tied,
                lines_won, lines_lost, lines_for, lines_ret,
                sets_won, sets_lost, games_won, games_lost,
                league_db_id
            ))
            
            if result:
                if result[0]["is_insert"]:
                    imported += 1
                else:
                    updated += 1
            
        except Exception as e:
            errors += 1
            if errors <= 5:  # Only log first 5 errors
                print(f"❌ Error importing record for {team}: {str(e)}")
    
    return {
        "imported": imported,
        "updated": updated,
        "errors": errors,
        "skipped": skipped
    }


def validate_import(league_id: str) -> Dict:
    """Validate the import results"""
    print(f"🔍 Validating import for {league_id}...")
    
    league_db_id = get_league_db_id(league_id)
    if not league_db_id:
        return {"total": 0, "with_series_id": 0, "with_team_id": 0}
    
    # Get total records for this league
    total = execute_query_one(
        "SELECT COUNT(*) as count FROM series_stats WHERE league_id = %s",
        (league_db_id,)
    )["count"]
    
    # Get records with series_id
    with_series_id = execute_query_one(
        "SELECT COUNT(*) as count FROM series_stats WHERE league_id = %s AND series_id IS NOT NULL",
        (league_db_id,)
    )["count"]
    
    # Get records with team_id
    with_team_id = execute_query_one(
        "SELECT COUNT(*) as count FROM series_stats WHERE league_id = %s AND team_id IS NOT NULL",
        (league_db_id,)
    )["count"]
    
    return {
        "total": total,
        "with_series_id": with_series_id,
        "with_team_id": with_team_id
    }


def main():
    """Main execution function"""
    print("🎾 Rally Series Stats Import Script")
    print("=" * 50)
    
    if len(sys.argv) != 2:
        print("Usage: python import_stats.py <league_id>")
        print("Example: python import_stats.py APTA_CHICAGO")
        sys.exit(1)
    
    league_id = normalize_league_id(sys.argv[1])
    print(f"🎯 Target League: {league_id}")
    
    # Load series stats data
    series_stats_data = load_series_stats_json(league_id)
    if not series_stats_data:
        print("❌ No data to import")
        sys.exit(1)
    
    # Import the data
    start_time = datetime.now()
    results = import_series_stats(series_stats_data, league_id)
    end_time = datetime.now()
    
    # Print results
    print(f"\n📊 Import Results:")
    print(f"   ✅ New records: {results['imported']}")
    print(f"   🔄 Updated records: {results['updated']}")
    print(f"   ❌ Errors: {results['errors']}")
    print(f"   ⏭️  Skipped: {results['skipped']}")
    print(f"   ⏱️  Duration: {end_time - start_time}")
    
    # Validate import
    validation = validate_import(league_id)
    print(f"\n🔍 Validation Results:")
    print(f"   📊 Total records: {validation['total']}")
    if validation['total'] > 0:
        print(f"   🔗 With series_id: {validation['with_series_id']} ({validation['with_series_id']/validation['total']*100:.1f}%)")
        print(f"   🔗 With team_id: {validation['with_team_id']} ({validation['with_team_id']/validation['total']*100:.1f}%)")
    else:
        print(f"   🔗 With series_id: {validation['with_series_id']} (0.0%)")
        print(f"   🔗 With team_id: {validation['with_team_id']} (0.0%)")
    
    if results['errors'] > 0:
        print(f"\n⚠️  Import completed with {results['errors']} errors")
        sys.exit(1)
    else:
        print(f"\n✅ Import completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main() 