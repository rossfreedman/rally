#!/usr/bin/env python3
"""
Script to prepare schedules.json for import by handling SW series data
and ensuring consistency with players.json
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

def load_json_file(file_path):
    """Load and return JSON data from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def analyze_sw_series_coverage(players_data, schedules_data):
    """Analyze SW series coverage between players and schedules."""
    print("=== SW SERIES COVERAGE ANALYSIS ===")
    
    # Get SW series from both files
    players_sw_series = set()
    schedules_sw_series = set()
    
    for player in players_data:
        series = player.get("Series", "")
        if "SW" in series:
            players_sw_series.add(series)
    
    for schedule in schedules_data:
        series = schedule.get("series", "")
        if "SW" in series:
            schedules_sw_series.add(series)
    
    print(f"SW series in players.json: {len(players_sw_series)}")
    print(f"SW series in schedules.json: {len(schedules_sw_series)}")
    
    print(f"\nSW series in players.json: {sorted(players_sw_series)}")
    print(f"SW series in schedules.json: {sorted(schedules_sw_series)}")
    
    # Check overlap
    common_sw_series = players_sw_series & schedules_sw_series
    sw_only_in_schedules = schedules_sw_series - players_sw_series
    sw_only_in_players = players_sw_series - schedules_sw_series
    
    print(f"\nCommon SW series: {len(common_sw_series)}")
    print(f"SW series only in schedules: {len(sw_only_in_schedules)}")
    print(f"SW series only in players: {len(sw_only_in_players)}")
    
    if sw_only_in_schedules:
        print(f"\nSW series only in schedules: {sorted(sw_only_in_schedules)}")
    
    return {
        'common_sw_series': common_sw_series,
        'sw_only_in_schedules': sw_only_in_schedules,
        'sw_only_in_players': sw_only_in_players
    }

def filter_schedules_by_series(schedules_data, include_sw=True):
    """Filter schedules data based on series inclusion."""
    if include_sw:
        return schedules_data
    
    # Filter out SW series
    filtered_schedules = []
    for schedule in schedules_data:
        series = schedule.get("series", "")
        if "SW" not in series:
            filtered_schedules.append(schedule)
    
    return filtered_schedules

def validate_team_coverage(players_data, schedules_data):
    """Validate that teams in schedules have corresponding player records."""
    print("\n=== TEAM COVERAGE VALIDATION ===")
    
    # Get all teams from schedules
    schedule_teams = set()
    for schedule in schedules_data:
        if schedule.get("home_team"):
            schedule_teams.add(schedule["home_team"])
        if schedule.get("away_team"):
            schedule_teams.add(schedule["away_team"])
    
    # Get all teams from players
    player_teams = set()
    for player in players_data:
        if player.get("Team"):
            player_teams.add(player["Team"])
    
    # Find teams in schedules but not in players
    missing_teams = schedule_teams - player_teams
    print(f"Teams in schedules but not in players: {len(missing_teams)}")
    
    if missing_teams:
        print("First 20 missing teams:")
        for i, team in enumerate(sorted(missing_teams)[:20]):
            print(f"  {team}")
        if len(missing_teams) > 20:
            print(f"  ... and {len(missing_teams) - 20} more")
    
    # Find teams in players but not in schedules
    missing_from_schedules = player_teams - schedule_teams
    print(f"\nTeams in players but not in schedules: {len(missing_from_schedules)}")
    
    if missing_from_schedules:
        print("First 20 teams missing from schedules:")
        for i, team in enumerate(sorted(missing_from_schedules)[:20]):
            print(f"  {team}")
        if len(missing_from_schedules) > 20:
            print(f"  ... and {len(missing_from_schedules) - 20} more")
    
    return {
        'missing_teams': missing_teams,
        'missing_from_schedules': missing_from_schedules
    }

def create_filtered_schedules(schedules_data, include_sw=True, output_file=None):
    """Create a filtered version of schedules.json."""
    filtered_data = filter_schedules_by_series(schedules_data, include_sw)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_data, f, indent=2)
        print(f"\nFiltered schedules saved to: {output_file}")
        print(f"Original entries: {len(schedules_data)}")
        print(f"Filtered entries: {len(filtered_data)}")
    
    return filtered_data

def generate_import_recommendations(sw_analysis, team_validation):
    """Generate recommendations for the import process."""
    print("\n=== IMPORT RECOMMENDATIONS ===")
    
    print("RECOMMENDATION 1: SW Series Handling")
    if sw_analysis['sw_only_in_schedules']:
        print(f"⚠️  WARNING: {len(sw_analysis['sw_only_in_schedules'])} SW series exist in schedules but not in players")
        print("   Options:")
        print("   a) Exclude SW series from import (recommended)")
        print("   b) Scrape missing SW series player data first")
        print("   c) Import SW series anyway (may cause data integrity issues)")
    else:
        print("✅ All SW series in schedules have corresponding player data")
    
    print("\nRECOMMENDATION 2: Missing Teams")
    if team_validation['missing_teams']:
        print(f"⚠️  WARNING: {len(team_validation['missing_teams'])} teams in schedules don't have player records")
        print("   This will cause import failures or orphaned records")
        print("   Recommended action: Filter out these teams or scrape missing player data")
    else:
        print("✅ All teams in schedules have corresponding player records")
    
    print("\nRECOMMENDATION 3: Import Strategy")
    if sw_analysis['sw_only_in_schedules'] or team_validation['missing_teams']:
        print("   RECOMMENDED: Use filtered schedules (exclude SW series and missing teams)")
        print("   This ensures data integrity and prevents import failures")
    else:
        print("   SAFE: Import all schedules data as-is")

def main():
    """Main function to prepare schedules for import."""
    base_path = Path("/Users/rossfreedman/dev/rally/data/leagues/APTA_CHICAGO")
    players_file = base_path / "players.json"
    schedules_file = base_path / "schedules.json"
    
    print("APTA_CHICAGO Schedules Import Preparation")
    print("=" * 50)
    
    # Load data
    print("Loading data files...")
    players_data = load_json_file(players_file)
    if not players_data:
        return
    
    schedules_data = load_json_file(schedules_file)
    if not schedules_data:
        return
    
    # Analyze SW series coverage
    sw_analysis = analyze_sw_series_coverage(players_data, schedules_data)
    
    # Validate team coverage
    team_validation = validate_team_coverage(players_data, schedules_data)
    
    # Generate recommendations
    generate_import_recommendations(sw_analysis, team_validation)
    
    # Ask user for decision
    print("\n" + "=" * 50)
    print("DECISION REQUIRED:")
    print("1. Include SW series in import (may cause issues)")
    print("2. Exclude SW series from import (recommended)")
    print("3. Create filtered schedules file for review")
    
    # For now, create filtered version
    print("\nCreating filtered schedules (excluding SW series)...")
    filtered_file = base_path / "schedules_filtered.json"
    create_filtered_schedules(schedules_data, include_sw=False, output_file=filtered_file)
    
    print(f"\nFiltered schedules created: {filtered_file}")
    print("Review this file before proceeding with import.")

if __name__ == "__main__":
    main()
