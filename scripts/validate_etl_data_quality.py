#!/usr/bin/env python3
"""
ETL Data Quality Validation Script

This script performs comprehensive validation of ETL import data quality
to catch issues early and ensure consistency across all import scripts.

Usage:
    python3 scripts/validate_etl_data_quality.py <LEAGUE_KEY>
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_config import get_db_url
import psycopg2
sys.path.insert(0, os.path.join(project_root, 'data', 'etl', 'import'))
from team_manager import TeamManager, validate_team_consistency, normalize_club_name, parse_team_name

def validate_source_data_consistency(league_key: str) -> Dict[str, Any]:
    """Validate consistency between different source data files."""
    print(f"🔍 Validating source data consistency for {league_key}...")
    
    data_dir = Path(f"data/leagues/{league_key}")
    report = {
        'teams_in_stats': set(),
        'teams_in_schedules': set(),
        'teams_in_players': set(),
        'teams_in_match_scores': set(),
        'missing_teams': [],
        'inconsistent_teams': [],
        'total_issues': 0
    }
    
    # Load teams from stats
    stats_file = data_dir / "series_stats.json"
    if stats_file.exists():
        with open(stats_file, 'r') as f:
            stats_data = json.load(f)
        for entry in stats_data:
            team_name = entry.get('team', '').strip()
            if team_name:
                report['teams_in_stats'].add(team_name)
    
    # Load teams from schedules
    schedules_file = data_dir / "schedules.json"
    if schedules_file.exists():
        with open(schedules_file, 'r') as f:
            schedules_data = json.load(f)
        for record in schedules_data:
            home_team = record.get('home_team', '').strip()
            away_team = record.get('away_team', '').strip()
            if home_team and home_team != 'BYE':
                report['teams_in_schedules'].add(home_team)
            if away_team and away_team != 'BYE':
                report['teams_in_schedules'].add(away_team)
    
    # Load teams from players
    players_file = data_dir / "players.json"
    if players_file.exists():
        with open(players_file, 'r') as f:
            players_data = json.load(f)
        for entry in players_data:
            team_name = entry.get('team', '').strip()
            if team_name:
                report['teams_in_players'].add(team_name)
    
    # Load teams from match scores
    match_scores_file = data_dir / "match_scores.json"
    if match_scores_file.exists():
        with open(match_scores_file, 'r') as f:
            match_scores_data = json.load(f)
        for entry in match_scores_data:
            home_team = entry.get('home_team', '').strip()
            away_team = entry.get('away_team', '').strip()
            if home_team:
                report['teams_in_match_scores'].add(home_team)
            if away_team:
                report['teams_in_match_scores'].add(away_team)
    
    # Find teams that appear in schedules but not in stats
    missing_in_stats = report['teams_in_schedules'] - report['teams_in_stats']
    if missing_in_stats:
        report['missing_teams'].extend([(team, 'stats') for team in missing_in_stats])
        report['total_issues'] += len(missing_in_stats)
    
    # Find teams that appear in stats but not in schedules
    missing_in_schedules = report['teams_in_stats'] - report['teams_in_schedules']
    if missing_in_schedules:
        report['missing_teams'].extend([(team, 'schedules') for team in missing_in_schedules])
        report['total_issues'] += len(missing_in_schedules)
    
    # Check for inconsistent team naming
    all_teams = report['teams_in_stats'] | report['teams_in_schedules'] | report['teams_in_players'] | report['teams_in_match_scores']
    normalized_teams = {}
    
    for team in all_teams:
        raw_club, series, _ = parse_team_name(team)
        if raw_club:
            normalized_club = normalize_club_name(raw_club)
            key = f"{normalized_club}_{series}"
            
            if key not in normalized_teams:
                normalized_teams[key] = []
            normalized_teams[key].append(team)
    
    # Find teams that normalize to the same club/series but have different names
    for key, teams in normalized_teams.items():
        if len(teams) > 1:
            report['inconsistent_teams'].append({
                'normalized_key': key,
                'variants': teams
            })
            report['total_issues'] += len(teams) - 1
    
    return report

def validate_database_consistency(league_key: str) -> Dict[str, Any]:
    """Validate database consistency for teams, clubs, and series."""
    print(f"🔍 Validating database consistency for league {league_key}...")
    
    conn = psycopg2.connect(get_db_url())
    cur = conn.cursor()
    
    # Get integer league ID
    cur.execute("SELECT id FROM leagues WHERE league_id = %s", (league_key,))
    result = cur.fetchone()
    if not result:
        print(f"❌ League {league_key} not found in database")
        return {'total_issues': 1}
    league_id = result[0]
    
    report = {
        'teams_without_clubs': [],
        'teams_without_series': [],
        'duplicate_team_names': [],
        'orphaned_teams': [],
        'club_normalization_issues': [],
        'total_teams': 0,
        'total_issues': 0
    }
    
    try:
        # Get all teams for the league
        cur.execute("""
            SELECT t.id, t.team_name, t.club_id, t.series_id, c.name as club_name, s.name as series_name
            FROM teams t
            LEFT JOIN clubs c ON t.club_id = c.id
            LEFT JOIN series s ON t.series_id = s.id
            WHERE t.league_id = %s
            ORDER BY t.team_name
        """, (league_id,))
        
        teams = cur.fetchall()
        report['total_teams'] = len(teams)
        
        # Check for issues
        for team_id, team_name, club_id, series_id, club_name, series_name in teams:
            if not club_id or not club_name:
                report['teams_without_clubs'].append({
                    'team_id': team_id,
                    'team_name': team_name
                })
                report['total_issues'] += 1
            
            if not series_id or not series_name:
                report['teams_without_series'].append({
                    'team_id': team_id,
                    'team_name': team_name
                })
                report['total_issues'] += 1
        
        # Check for duplicate team names
        cur.execute("""
            SELECT team_name, COUNT(*) as count
            FROM teams
            WHERE league_id = %s
            GROUP BY team_name
            HAVING COUNT(*) > 1
        """, (league_id,))
        
        duplicates = cur.fetchall()
        for team_name, count in duplicates:
            report['duplicate_team_names'].append({
                'team_name': team_name,
                'count': count
            })
            report['total_issues'] += count - 1
        
        # Check for club normalization issues
        cur.execute("""
            SELECT DISTINCT c.name as club_name, COUNT(*) as team_count
            FROM clubs c
            JOIN teams t ON c.id = t.club_id
            WHERE t.league_id = %s
            GROUP BY c.name
            ORDER BY c.name
        """, (league_id,))
        
        clubs = cur.fetchall()
        for club_name, team_count in clubs:
            normalized_name = normalize_club_name(club_name)
            if club_name != normalized_name:
                report['club_normalization_issues'].append({
                    'original_name': club_name,
                    'normalized_name': normalized_name,
                    'team_count': team_count
                })
                report['total_issues'] += 1
        
    finally:
        cur.close()
        conn.close()
    
    return report

def validate_import_consistency(league_key: str) -> Dict[str, Any]:
    """Validate consistency between source data and database."""
    print(f"🔍 Validating import consistency for {league_key}...")
    
    # Get source data teams
    source_report = validate_source_data_consistency(league_key)
    source_teams = source_report['teams_in_stats'] | source_report['teams_in_schedules']
    
    # Get database teams
    conn = psycopg2.connect(get_db_url())
    cur = conn.cursor()
    
    # Get integer league ID
    cur.execute("SELECT id FROM leagues WHERE league_id = %s", (league_key,))
    result = cur.fetchone()
    if not result:
        print(f"❌ League {league_key} not found in database")
        return {'total_issues': 1}
    league_id = result[0]
    
    report = {
        'source_teams_not_in_db': [],
        'db_teams_not_in_source': [],
        'total_issues': 0
    }
    
    try:
        # Get all teams from database
        cur.execute("""
            SELECT team_name FROM teams WHERE league_id = %s
        """, (league_id,))
        
        db_teams = {row[0] for row in cur.fetchall()}
        
        # Find teams in source but not in database
        for team in source_teams:
            if team not in db_teams:
                report['source_teams_not_in_db'].append(team)
                report['total_issues'] += 1
        
        # Find teams in database but not in source
        for team in db_teams:
            if team not in source_teams:
                report['db_teams_not_in_source'].append(team)
                report['total_issues'] += 1
        
    finally:
        cur.close()
        conn.close()
    
    return report

def print_validation_report(league_key: str, source_report: Dict, db_report: Dict, import_report: Dict):
    """Print a comprehensive validation report."""
    print(f"\n{'='*80}")
    print(f"📊 ETL DATA QUALITY VALIDATION REPORT: {league_key.upper()}")
    print(f"{'='*80}")
    
    total_issues = source_report['total_issues'] + db_report['total_issues'] + import_report['total_issues']
    
    if total_issues == 0:
        print("✅ No data quality issues found!")
        return
    
    print(f"❌ Found {total_issues} data quality issues:")
    
    # Source data issues
    if source_report['total_issues'] > 0:
        print(f"\n📁 SOURCE DATA ISSUES ({source_report['total_issues']} issues):")
        
        if source_report['missing_teams']:
            print(f"  🔸 Teams missing from source files:")
            for team, missing_from in source_report['missing_teams']:
                print(f"    - '{team}' missing from {missing_from}")
        
        if source_report['inconsistent_teams']:
            print(f"  🔸 Inconsistent team naming:")
            for issue in source_report['inconsistent_teams']:
                print(f"    - {issue['normalized_key']}: {issue['variants']}")
    
    # Database issues
    if db_report['total_issues'] > 0:
        print(f"\n🗄️ DATABASE ISSUES ({db_report['total_issues']} issues):")
        
        if db_report['teams_without_clubs']:
            print(f"  🔸 Teams without clubs:")
            for team in db_report['teams_without_clubs']:
                print(f"    - ID {team['team_id']}: '{team['team_name']}'")
        
        if db_report['teams_without_series']:
            print(f"  🔸 Teams without series:")
            for team in db_report['teams_without_series']:
                print(f"    - ID {team['team_id']}: '{team['team_name']}'")
        
        if db_report['duplicate_team_names']:
            print(f"  🔸 Duplicate team names:")
            for dup in db_report['duplicate_team_names']:
                print(f"    - '{dup['team_name']}' appears {dup['count']} times")
        
        if db_report['club_normalization_issues']:
            print(f"  🔸 Club normalization issues:")
            for issue in db_report['club_normalization_issues']:
                print(f"    - '{issue['original_name']}' should be '{issue['normalized_name']}' ({issue['team_count']} teams)")
    
    # Import consistency issues
    if import_report['total_issues'] > 0:
        print(f"\n🔄 IMPORT CONSISTENCY ISSUES ({import_report['total_issues']} issues):")
        
        if import_report['source_teams_not_in_db']:
            print(f"  🔸 Teams in source data but not in database:")
            for team in import_report['source_teams_not_in_db']:
                print(f"    - '{team}'")
        
        if import_report['db_teams_not_in_source']:
            print(f"  🔸 Teams in database but not in source data:")
            for team in import_report['db_teams_not_in_source']:
                print(f"    - '{team}'")
    
    print(f"\n💡 RECOMMENDATIONS:")
    if source_report['total_issues'] > 0:
        print("  - Fix source data inconsistencies before importing")
    if db_report['total_issues'] > 0:
        print("  - Run database cleanup scripts to fix orphaned records")
    if import_report['total_issues'] > 0:
        print("  - Re-run import scripts to sync source data with database")
    
    print(f"\n{'='*80}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/validate_etl_data_quality.py <LEAGUE_KEY>")
        sys.exit(1)
    
    league_key = sys.argv[1].upper()
    
    # Get league ID
    from utils.league_utils import normalize_league_id
    league_id = normalize_league_id(league_key)
    
    if not league_id:
        print(f"❌ Invalid league key: {league_key}")
        sys.exit(1)
    
    print(f"🚀 Starting ETL data quality validation for {league_key} (ID: {league_id})...")
    
    # Run all validations
    source_report = validate_source_data_consistency(league_key)
    db_report = validate_database_consistency(league_key)
    import_report = validate_import_consistency(league_key)
    
    # Print comprehensive report
    print_validation_report(league_key, source_report, db_report, import_report)
    
    # Exit with error code if issues found
    total_issues = source_report['total_issues'] + db_report['total_issues'] + import_report['total_issues']
    if total_issues > 0:
        sys.exit(1)
    else:
        print("🎉 All validations passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()
