#!/usr/bin/env python3
"""
Daily Team Assignment Validation

Run this script daily to check for team assignment issues
and automatically fix simple cases.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db
from database_utils import execute_query, execute_query_one

def daily_team_validation():
    """Run daily validation and fix simple issues"""
    print("Running daily team assignment validation...")
    
    # Get validation results
    issues = execute_query("SELECT * FROM validate_team_assignments()")
    
    total_issues = sum(issue['issue_count'] for issue in issues)
    
    if total_issues == 0:
        print("✅ No team assignment issues found!")
        return
    
    print(f"Found {total_issues} total issues:")
    for issue in issues:
        print(f"  {issue['validation_type']}: {issue['issue_count']}")
    
    # Auto-fix unassigned players with high-confidence matches
    high_confidence_assignments = execute_query("""
        SELECT * FROM assign_player_teams_from_matches() 
        WHERE assignment_confidence = 'HIGH' AND old_team = 'UNASSIGNED'
        LIMIT 50
    """)
    
    if high_confidence_assignments:
        print(f"\nAuto-fixing {len(high_confidence_assignments)} high-confidence unassigned players...")
        
        for assignment in high_confidence_assignments:
            try:
                target_team = execute_query_one(
                    "SELECT id FROM teams WHERE team_name = %s LIMIT 1",
                    [assignment['new_team']]
                )
                
                if target_team:
                    execute_query(
                        "UPDATE players SET team_id = %s WHERE tenniscores_player_id = %s",
                        [target_team['id'], assignment['player_id']]
                    )
                    print(f"  ✅ Assigned {assignment['player_name']} to {assignment['new_team']}")
                    
            except Exception as e:
                print(f"  ❌ Failed to assign {assignment['player_name']}: {e}")

if __name__ == "__main__":
    daily_team_validation()
