#!/usr/bin/env python3

import sys
import json
sys.path.append('.')

from data.etl.database_import.import_all_jsons_to_database import ComprehensiveETL
from database_utils import execute_query, execute_query_one

def debug_team_extraction():
    """Debug team extraction and league assignment"""
    print("🔍 DEBUGGING TEAM EXTRACTION AND LEAGUE ASSIGNMENT")
    print("=" * 60)
    
    # Create ETL instance
    etl = ComprehensiveETL()
    
    # Load JSON files
    print("📂 Loading JSON files...")
    series_stats_data = etl.load_json_file('series_stats.json')
    schedules_data = etl.load_json_file('schedules.json')
    
    # Extract teams
    print("\n🏗️  Extracting teams...")
    teams_data = etl.extract_teams(series_stats_data, schedules_data)
    
    # Analyze by league
    teams_by_league = {}
    for team in teams_data:
        league_id = team['league_id']
        if league_id not in teams_by_league:
            teams_by_league[league_id] = []
        teams_by_league[league_id].append(team)
    
    print(f"\n📊 EXTRACTED TEAMS SUMMARY:")
    for league_id, teams in teams_by_league.items():
        print(f"  {league_id}: {len(teams)} teams")
        
        # Show sample teams for each league
        sample_teams = teams[:3]
        for team in sample_teams:
            print(f"    - {team['team_name']} (Club: {team['club_name']}, Series: {team['series_name']})")
        if len(teams) > 3:
            print(f"    ... and {len(teams) - 3} more teams")
    
    # Check current database state
    print(f"\n🗄️  CURRENT DATABASE STATE:")
    leagues = execute_query("SELECT id, league_id, league_name FROM leagues ORDER BY league_name")
    for league in leagues:
        league_db_id = league['id']
        league_id = league['league_id']
        league_name = league['league_name']
        
        # Count teams in this league
        team_count = execute_query_one(
            "SELECT COUNT(*) as count FROM teams WHERE league_id = %s", 
            [league_db_id]
        )['count']
        
        print(f"  {league_name} (league_id: {league_id}, db_id: {league_db_id}): {team_count} teams")
    
    # Check for potential lookup issues
    print(f"\n🔍 CHECKING LEAGUE LOOKUP LOGIC:")
    for league_id in teams_by_league.keys():
        print(f"\n  Testing lookup for league_id: '{league_id}'")
        
        # Test the exact query used in import_teams
        league_lookup = execute_query_one(
            "SELECT id, league_name FROM leagues WHERE league_id = %s", 
            [league_id]
        )
        
        if league_lookup:
            print(f"    ✅ Found: {league_lookup['league_name']} (db_id: {league_lookup['id']})")
        else:
            print(f"    ❌ Not found! Available league_ids:")
            all_leagues = execute_query("SELECT league_id FROM leagues")
            for l in all_leagues:
                print(f"      - '{l['league_id']}'")
    
    # Test sample team creation logic
    print(f"\n🧪 TESTING SAMPLE TEAM CREATION:")
    if 'NSTF' in teams_by_league:
        sample_team = teams_by_league['NSTF'][0]
        club_name = sample_team['club_name']
        series_name = sample_team['series_name']
        league_id = sample_team['league_id']
        
        print(f"  Sample team: {sample_team['team_name']}")
        print(f"  Club: '{club_name}', Series: '{series_name}', League: '{league_id}'")
        
        # Test the exact lookup query from import_teams
        refs_query = """
            SELECT c.id, s.id, l.id 
            FROM clubs c, series s, leagues l
            WHERE c.name = %s AND s.name = %s AND l.league_id = %s
        """
        refs = execute_query_one(refs_query, (club_name, series_name, league_id))
        
        if refs:
            print(f"    ✅ References found: club_id={refs['id']}, series_id={refs['id_1']}, league_db_id={refs['id_2']}")
        else:
            print(f"    ❌ References NOT found!")
            
            # Check each component
            club_check = execute_query_one("SELECT id FROM clubs WHERE name = %s", [club_name])
            series_check = execute_query_one("SELECT id FROM series WHERE name = %s", [series_name])
            league_check = execute_query_one("SELECT id FROM leagues WHERE league_id = %s", [league_id])
            
            print(f"      Club '{club_name}' exists: {'✅' if club_check else '❌'}")
            print(f"      Series '{series_name}' exists: {'✅' if series_check else '❌'}")
            print(f"      League '{league_id}' exists: {'✅' if league_check else '❌'}")

if __name__ == '__main__':
    debug_team_extraction() 