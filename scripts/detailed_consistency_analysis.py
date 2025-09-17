#!/usr/bin/env python3
"""
Detailed analysis of data consistency issues between players.json and schedules.json
"""

import json
import re
from collections import defaultdict, Counter
from pathlib import Path

def load_json_file(file_path):
    """Load and return JSON data from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def extract_club_from_team_name(team_name):
    """Extract club name from team name."""
    # Remove series number at the end
    parts = team_name.split()
    if len(parts) > 1 and parts[-1].isdigit():
        return ' '.join(parts[:-1])
    return team_name

def normalize_club_name(name):
    """Normalize club name for comparison."""
    # Remove common suffixes and normalize
    name = name.replace(' CC', '').replace(' PD', '').replace(' GC', '').replace(' S&F', '')
    name = re.sub(r'\s+', ' ', name.strip())  # Normalize whitespace
    return name.lower()

def analyze_naming_patterns(players_data, schedules_data):
    """Analyze naming patterns to understand the differences."""
    print("=== DETAILED NAMING PATTERN ANALYSIS ===\n")
    
    # Extract clubs from players data
    players_clubs = set()
    players_teams = set()
    for player in players_data:
        if player.get("Club"):
            players_clubs.add(player["Club"])
        if player.get("Team"):
            players_teams.add(player["Team"])
    
    # Extract teams from schedules data
    schedules_teams = set()
    for schedule in schedules_data:
        if schedule.get("home_team"):
            schedules_teams.add(schedule["home_team"])
        if schedule.get("away_team"):
            schedules_teams.add(schedule["away_team"])
    
    # Extract clubs from schedule team names
    schedules_clubs = set()
    for team in schedules_teams:
        club = extract_club_from_team_name(team)
        schedules_clubs.add(club)
    
    print("1. CLUB NAMING PATTERNS:")
    print("=" * 40)
    
    # Analyze club naming patterns
    players_club_patterns = defaultdict(list)
    schedules_club_patterns = defaultdict(list)
    
    for club in players_clubs:
        normalized = normalize_club_name(club)
        players_club_patterns[normalized].append(club)
    
    for club in schedules_clubs:
        normalized = normalize_club_name(club)
        schedules_club_patterns[normalized].append(club)
    
    print("Players.json club patterns (showing first 10):")
    for i, (normalized, clubs) in enumerate(list(players_club_patterns.items())[:10]):
        print(f"  {normalized}: {clubs}")
    
    print("\nSchedules.json club patterns (showing first 10):")
    for i, (normalized, clubs) in enumerate(list(schedules_club_patterns.items())[:10]):
        print(f"  {normalized}: {clubs}")
    
    # Find common normalized clubs
    common_normalized = set(players_club_patterns.keys()) & set(schedules_club_patterns.keys())
    print(f"\nCommon normalized club names: {len(common_normalized)}")
    
    # Find clubs that exist in both but with different exact names
    naming_variations = []
    for normalized in common_normalized:
        players_variants = players_club_patterns[normalized]
        schedules_variants = schedules_club_patterns[normalized]
        
        if set(players_variants) != set(schedules_variants):
            naming_variations.append({
                'normalized': normalized,
                'players': players_variants,
                'schedules': schedules_variants
            })
    
    print(f"\nClubs with naming variations: {len(naming_variations)}")
    for i, variation in enumerate(naming_variations[:5]):  # Show first 5
        print(f"  {variation['normalized']}:")
        print(f"    Players: {variation['players']}")
        print(f"    Schedules: {variation['schedules']}")
    
    print("\n2. SERIES NAMING ANALYSIS:")
    print("=" * 40)
    
    # Analyze series naming
    players_series = set()
    for player in players_data:
        if player.get("Series"):
            players_series.add(player["Series"])
    
    schedules_series = set()
    for schedule in schedules_data:
        if schedule.get("series"):
            schedules_series.add(schedule["series"])
    
    print(f"Players.json series: {sorted(players_series)}")
    print(f"Schedules.json series: {sorted(schedules_series)}")
    
    # Check for SW series pattern
    sw_series = [s for s in schedules_series if 'SW' in s]
    regular_series = [s for s in schedules_series if 'SW' not in s]
    
    print(f"\nSW series in schedules: {len(sw_series)}")
    print(f"Regular series in schedules: {len(regular_series)}")
    print(f"SW series: {sorted(sw_series)}")
    
    print("\n3. TEAM NAMING ANALYSIS:")
    print("=" * 40)
    
    # Analyze team naming patterns
    players_team_patterns = defaultdict(list)
    schedules_team_patterns = defaultdict(list)
    
    for team in players_teams:
        club = extract_club_from_team_name(team)
        normalized_club = normalize_club_name(club)
        players_team_patterns[normalized_club].append(team)
    
    for team in schedules_teams:
        club = extract_club_from_team_name(team)
        normalized_club = normalize_club_name(club)
        schedules_team_patterns[normalized_club].append(team)
    
    # Find teams that exist in both files
    common_teams = players_teams & schedules_teams
    print(f"Teams in both files: {len(common_teams)}")
    
    # Find teams only in players
    players_only = players_teams - schedules_teams
    print(f"Teams only in players.json: {len(players_only)}")
    
    # Find teams only in schedules
    schedules_only = schedules_teams - players_teams
    print(f"Teams only in schedules.json: {len(schedules_only)}")
    
    # Analyze SW teams
    sw_teams = [t for t in schedules_teams if 'SW' in t]
    print(f"SW teams in schedules: {len(sw_teams)}")
    
    print("\n4. SPECIFIC ISSUES IDENTIFIED:")
    print("=" * 40)
    
    # Issue 1: SW series/teams
    print("ISSUE 1: SW (Summer/Winter) series and teams")
    print("- Schedules.json contains SW series (Series 15 SW, Series 17 SW, etc.)")
    print("- Players.json does not contain SW series")
    print("- This suggests schedules.json includes summer/winter league data")
    print("- Players.json only contains regular season data")
    
    # Issue 2: Club name variations
    print("\nISSUE 2: Club name variations")
    print("- Players.json uses full club names with series numbers (e.g., 'Evanston 20')")
    print("- Schedules.json uses base club names (e.g., 'Evanston')")
    print("- This is actually correct - schedules show base club names, players show specific teams")
    
    # Issue 3: Missing teams in schedules
    print("\nISSUE 3: Teams missing from schedules")
    print("- Many teams from players.json don't appear in schedules.json")
    print("- This could indicate:")
    print("  a) Teams that don't have scheduled matches yet")
    print("  b) Teams from different seasons/series not covered in current schedule")
    print("  c) Data completeness issues")
    
    return {
        'naming_variations': naming_variations,
        'sw_series': sw_series,
        'sw_teams': sw_teams,
        'common_teams': common_teams,
        'players_only_teams': players_only,
        'schedules_only_teams': schedules_only
    }

def generate_recommendations(analysis_results):
    """Generate recommendations for fixing data consistency issues."""
    print("\n5. RECOMMENDATIONS:")
    print("=" * 40)
    
    print("RECOMMENDATION 1: Verify SW Series Data")
    print("- The schedules.json contains SW (Summer/Winter) series data")
    print("- Players.json does not contain corresponding SW series data")
    print("- ACTION: Verify if SW series data should be included in players.json")
    print("- If yes, scrape SW series player data")
    print("- If no, filter out SW series from schedules.json before import")
    
    print("\nRECOMMENDATION 2: Club Name Normalization")
    print("- The club name variations are mostly due to different naming conventions")
    print("- Players.json: 'Evanston 20' (club + series)")
    print("- Schedules.json: 'Evanston' (base club name)")
    print("- ACTION: This is actually correct - no changes needed")
    print("- The import process should handle this mapping correctly")
    
    print("\nRECOMMENDATION 3: Missing Teams Analysis")
    print("- Many teams from players.json don't appear in schedules.json")
    print("- ACTION: Investigate specific missing teams:")
    
    # Show some examples of missing teams
    missing_teams = list(analysis_results['players_only_teams'])[:10]
    print(f"  Examples: {missing_teams}")
    print("- Check if these teams have matches scheduled")
    print("- Verify if they're from different seasons/series")
    
    print("\nRECOMMENDATION 4: Data Validation")
    print("- Before importing schedules, validate that:")
    print("  a) All teams in schedules.json have corresponding player records")
    print("  b) All series in schedules.json are valid")
    print("  c) Club names can be properly mapped between files")
    
    print("\nRECOMMENDATION 5: Import Strategy")
    print("- Consider importing schedules in phases:")
    print("  Phase 1: Regular series only (exclude SW series)")
    print("  Phase 2: SW series (if player data is available)")
    print("- This allows for proper validation and testing")

def main():
    """Main function to run the detailed analysis."""
    base_path = Path("/Users/rossfreedman/dev/rally/data/leagues/APTA_CHICAGO")
    players_file = base_path / "players.json"
    schedules_file = base_path / "schedules.json"
    
    print("APTA_CHICAGO Detailed Data Consistency Analysis")
    print("=" * 60)
    
    # Load data
    print("Loading data files...")
    players_data = load_json_file(players_file)
    if not players_data:
        return
    
    schedules_data = load_json_file(schedules_file)
    if not schedules_data:
        return
    
    # Run analysis
    analysis_results = analyze_naming_patterns(players_data, schedules_data)
    
    # Generate recommendations
    generate_recommendations(analysis_results)
    
    print("\n" + "=" * 60)
    print("Analysis complete. Review recommendations above.")

if __name__ == "__main__":
    main()
