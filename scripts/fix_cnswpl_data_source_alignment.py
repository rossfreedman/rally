#!/usr/bin/env python3
"""
Fix CNSWPL Data Source Alignment
================================

Fix CNSWPL schedule data source to align with teams table naming conventions.
This script updates the schedules.json file to use consistent team naming.

The issue is that schedule data has:
- "Hinsdale PC 1b - Series 1" (with "b" suffix)
- "North Shore I - Series I" (letter series)

While teams table has:
- "Hinsdale PC 1a" (with "a" suffix)
- "North Shore 1" (numeric series)

This script will:
1. Convert "b" suffixes to "a" suffixes to match teams table
2. Convert letter series to numeric series where possible
3. Create a mapping for letter series that can't be converted
"""

import sys
import os
import json
import re
from datetime import datetime

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

def load_json_file(filename):
    """Load JSON file from data/leagues/all/"""
    file_path = os.path.join(project_root, "data", "leagues", "all", filename)
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json_file(filename, data):
    """Save JSON file to data/leagues/all/ with backup"""
    file_path = os.path.join(project_root, "data", "leagues", "all", filename)
    
    # Create backup
    backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if os.path.exists(file_path):
        import shutil
        shutil.copy2(file_path, backup_path)
        print(f"📦 Created backup: {backup_path}")
    
    # Save updated file
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Saved updated file: {file_path}")

def normalize_team_name(team_name):
    """Normalize team name to match teams table format"""
    if not team_name or team_name == "BYE":
        return team_name
    
    # Remove " - Series X" suffix first
    if " - Series " in team_name:
        base_name = team_name.split(" - Series ")[0]
        series_part = team_name.split(" - Series ")[1]
    else:
        base_name = team_name
        series_part = None
    
    # Handle "b" suffix conversion to "a"
    if base_name.endswith("b"):
        base_name = base_name[:-1] + "a"
    
    # Handle letter series conversion to numeric
    if series_part and series_part.isalpha():
        # Map letter series to numeric (this is a best guess)
        letter_to_number = {
            'A': '1', 'B': '2', 'C': '3', 'D': '4', 'E': '5', 'F': '6',
            'G': '7', 'H': '8', 'I': '9', 'J': '10', 'K': '11', 'SN': '12'
        }
        if series_part in letter_to_number:
            # Update the base name to include the numeric series
            # Remove any existing number and add the mapped number
            base_name = re.sub(r'\s+\d+[a-z]?$', '', base_name).strip()
            base_name = f"{base_name} {letter_to_number[series_part]}"
            series_part = None  # No longer need the " - Series X" part
    
    # Reconstruct the team name
    if series_part:
        return f"{base_name} - Series {series_part}"
    else:
        return base_name

def main():
    print("🔧 Fixing CNSWPL Data Source Alignment")
    print("=" * 50)
    
    # Load current schedule data
    print("📂 Loading current schedule data...")
    try:
        schedules_data = load_json_file("schedules.json")
        print(f"✅ Loaded {len(schedules_data):,} schedule records")
    except Exception as e:
        print(f"❌ Error loading schedules.json: {e}")
        return
    
    # Filter CNSWPL records
    cnswpl_records = [record for record in schedules_data if record.get("League") == "CNSWPL"]
    print(f"📊 Found {len(cnswpl_records):,} CNSWPL records")
    
    if len(cnswpl_records) == 0:
        print("⚠️ No CNSWPL records found in schedule data")
        return
    
    # Analyze current naming patterns
    print("\n🔍 Analyzing current naming patterns...")
    team_patterns = {}
    for record in cnswpl_records[:100]:  # Sample first 100
        home_team = record.get("home_team", "")
        away_team = record.get("away_team", "")
        
        for team in [home_team, away_team]:
            if team and team != "BYE":
                if " - Series " in team:
                    base = team.split(" - Series ")[0]
                    series = team.split(" - Series ")[1]
                    pattern = f"{base} - Series {series}"
                    team_patterns[pattern] = team_patterns.get(pattern, 0) + 1
    
    print("Current team patterns (sample):")
    for pattern, count in sorted(team_patterns.items())[:10]:
        print(f"  {pattern} ({count} occurrences)")
    
    # Fix team names
    print(f"\n🔧 Fixing team names...")
    fixed_count = 0
    unchanged_count = 0
    
    for record in schedules_data:
        if record.get("League") == "CNSWPL":
            original_home = record.get("home_team", "")
            original_away = record.get("away_team", "")
            
            # Fix home team
            if original_home and original_home != "BYE":
                new_home = normalize_team_name(original_home)
                if new_home != original_home:
                    record["home_team"] = new_home
                    fixed_count += 1
                    print(f"  ✅ Fixed: {original_home} → {new_home}")
                else:
                    unchanged_count += 1
            
            # Fix away team
            if original_away and original_away != "BYE":
                new_away = normalize_team_name(original_away)
                if new_away != original_away:
                    record["away_team"] = new_away
                    fixed_count += 1
                    print(f"  ✅ Fixed: {original_away} → {new_away}")
                else:
                    unchanged_count += 1
    
    print(f"\n📊 Summary:")
    print(f"  Fixed team names: {fixed_count}")
    print(f"  Unchanged team names: {unchanged_count}")
    
    if fixed_count > 0:
        # Save updated data
        print(f"\n💾 Saving updated schedule data...")
        save_json_file("schedules.json", schedules_data)
        
        print(f"\n🎉 CNSWPL data source alignment complete!")
        print(f"   Next ETL import should have much better team mapping success.")
        print(f"   Run: python scripts/fix_cnswpl_schedule_team_mappings_comprehensive.py")
        print(f"   to verify the improvements after the next ETL import.")
    else:
        print(f"\n⚠️ No team names needed fixing.")
        print(f"   The data source alignment issue may be more complex than expected.")

if __name__ == "__main__":
    main() 