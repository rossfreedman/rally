#!/usr/bin/env python3
"""
ETL Issue Diagnostic Script
==========================

This script diagnoses why the ETL works on staging but fails on production
by examining the data being processed and identifying the root cause.
"""

import json
import os
import sys
import re
from collections import defaultdict, Counter

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.league_utils import normalize_league_id

def analyze_json_data():
    """Analyze the JSON data for issues"""
    print("🔍 Analyzing JSON Data for ETL Issues")
    print("=" * 60)
    
    # Load the main data files
    data_dir = "data/leagues/all"
    
    files_to_check = [
        "match_history.json",
        "players.json", 
        "series_stats.json",
        "schedules.json",
        "player_history.json"
    ]
    
    for filename in files_to_check:
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            print(f"\n📄 Analyzing {filename}...")
            analyze_file(filepath, filename)
        else:
            print(f"❌ {filename} not found!")

def analyze_file(filepath, filename):
    """Analyze a specific JSON file"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        print(f"   📊 Loaded {len(data)} records")
        
        if filename == "match_history.json":
            analyze_match_history(data)
        elif filename == "players.json":
            analyze_players(data)
        elif filename == "player_history.json":
            analyze_player_history(data)
        elif filename == "series_stats.json":
            analyze_series_stats(data)
        elif filename == "schedules.json":
            analyze_schedules(data)
            
    except Exception as e:
        print(f"   ❌ Error analyzing {filename}: {e}")

def analyze_match_history(data):
    """Analyze match history data"""
    print("   🔍 Match History Analysis:")
    
    # Check for team name patterns
    team_patterns = defaultdict(int)
    leagues = Counter()
    
    for record in data:
        home_team = record.get("Home Team", "").strip()
        away_team = record.get("Away Team", "").strip()
        league = record.get("league_id", "").strip()
        
        if home_team:
            team_patterns[extract_team_pattern(home_team)] += 1
        if away_team:
            team_patterns[extract_team_pattern(away_team)] += 1
        if league:
            leagues[league] += 1
    
    print(f"   📊 Team patterns found: {len(team_patterns)}")
    for pattern, count in sorted(team_patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"      {pattern}: {count}")
    
    print(f"   📊 Leagues: {dict(leagues)}")

def analyze_players(data):
    """Analyze players data"""
    print("   🔍 Players Analysis:")
    
    series_counter = Counter()
    club_counter = Counter()
    leagues = Counter()
    unknown_series = 0
    unknown_clubs = 0
    
    for record in data:
        series = record.get("Series", "").strip()
        club = record.get("Club", "").strip()
        league = record.get("League", "").strip()
        
        if series:
            series_counter[series] += 1
            if series.lower() == "unknown":
                unknown_series += 1
        
        if club:
            club_counter[club] += 1
            if club.lower() == "unknown":
                unknown_clubs += 1
        
        if league:
            leagues[league] += 1
    
    print(f"   📊 Series found: {len(series_counter)}")
    print(f"   ⚠️  Unknown series: {unknown_series}")
    
    print(f"   📊 Clubs found: {len(club_counter)}")
    print(f"   ⚠️  Unknown clubs: {unknown_clubs}")
    
    print(f"   📊 Leagues: {dict(leagues)}")
    
    # Show top series
    print("   📊 Top Series:")
    for series, count in series_counter.most_common(10):
        print(f"      {series}: {count}")

def analyze_player_history(data):
    """Analyze player history data"""
    print("   🔍 Player History Analysis:")
    
    series_counter = Counter()
    club_counter = Counter()
    leagues = Counter()
    unknown_series = 0
    unknown_clubs = 0
    
    for record in data:
        series = record.get("series", "").strip()
        club = record.get("club", "").strip()
        league = record.get("league_id", "").strip()
        
        if series:
            series_counter[series] += 1
            if series.lower() == "unknown":
                unknown_series += 1
        
        if club:
            club_counter[club] += 1
            if club.lower() == "unknown":
                unknown_clubs += 1
        
        if league:
            leagues[league] += 1
    
    print(f"   📊 Series found: {len(series_counter)}")
    print(f"   ⚠️  Unknown series: {unknown_series}")
    
    print(f"   📊 Clubs found: {len(club_counter)}")
    print(f"   ⚠️  Unknown clubs: {unknown_clubs}")
    
    print(f"   📊 Leagues: {dict(leagues)}")

def analyze_series_stats(data):
    """Analyze series stats data"""
    print("   🔍 Series Stats Analysis:")
    
    series_counter = Counter()
    leagues = Counter()
    
    for record in data:
        series = record.get("series", "").strip()
        league = record.get("league_id", "").strip()
        
        if series:
            series_counter[series] += 1
        if league:
            leagues[league] += 1
    
    print(f"   📊 Series found: {len(series_counter)}")
    print(f"   📊 Leagues: {dict(leagues)}")

def analyze_schedules(data):
    """Analyze schedules data"""
    print("   🔍 Schedules Analysis:")
    
    team_patterns = defaultdict(int)
    leagues = Counter()
    
    for record in data:
        home_team = record.get("home_team", "").strip()
        away_team = record.get("away_team", "").strip()
        league = record.get("League", "").strip()
        
        if home_team:
            team_patterns[extract_team_pattern(home_team)] += 1
        if away_team:
            team_patterns[extract_team_pattern(away_team)] += 1
        if league:
            leagues[league] += 1
    
    print(f"   📊 Team patterns found: {len(team_patterns)}")
    for pattern, count in sorted(team_patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"      {pattern}: {count}")
    
    print(f"   📊 Leagues: {dict(leagues)}")

def extract_team_pattern(team_name):
    """Extract team name pattern for analysis"""
    if not team_name:
        return "EMPTY"
    
    # APTA Chicago format: "Club - Number"
    if " - " in team_name:
        return "APTA_FORMAT"
    
    # NSTF format: "Club SNumber"
    if re.search(r" S\d", team_name):
        return "NSTF_FORMAT"
    
    # CNSWPL format: "Club Number"
    if re.search(r"\s+\d+[a-zA-Z]*$", team_name):
        return "CNSWPL_FORMAT"
    
    return "UNKNOWN_FORMAT"

def diagnose_series_extraction():
    """Diagnose series extraction issues"""
    print("\n🔧 Diagnosing Series Extraction Logic")
    print("=" * 60)
    
    # Test the series extraction logic with sample team names
    test_cases = [
        ("Tennaqua - 22", "APTA_CHICAGO"),
        ("Tennaqua S2B", "NSTF"),
        ("Tennaqua 1", "CNSWPL"),
        ("Hinsdale PC 1a", "CNSWPL"),
        ("Wilmette Sunday A", "NSTF"),
        ("BYE", "APTA_CHICAGO"),
        ("", "APTA_CHICAGO"),
        ("InvalidFormat", "APTA_CHICAGO"),
    ]
    
    print("Testing series extraction on sample team names:")
    for team_name, league_id in test_cases:
        extracted_series = extract_series_from_team_name(team_name, league_id)
        print(f"   {team_name:<20} ({league_id:<12}) → {extracted_series}")

def extract_series_from_team_name(team_name, league_id):
    """Test version of series extraction logic"""
    if not team_name:
        return "EMPTY_TEAM_NAME"
    
    team_name = team_name.strip()
    
    # Handle APTA_CHICAGO format: "Club - Suffix"
    if " - " in team_name:
        parts = team_name.split(" - ")
        if len(parts) >= 2:
            series_suffix = parts[1].strip()
            try:
                series_num = int(series_suffix)
                if series_num <= 20:
                    return f"Division {series_num}"
                else:
                    return f"Chicago {series_num}"
            except ValueError:
                return f"Chicago {series_suffix}"
    
    # Handle NSTF format: "Club SSuffix"
    if re.search(r" S\d", team_name):
        parts = team_name.split(" S")
        if len(parts) >= 2:
            series_suffix = parts[1].strip()
            return f"Series {series_suffix}"
    
    # Handle CNSWPL format: "Club Number"
    if re.search(r"\s+\d+[a-zA-Z]*$", team_name):
        series_match = re.search(r"\s+(\d+[a-zA-Z]*)$", team_name)
        if series_match:
            series_suffix = series_match.group(1)
            return f"Division {series_suffix}"
    
    # Handle NSTF Sunday formats
    if "Sunday A" in team_name:
        return "Series A"
    elif "Sunday B" in team_name:
        return "Series B"
    
    # Handle BYE
    if team_name == "BYE":
        return "BYE"
    
    return "UNKNOWN_EXTRACTION_FAILED"

def main():
    """Main diagnostic function"""
    print("🚨 ETL Issue Diagnostic Tool")
    print("=" * 60)
    print("This tool will help identify why ETL works on staging but fails on production")
    print()
    
    # Analyze JSON data
    analyze_json_data()
    
    # Diagnose series extraction
    diagnose_series_extraction()
    
    print("\n🔍 Summary & Recommendations")
    print("=" * 60)
    print("1. Check for 'Unknown' series in JSON data")
    print("2. Verify team name formats match expected patterns")
    print("3. Ensure series extraction logic handles all team name formats")
    print("4. Compare staging vs production data differences")
    print("5. Check if production has different data than staging")

if __name__ == "__main__":
    main() 