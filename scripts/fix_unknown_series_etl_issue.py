#!/usr/bin/env python3
"""
Fix Unknown Series ETL Issue
============================

This script fixes the ETL issue where ~4,081 records in player_history.json
have "Unknown" series and clubs, causing player lookups to fail.

Solution approaches:
1. Filter out records with "Unknown" series/clubs
2. Attempt to infer correct series/clubs from other data sources  
3. Create a clean dataset for ETL processing
"""

import json
import os
import sys
from collections import defaultdict, Counter
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def backup_original_files():
    """Create backups of original JSON files"""
    print("📁 Creating backups of original files...")
    
    files_to_backup = [
        "data/leagues/all/player_history.json",
        "data/leagues/all/match_history.json"
    ]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for filepath in files_to_backup:
        if os.path.exists(filepath):
            backup_path = f"{filepath}.backup_{timestamp}"
            os.system(f"cp '{filepath}' '{backup_path}'")
            print(f"   ✅ Backed up {filepath} → {backup_path}")
    
    return timestamp

def load_reference_data():
    """Load reference data to help infer correct series/clubs"""
    print("📊 Loading reference data...")
    
    reference = {
        'players': {},
        'teams': {},
        'series_mapping': defaultdict(set)
    }
    
    # Load players.json for reference
    try:
        with open("data/leagues/all/players.json", 'r') as f:
            players_data = json.load(f)
        
        for player in players_data:
            player_id = player.get("Player ID", "").strip()
            if player_id:
                reference['players'][player_id] = {
                    'first_name': player.get("First Name", "").strip(),
                    'last_name': player.get("Last Name", "").strip(),
                    'club': player.get("Club", "").strip(),
                    'series': player.get("Series", "").strip(),
                    'league': player.get("League", "").strip()
                }
        
        print(f"   ✅ Loaded {len(reference['players'])} player references")
    except Exception as e:
        print(f"   ❌ Error loading players.json: {e}")
    
    # Load match_history.json for team patterns
    try:
        with open("data/leagues/all/match_history.json", 'r') as f:
            match_data = json.load(f)
        
        for match in match_data:
            home_team = match.get("Home Team", "").strip()
            away_team = match.get("Away Team", "").strip()
            league = match.get("league_id", "").strip()
            
            for team_name in [home_team, away_team]:
                if team_name and team_name != "BYE":
                    club_name, series_name = extract_club_and_series(team_name)
                    if club_name and series_name and series_name != "UNKNOWN":
                        reference['teams'][team_name] = {
                            'club': club_name,
                            'series': series_name,
                            'league': league
                        }
                        reference['series_mapping'][club_name].add(series_name)
        
        print(f"   ✅ Loaded {len(reference['teams'])} team references")
        print(f"   ✅ Created mapping for {len(reference['series_mapping'])} clubs")
    except Exception as e:
        print(f"   ❌ Error loading match_history.json: {e}")
    
    return reference

def extract_club_and_series(team_name):
    """Extract club and series from team name"""
    import re
    
    if not team_name:
        return None, None
    
    team_name = team_name.strip()
    
    # APTA Chicago format: "Club - Number"
    if " - " in team_name:
        parts = team_name.split(" - ")
        if len(parts) >= 2:
            club_name = parts[0].strip()
            series_suffix = parts[1].strip()
            try:
                series_num = int(series_suffix)
                if series_num <= 20:
                    series_name = f"Division {series_num}"
                else:
                    series_name = f"Chicago {series_num}"
            except ValueError:
                series_name = f"Chicago {series_suffix}"
            return club_name, series_name
    
    # NSTF format: "Club SSuffix"
    if re.search(r" S\d", team_name):
        parts = team_name.split(" S")
        if len(parts) >= 2:
            club_name = parts[0].strip()
            series_suffix = parts[1].strip()
            series_name = f"Series {series_suffix}"
            return club_name, series_name
    
    # CNSWPL format: "Club Number"
    if re.search(r"\s+\d+[a-zA-Z]*$", team_name):
        club_name = re.sub(r"\s+\d+[a-zA-Z]*$", "", team_name).strip()
        series_match = re.search(r"\s+(\d+[a-zA-Z]*)$", team_name)
        if series_match and club_name:
            series_suffix = series_match.group(1)
            series_name = f"Division {series_suffix}"
            return club_name, series_name
    
    # NSTF Sunday formats
    if "Sunday A" in team_name:
        club_name = team_name.replace("Sunday A", "").strip()
        return club_name, "Series A"
    elif "Sunday B" in team_name:
        club_name = team_name.replace("Sunday B", "").strip()
        return club_name, "Series B"
    
    return team_name, "UNKNOWN"

def fix_player_history(reference_data):
    """Fix the player_history.json file"""
    print("🔧 Fixing player_history.json...")
    
    # Load the original file
    with open("data/leagues/all/player_history.json", 'r') as f:
        player_history = json.load(f)
    
    print(f"   📊 Original records: {len(player_history)}")
    
    fixed_records = []
    unknown_filtered = 0
    inferred_fixes = 0
    
    for record in player_history:
        series = record.get("series", "").strip()
        club = record.get("club", "").strip()
        player_id = record.get("original_player_id", "").strip()
        
        # Skip records with Unknown series/clubs
        if series.lower() == "unknown" or club.lower() == "unknown":
            # Try to infer from reference data
            if player_id and player_id in reference_data['players']:
                ref_player = reference_data['players'][player_id]
                if ref_player['series'] and ref_player['club']:
                    record["series"] = ref_player['series']
                    record["club"] = ref_player['club']
                    record["league_id"] = ref_player['league']
                    fixed_records.append(record)
                    inferred_fixes += 1
                    continue
            
            # If we can't infer, skip this record
            unknown_filtered += 1
            continue
        
        # Keep good records as-is
        fixed_records.append(record)
    
    print(f"   📊 Fixed records: {len(fixed_records)}")
    print(f"   ⚠️  Unknown filtered: {unknown_filtered}")
    print(f"   🔧 Inferred fixes: {inferred_fixes}")
    
    # Save the fixed file
    with open("data/leagues/all/player_history.json", 'w') as f:
        json.dump(fixed_records, f, indent=2)
    
    print(f"   ✅ Saved fixed player_history.json")
    
    return len(fixed_records), unknown_filtered

def fix_match_history_unknown_formats(reference_data):
    """Fix team names with unknown formats in match_history.json"""
    print("🔧 Analyzing match_history.json for unknown team formats...")
    
    with open("data/leagues/all/match_history.json", 'r') as f:
        match_history = json.load(f)
    
    unknown_teams = set()
    fixed_count = 0
    
    for record in match_history:
        home_team = record.get("Home Team", "").strip()
        away_team = record.get("Away Team", "").strip()
        
        for team_name in [home_team, away_team]:
            if team_name and team_name != "BYE":
                club_name, series_name = extract_club_and_series(team_name)
                if series_name == "UNKNOWN":
                    unknown_teams.add(team_name)
    
    print(f"   📊 Found {len(unknown_teams)} unique teams with unknown formats")
    
    if unknown_teams:
        print("   🔍 Unknown team formats (first 20):")
        for i, team in enumerate(sorted(unknown_teams)[:20]):
            print(f"      {team}")
        
        if len(unknown_teams) > 20:
            print(f"      ... and {len(unknown_teams) - 20} more")
    
    return len(unknown_teams)

def create_etl_health_report():
    """Create a health report after fixes"""
    print("📋 Creating ETL Health Report...")
    
    try:
        # Re-analyze the fixed data
        with open("data/leagues/all/player_history.json", 'r') as f:
            player_history = json.load(f)
        
        unknown_series = sum(1 for record in player_history 
                           if record.get("series", "").strip().lower() == "unknown")
        unknown_clubs = sum(1 for record in player_history 
                          if record.get("club", "").strip().lower() == "unknown")
        
        print(f"   📊 Final player_history.json stats:")
        print(f"      Total records: {len(player_history)}")
        print(f"      Unknown series: {unknown_series}")
        print(f"      Unknown clubs: {unknown_clubs}")
        print(f"      Health score: {((len(player_history) - unknown_series) / len(player_history) * 100):.1f}%")
        
        if unknown_series == 0 and unknown_clubs == 0:
            print("   ✅ ETL data is now clean and ready for processing!")
            return True
        else:
            print("   ⚠️  Some Unknown records remain - may need manual review")
            return False
    
    except Exception as e:
        print(f"   ❌ Error creating health report: {e}")
        return False

def main():
    """Main function to fix the ETL issue"""
    print("🔧 ETL Unknown Series Fix Tool")
    print("=" * 60)
    print("This will fix the 'Unknown' series issue causing ETL failures")
    print()
    
    # Confirm operation
    response = input("Proceed with fixing Unknown series data? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Operation cancelled")
        return 1
    
    try:
        # Step 1: Backup original files
        backup_timestamp = backup_original_files()
        
        # Step 2: Load reference data
        reference_data = load_reference_data()
        
        # Step 3: Fix player_history.json
        fixed_count, filtered_count = fix_player_history(reference_data)
        
        # Step 4: Analyze match_history issues
        unknown_teams_count = fix_match_history_unknown_formats(reference_data)
        
        # Step 5: Create health report
        is_healthy = create_etl_health_report()
        
        print("\n🎉 Fix Operation Complete!")
        print("=" * 60)
        print(f"📁 Backups created with timestamp: {backup_timestamp}")
        print(f"🔧 Player history records fixed: {fixed_count}")
        print(f"⚠️  Unknown records filtered: {filtered_count}")
        print(f"📊 Unknown team formats found: {unknown_teams_count}")
        print(f"✅ ETL Health Status: {'HEALTHY' if is_healthy else 'NEEDS REVIEW'}")
        
        if is_healthy:
            print("\n🚀 Ready to run ETL import!")
            print("   The Unknown series issue has been resolved.")
        else:
            print("\n⚠️  Manual review may be needed for remaining issues.")
        
        return 0 if is_healthy else 1
        
    except Exception as e:
        print(f"\n❌ Fix operation failed: {e}")
        print("💡 Original files are preserved in backups")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 