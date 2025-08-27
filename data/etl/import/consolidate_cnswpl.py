#!/usr/bin/env python3
"""
Consolidate CNSWPL Series Data Script

Consolidates all series_*.json files from data/leagues/CNSWPL/temp/ into a single
comprehensive players.json file, removing duplicates and maintaining data integrity.

Usage: python3 data/etl/import/consolidate_cnswpl.py
"""

import json
import os
import glob
from collections import defaultdict

def load_json_file(file_path):
    """Load and parse a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {file_path}: {e}")
        return []
    except Exception as e:
        print(f"ERROR: Failed to load {file_path}: {e}")
        return []

def extract_team_info(record):
    """Extract team information from a player record."""
    club = record.get("Club", "").strip()
    series = record.get("Series", "").strip()
    series_mapping = record.get("Series Mapping ID", "").strip()
    
    # Use Series Mapping ID as team name if available, otherwise construct from Club + Series
    if series_mapping:
        team_name = series_mapping
    else:
        # Extract series number from series name (e.g., "Series 1" -> "1")
        series_num = series.replace("Series ", "").strip()
        team_name = f"{club} {series_num}"
    
    return {
        "Club": club,
        "Series": series,
        "Team": team_name
    }

def consolidate_cnswpl_data():
    """Consolidate all CNSWPL series files into a single players.json."""
    
    # Paths
    temp_dir = "data/leagues/CNSWPL/temp"
    output_file = "data/leagues/CNSWPL/players.json"
    
    # Find all series files
    series_files = glob.glob(os.path.join(temp_dir, "series_*.json"))
    series_files.sort()  # Sort for consistent processing order
    
    print(f"Found {len(series_files)} series files to consolidate")
    
    # Track unique players and teams
    unique_players = {}  # key: (first_name, last_name, club, series), value: record
    unique_teams = set()  # set of (club, series, team) tuples
    total_records = 0
    duplicate_records = 0
    
    # Process each series file
    for series_file in series_files:
        series_name = os.path.basename(series_file).replace('.json', '')
        print(f"Processing {series_name}...")
        
        records = load_json_file(series_file)
        if not records:
            continue
        
        print(f"  Loaded {len(records)} records from {series_name}")
        
        for record in records:
            total_records += 1
            
            # Extract basic player info
            first_name = record.get("First Name", "").strip()
            last_name = record.get("Last Name", "").strip()
            player_id = record.get("Player ID", "").strip()
            
            # Skip records without essential player info
            if not first_name or not last_name:
                duplicate_records += 1
                continue
            
            # Extract team info
            team_info = extract_team_info(record)
            club = team_info["Club"]
            series = team_info["Series"]
            team = team_info["Team"]
            
            # Create unique key for player (allowing same name in different teams/series)
            player_key = (first_name, last_name, club, series)
            
            # Check if this is a duplicate player in the same team/series
            if player_key in unique_players:
                # If duplicate, prefer the record with more complete information
                existing_record = unique_players[player_key]
                existing_completeness = sum(1 for v in existing_record.values() if v)
                current_completeness = sum(1 for v in record.values() if v)
                
                if current_completeness > existing_completeness:
                    unique_players[player_key] = record
                    print(f"    Replaced duplicate player {first_name} {last_name} in {team} with more complete record")
                else:
                    print(f"    Skipped duplicate player {first_name} {last_name} in {team} (existing record more complete)")
                duplicate_records += 1
            else:
                # New unique player
                unique_players[player_key] = record
                unique_teams.add((club, series, team))
    
    # Convert to list format for output
    consolidated_records = list(unique_players.values())
    
    # Sort by club, series, team, last name, first name for consistent output
    consolidated_records.sort(key=lambda x: (
        x.get("Club", ""),
        x.get("Series", ""),
        x.get("Series Mapping ID", ""),
        x.get("Last Name", ""),
        x.get("First Name", "")
    ))
    
    # Create backup of existing players.json
    if os.path.exists(output_file):
        backup_file = f"{output_file}.backup_$(date +%Y%m%d_%H%M%S)"
        print(f"Creating backup of existing players.json: {backup_file}")
        os.system(f"cp '{output_file}' '{backup_file}'")
    
    # Write consolidated data
    try:
        with open(output_file, 'w') as f:
            json.dump(consolidated_records, f, indent=2)
        
        print(f"\n✅ Consolidation completed successfully!")
        print(f"📊 Summary:")
        print(f"   Total records processed: {total_records}")
        print(f"   Unique players: {len(consolidated_records)}")
        print(f"   Duplicate records removed: {duplicate_records}")
        print(f"   Unique teams: {len(unique_teams)}")
        print(f"   Output file: {output_file}")
        
        # Show sample of unique teams
        print(f"\n🏆 Sample of unique teams:")
        sorted_teams = sorted(list(unique_teams), key=lambda x: (x[0], x[1], x[2]))[:20]
        for club, series, team in sorted_teams:
            print(f"   {club} | {series} | {team}")
        
        if len(unique_teams) > 20:
            print(f"   ... and {len(unique_teams) - 20} more teams")
        
    except Exception as e:
        print(f"ERROR: Failed to write consolidated file: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔄 CNSWPL Data Consolidation Script")
    print("=" * 50)
    
    success = consolidate_cnswpl_data()
    
    if success:
        print(f"\n🎯 Next steps:")
        print(f"   1. Review the consolidated players.json file")
        print(f"   2. Run: python3 data/etl/import/start_season.py CNSWPL")
        print(f"   3. Verify all data was imported correctly")
    else:
        print(f"\n❌ Consolidation failed. Please check the errors above.")
        exit(1)
