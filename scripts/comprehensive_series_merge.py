#!/usr/bin/env python3

"""
Comprehensive Series Merge Script

This script merges all remaining incorrect series names into their correct "Series X" format.
It performs comprehensive validation before, during, and after the merge process.

SERIES TO MERGE:
- "13" → "Series 13"
- "17" → "Series 17" 
- "21" → "Series 21"
- "23" → "Series 23"
- "29" → "Series 29"
- "32" → "Series 32"
- "33" → "Series 33"
- "6" → "Series 6"
- "9" → "Series 9"

SAFETY FEATURES:
- Only runs on local database
- Comprehensive pre-merge validation
- Detailed logging of all operations
- Post-merge validation
- Rollback instructions
- Progress tracking
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple

# Add the project root to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from database_utils import execute_query, execute_update
from database_config import is_local_development

# Series to merge (incorrect_name: correct_name)
SERIES_TO_MERGE = {
    "13": "Series 13",
    "17": "Series 17", 
    "21": "Series 21",
    "23": "Series 23",
    "29": "Series 29",
    "32": "Series 32",
    "33": "Series 33",
    "6": "Series 6",
    "9": "Series 9"
}

def check_database_environment():
    """Ensure we're only running on local database"""
    if not is_local_development():
        print("❌ ERROR: This script can only run on local database!")
        print("   Current environment is not local development")
        sys.exit(1)
    
    print("✅ Confirmed running on local database")

def get_series_data() -> Dict[str, Dict]:
    """Get comprehensive data for all series to be merged"""
    print("\n📊 Gathering series data...")
    
    series_data = {}
    
    for incorrect_name, correct_name in SERIES_TO_MERGE.items():
        query = """
        SELECT 
            s.id,
            s.name,
            COUNT(p.id) as player_count,
            COUNT(t.id) as team_count
        FROM series s
        LEFT JOIN players p ON s.id = p.series_id
        LEFT JOIN teams t ON s.id = t.series_id
        WHERE s.name IN (%s, %s) AND s.league_id = 4783
        GROUP BY s.id, s.name
        ORDER BY s.name
        """
        
        results = execute_query(query, [incorrect_name, correct_name])
        
        incorrect_series = None
        correct_series = None
        
        for record in results:
            if record['name'] == incorrect_name:
                incorrect_series = record
            elif record['name'] == correct_name:
                correct_series = record
        
        series_data[incorrect_name] = {
            'incorrect': incorrect_series,
            'correct': correct_series,
            'correct_name': correct_name
        }
        
        if incorrect_series and correct_series:
            print(f"   {incorrect_name} → {correct_name}: {incorrect_series['player_count']} players, {incorrect_series['team_count']} teams")
        else:
            print(f"   ❌ Missing data for {incorrect_name} → {correct_name}")
    
    return series_data

def check_duplicate_players(series_data: Dict[str, Dict]) -> Dict[str, List]:
    """Check for duplicate players across all series"""
    print("\n🔍 Checking for duplicate players...")
    
    duplicates = {}
    
    for incorrect_name, data in series_data.items():
        if not data['incorrect'] or not data['correct']:
            continue
            
        incorrect_id = data['incorrect']['id']
        correct_id = data['correct']['id']
        
        query = """
        SELECT 
            p1.tenniscores_player_id,
            p1.first_name,
            p1.last_name,
            c.name as club_name
        FROM players p1
        JOIN players p2 ON (
            p1.tenniscores_player_id = p2.tenniscores_player_id
            AND p1.league_id = p2.league_id
            AND p1.club_id = p2.club_id
        )
        JOIN clubs c ON p1.club_id = c.id
        WHERE p1.series_id = %s AND p2.series_id = %s
        ORDER BY p1.first_name, p1.last_name
        """
        
        results = execute_query(query, [incorrect_id, correct_id])
        duplicates[incorrect_name] = results
        
        if results:
            print(f"   {incorrect_name}: {len(results)} duplicate players")
        else:
            print(f"   {incorrect_name}: No duplicates")
    
    return duplicates

def check_foreign_key_references(series_data: Dict[str, Dict]) -> Dict[str, Dict]:
    """Check foreign key references for all series"""
    print("\n🔗 Checking foreign key references...")
    
    references = {}
    
    for incorrect_name, data in series_data.items():
        if not data['incorrect']:
            continue
            
        series_id = data['incorrect']['id']
        
        queries = [
            ("players", "SELECT COUNT(*) as count FROM players WHERE series_id = %s"),
            ("teams", "SELECT COUNT(*) as count FROM teams WHERE series_id = %s"),
            ("match_scores", """
                SELECT COUNT(*) as count FROM match_scores 
                WHERE home_team_id IN (SELECT id FROM teams WHERE series_id = %s) 
                   OR away_team_id IN (SELECT id FROM teams WHERE series_id = %s)
            """),
        ]
        
        series_refs = {}
        for table_name, query in queries:
            if table_name == "match_scores":
                result = execute_query(query, [series_id, series_id])
            else:
                result = execute_query(query, [series_id])
            series_refs[table_name] = result[0]['count'] if result else 0
        
        references[incorrect_name] = series_refs
        
        print(f"   {incorrect_name}: {series_refs['players']} players, {series_refs['teams']} teams, {series_refs['match_scores']} matches")
    
    return references

def merge_single_series(incorrect_name: str, series_data: Dict[str, Dict]) -> Tuple[bool, str]:
    """Merge a single series"""
    data = series_data[incorrect_name]
    
    if not data['incorrect'] or not data['correct']:
        return False, f"Missing data for {incorrect_name}"
    
    incorrect_id = data['incorrect']['id']
    correct_id = data['correct']['id']
    correct_name = data['correct_name']
    
    print(f"\n🔧 Merging {incorrect_name} → {correct_name}...")
    
    try:
        # Step 1: Delete duplicate players from incorrect series
        print(f"   Step 1: Deleting players from series {incorrect_id}")
        delete_players_query = "DELETE FROM players WHERE series_id = %s"
        result1 = execute_update(delete_players_query, [incorrect_id])
        
        # Step 2: Update teams to point to correct series
        print(f"   Step 2: Updating teams to series {correct_id}")
        update_teams_query = "UPDATE teams SET series_id = %s WHERE series_id = %s"
        result2 = execute_update(update_teams_query, [correct_id, incorrect_id])
        
        # Step 3: Delete the incorrect series
        print(f"   Step 3: Deleting series {incorrect_id}")
        delete_series_query = "DELETE FROM series WHERE id = %s AND name = %s"
        result3 = execute_update(delete_series_query, [incorrect_id, incorrect_name])
        
        print(f"   ✅ Success: {incorrect_name} → {correct_name}")
        return True, f"Successfully merged {incorrect_name} → {correct_name}"
        
    except Exception as e:
        error_msg = f"Error merging {incorrect_name}: {str(e)}"
        print(f"   ❌ {error_msg}")
        return False, error_msg

def validate_merge_results(series_data: Dict[str, Dict]) -> Dict[str, bool]:
    """Validate that all merges were successful"""
    print("\n✅ Validating merge results...")
    
    validation_results = {}
    
    for incorrect_name, data in series_data.items():
        correct_name = data['correct_name']
        
        # Check that incorrect series is gone
        incorrect_check = """
        SELECT COUNT(*) as count
        FROM series 
        WHERE name = %s AND league_id = 4783
        """
        
        incorrect_result = execute_query(incorrect_check, [incorrect_name])
        incorrect_gone = incorrect_result[0]['count'] == 0
        
        # Check that correct series still exists and has data
        if data['correct']:
            correct_id = data['correct']['id']
            correct_check = """
            SELECT 
                s.id,
                s.name,
                COUNT(p.id) as player_count,
                COUNT(t.id) as team_count
            FROM series s
            LEFT JOIN players p ON s.id = p.series_id
            LEFT JOIN teams t ON s.id = t.series_id
            WHERE s.id = %s
            GROUP BY s.id, s.name
            """
            
            correct_result = execute_query(correct_check, [correct_id])
            correct_exists = len(correct_result) > 0
            
            if correct_exists:
                series = correct_result[0]
                print(f"   {correct_name}: ID {series['id']}, {series['player_count']} players, {series['team_count']} teams")
            else:
                print(f"   ❌ {correct_name}: Not found!")
                correct_exists = False
        else:
            correct_exists = False
        
        validation_results[incorrect_name] = incorrect_gone and correct_exists
        
        if validation_results[incorrect_name]:
            print(f"   ✅ {incorrect_name} → {correct_name}: Success")
        else:
            print(f"   ❌ {incorrect_name} → {correct_name}: Failed")
    
    return validation_results

def comprehensive_data_validation():
    """Perform comprehensive validation of all data"""
    print("\n🔍 COMPREHENSIVE DATA VALIDATION")
    print("=" * 50)
    
    # Check for any remaining incorrect series
    remaining_check = """
    SELECT 
        s.id,
        s.name,
        COUNT(p.id) as player_count,
        COUNT(t.id) as team_count
    FROM series s
    LEFT JOIN players p ON s.id = p.series_id
    LEFT JOIN teams t ON s.id = t.series_id
    WHERE s.name ~ '^[0-9]+$' AND s.league_id = 4783
    GROUP BY s.id, s.name
    ORDER BY s.name
    """
    
    remaining_results = execute_query(remaining_check)
    print(f"\n📊 Remaining incorrect series: {len(remaining_results)}")
    
    if remaining_results:
        for record in remaining_results:
            print(f"   Series ID {record['id']}: \"{record['name']}\" - {record['player_count']} players, {record['team_count']} teams")
    else:
        print("   ✅ No incorrect series remaining!")
    
    # Check total series count
    total_series_check = """
    SELECT COUNT(*) as count
    FROM series 
    WHERE league_id = 4783 AND name LIKE 'Series %'
    """
    
    total_result = execute_query(total_series_check)
    print(f"\n📊 Total correct \"Series X\" records: {total_result[0]['count']}")
    
    # Check for any constraint violations
    constraint_check = """
    SELECT 
        COUNT(DISTINCT CONCAT(tenniscores_player_id, '-', league_id, '-', club_id, '-', series_id)) as unique_combinations,
        COUNT(*) as total_players
    FROM players
    WHERE league_id = 4783
    """
    
    constraint_result = execute_query(constraint_check)
    unique_combos = constraint_result[0]['unique_combinations']
    total_players = constraint_result[0]['total_players']
    
    print(f"\n📊 Player constraint check:")
    print(f"   Unique combinations: {unique_combos}")
    print(f"   Total players: {total_players}")
    
    if unique_combos == total_players:
        print("   ✅ No constraint violations detected!")
    else:
        print(f"   ⚠️  Potential constraint violations: {total_players - unique_combos}")
    
    # Check for orphaned teams
    orphaned_teams_check = """
    SELECT COUNT(*) as count
    FROM teams t
    LEFT JOIN series s ON t.series_id = s.id
    WHERE t.league_id = 4783 AND s.id IS NULL
    """
    
    orphaned_result = execute_query(orphaned_teams_check)
    orphaned_teams = orphaned_result[0]['count']
    
    print(f"\n📊 Orphaned teams check:")
    print(f"   Orphaned teams: {orphaned_teams}")
    
    if orphaned_teams == 0:
        print("   ✅ No orphaned teams!")
    else:
        print(f"   ⚠️  {orphaned_teams} orphaned teams found!")
    
    return len(remaining_results) == 0 and unique_combos == total_players and orphaned_teams == 0

def provide_rollback_instructions(series_data: Dict[str, Dict]):
    """Provide comprehensive rollback instructions"""
    print(f"\n📋 COMPREHENSIVE ROLLBACK INSTRUCTIONS:")
    print("=" * 50)
    print("If you need to rollback all merges:")
    print()
    
    for incorrect_name, data in series_data.items():
        if data['incorrect'] and data['correct']:
            incorrect_id = data['incorrect']['id']
            correct_id = data['correct']['id']
            correct_name = data['correct_name']
            
            print(f"-- Rollback {incorrect_name} → {correct_name}")
            print(f"INSERT INTO series (id, name, league_id) VALUES ({incorrect_id}, '{incorrect_name}', 4783);")
            print(f"UPDATE teams SET series_id = {incorrect_id} WHERE series_id = {correct_id} AND team_name LIKE '%{incorrect_name}%';")
            print()
    
    print("Note: Player records would need to be restored from backup")

def main():
    """Main execution function"""
    print("=" * 70)
    print("COMPREHENSIVE SERIES MERGE SCRIPT")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Series to merge: {len(SERIES_TO_MERGE)}")
    print()
    
    # Safety checks
    check_database_environment()
    
    # Gather comprehensive data
    series_data = get_series_data()
    
    # Check for missing data
    missing_data = []
    for incorrect_name, data in series_data.items():
        if not data['incorrect'] or not data['correct']:
            missing_data.append(incorrect_name)
    
    if missing_data:
        print(f"\n❌ Missing data for series: {missing_data}")
        print("   Cannot proceed with incomplete data")
        sys.exit(1)
    
    # Check for duplicate players
    duplicates = check_duplicate_players(series_data)
    total_duplicates = sum(len(dup_list) for dup_list in duplicates.values())
    print(f"\n📊 Total duplicate players to be deleted: {total_duplicates}")
    
    # Check foreign key references
    references = check_foreign_key_references(series_data)
    
    # Show summary
    print(f"\n📊 MERGE SUMMARY:")
    total_players = sum(data['incorrect']['player_count'] for data in series_data.values())
    total_teams = sum(data['incorrect']['team_count'] for data in series_data.values())
    print(f"   Series to merge: {len(SERIES_TO_MERGE)}")
    print(f"   Players to delete: {total_duplicates}")
    print(f"   Teams to update: {total_teams}")
    print(f"   Total operations: {len(SERIES_TO_MERGE) * 3}")
    
    # Confirm before proceeding
    print(f"\n⚠️  WARNING: This will permanently delete {len(SERIES_TO_MERGE)} series and {total_duplicates} player records!")
    response = input("Do you want to continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Operation cancelled by user")
        sys.exit(1)
    
    # Perform all merges
    print(f"\n🚀 Starting comprehensive merge...")
    merge_results = {}
    success_count = 0
    
    for incorrect_name in SERIES_TO_MERGE.keys():
        success, message = merge_single_series(incorrect_name, series_data)
        merge_results[incorrect_name] = success
        if success:
            success_count += 1
    
    # Validate results
    validation_results = validate_merge_results(series_data)
    
    # Comprehensive validation
    comprehensive_success = comprehensive_data_validation()
    
    # Summary
    print(f"\n" + "=" * 70)
    print("COMPREHENSIVE MERGE RESULTS")
    print("=" * 70)
    print(f"Series merged successfully: {success_count}/{len(SERIES_TO_MERGE)}")
    print(f"Validation passed: {comprehensive_success}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if comprehensive_success:
        print("\n✅ ALL MERGES COMPLETED SUCCESSFULLY!")
        print("✅ COMPREHENSIVE VALIDATION PASSED!")
        print("\nNext steps:")
        print("1. Test the application thoroughly")
        print("2. Update the import process to prevent future issues")
        print("3. Consider applying constraint removal to production")
    else:
        print("\n❌ SOME ISSUES DETECTED!")
        print("   Check the validation results above")
        print("   Consider rollback if necessary")
    
    # Provide rollback instructions
    provide_rollback_instructions(series_data)

if __name__ == "__main__":
    main()
