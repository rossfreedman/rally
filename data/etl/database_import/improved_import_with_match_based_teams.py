#!/usr/bin/env python3
"""
Improved ETL Process with Match-Based Team Assignment

This script replaces the complex JOIN-based team assignment with
a match-participation-based approach that is more reliable.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db
from database_utils import execute_query, execute_query_one

def improved_player_import_with_team_assignment():
    """Import players with match-based team assignment"""
    print("Starting improved player import with match-based team assignment...")
    
    # Step 1: Import basic player data (without team assignment)
    print("1. Importing basic player data...")
    # ... existing player import logic here ...
    
    # Step 2: Use match-based team assignment
    print("2. Assigning teams based on match participation...")
    
    try:
        # Use our new function to get team assignments
        assignments = execute_query("SELECT * FROM assign_player_teams_from_matches()")
        
        successful_assignments = 0
        for assignment in assignments:
            try:
                # Find target team ID
                target_team = execute_query_one(
                    "SELECT id FROM teams WHERE team_name = %s LIMIT 1",
                    [assignment['new_team']]
                )
                
                if target_team:
                    # Update player's team assignment
                    execute_query(
                        "UPDATE players SET team_id = %s WHERE tenniscores_player_id = %s",
                        [target_team['id'], assignment['player_id']]
                    )
                    successful_assignments += 1
                    
            except Exception as e:
                print(f"Failed to assign {assignment['player_name']}: {e}")
        
        print(f"Successfully assigned teams to {successful_assignments} players")
        
    except Exception as e:
        print(f"Team assignment failed: {e}")
    
    # Step 3: Validate the results
    print("3. Validating team assignments...")
    
    try:
        validation_results = execute_query("SELECT * FROM validate_team_assignments()")
        
        for result in validation_results:
            if result['issue_count'] > 0:
                print(f"⚠️  {result['validation_type']}: {result['issue_count']} issues")
                print(f"   {result['description']}")
            else:
                print(f"✅ {result['validation_type']}: No issues found")
                
    except Exception as e:
        print(f"Validation failed: {e}")
    
    print("Improved ETL process completed!")

if __name__ == "__main__":
    improved_player_import_with_team_assignment()
