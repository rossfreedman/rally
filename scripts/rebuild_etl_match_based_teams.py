#!/usr/bin/env python3
"""
Rebuild ETL Process with Match-Based Team Assignment - Phase 3 (Long-term)

This script creates a new ETL process that assigns teams based on actual match 
participation rather than complex JOIN logic, preventing future team assignment issues.
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_config import get_db
from database_utils import execute_query, execute_query_one

def create_match_based_team_assignment_function():
    """Create a stored procedure for match-based team assignment"""
    print("=" * 80)
    print("PHASE 3: REBUILDING ETL WITH MATCH-BASED TEAM ASSIGNMENT")
    print("=" * 80)
    
    print("1. Creating match-based team assignment function...")
    
    # Create a PostgreSQL function for match-based team assignment
    function_sql = """
    CREATE OR REPLACE FUNCTION assign_player_teams_from_matches()
    RETURNS TABLE(
        player_id VARCHAR,
        player_name VARCHAR,
        old_team VARCHAR,
        new_team VARCHAR,
        match_count INTEGER,
        assignment_confidence VARCHAR
    )
    LANGUAGE plpgsql
    AS $$
    BEGIN
        RETURN QUERY
        WITH player_match_teams AS (
            SELECT 
                CASE 
                    WHEN ms.home_player_1_id = p.tenniscores_player_id THEN ms.home_team
                    WHEN ms.home_player_2_id = p.tenniscores_player_id THEN ms.home_team
                    WHEN ms.away_player_1_id = p.tenniscores_player_id THEN ms.away_team
                    WHEN ms.away_player_2_id = p.tenniscores_player_id THEN ms.away_team
                END as match_team,
                p.tenniscores_player_id,
                p.first_name || ' ' || p.last_name as full_name,
                t.team_name as current_team,
                COUNT(*) as team_match_count
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            JOIN match_scores ms ON (
                ms.home_player_1_id = p.tenniscores_player_id OR
                ms.home_player_2_id = p.tenniscores_player_id OR
                ms.away_player_1_id = p.tenniscores_player_id OR
                ms.away_player_2_id = p.tenniscores_player_id
            )
            WHERE p.is_active = TRUE
            GROUP BY p.tenniscores_player_id, full_name, current_team, match_team
        ),
        player_primary_teams AS (
            SELECT 
                tenniscores_player_id,
                full_name,
                current_team,
                match_team as primary_team,
                team_match_count,
                SUM(team_match_count) OVER (PARTITION BY tenniscores_player_id) as total_matches,
                ROW_NUMBER() OVER (
                    PARTITION BY tenniscores_player_id 
                    ORDER BY team_match_count DESC
                ) as team_rank
            FROM player_match_teams
        ),
        final_assignments AS (
            SELECT 
                tenniscores_player_id,
                full_name,
                current_team,
                primary_team,
                team_match_count,
                total_matches,
                CASE 
                    WHEN team_match_count::FLOAT / total_matches > 0.8 THEN 'HIGH'
                    WHEN team_match_count::FLOAT / total_matches > 0.6 THEN 'MEDIUM'
                    WHEN team_match_count::FLOAT / total_matches > 0.4 THEN 'LOW'
                    ELSE 'VERY_LOW'
                END as confidence
            FROM player_primary_teams
            WHERE team_rank = 1
        )
        SELECT 
            fa.tenniscores_player_id,
            fa.full_name,
            COALESCE(fa.current_team, 'UNASSIGNED'),
            fa.primary_team,
            fa.team_match_count,
            fa.confidence
        FROM final_assignments fa
        WHERE fa.current_team IS NULL 
        OR fa.current_team != fa.primary_team
        ORDER BY fa.team_match_count DESC;
    END;
    $$;
    """
    
    try:
        execute_query(function_sql)
        print("✅ Match-based team assignment function created successfully")
    except Exception as e:
        print(f"❌ Failed to create function: {e}")
        return False
    
    return True

def create_etl_validation_function():
    """Create a function to validate team assignments after ETL"""
    print("2. Creating ETL validation function...")
    
    validation_function_sql = """
    CREATE OR REPLACE FUNCTION validate_team_assignments()
    RETURNS TABLE(
        validation_type VARCHAR,
        issue_count INTEGER,
        description VARCHAR
    )
    LANGUAGE plpgsql
    AS $$
    BEGIN
        -- Check for players with no team assignment who have matches
        RETURN QUERY
        SELECT 
            'UNASSIGNED_WITH_MATCHES'::VARCHAR,
            COUNT(*)::INTEGER,
            'Players with matches but no team assignment'::VARCHAR
        FROM players p
        WHERE p.team_id IS NULL 
        AND p.is_active = TRUE
        AND EXISTS (
            SELECT 1 FROM match_scores ms 
            WHERE ms.home_player_1_id = p.tenniscores_player_id
            OR ms.home_player_2_id = p.tenniscores_player_id
            OR ms.away_player_1_id = p.tenniscores_player_id
            OR ms.away_player_2_id = p.tenniscores_player_id
        );
        
        -- Check for mismatched team assignments
        RETURN QUERY
        WITH player_match_teams AS (
            SELECT 
                p.tenniscores_player_id,
                CASE 
                    WHEN ms.home_player_1_id = p.tenniscores_player_id THEN ms.home_team
                    WHEN ms.home_player_2_id = p.tenniscores_player_id THEN ms.home_team
                    WHEN ms.away_player_1_id = p.tenniscores_player_id THEN ms.away_team
                    WHEN ms.away_player_2_id = p.tenniscores_player_id THEN ms.away_team
                END as match_team,
                t.team_name as assigned_team,
                COUNT(*) as match_count
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            JOIN match_scores ms ON (
                ms.home_player_1_id = p.tenniscores_player_id OR
                ms.home_player_2_id = p.tenniscores_player_id OR
                ms.away_player_1_id = p.tenniscores_player_id OR
                ms.away_player_2_id = p.tenniscores_player_id
            )
            WHERE p.is_active = TRUE AND t.team_name IS NOT NULL
            GROUP BY p.tenniscores_player_id, assigned_team, match_team
        ),
        mismatched AS (
            SELECT tenniscores_player_id
            FROM player_match_teams
            WHERE assigned_team != match_team
            GROUP BY tenniscores_player_id
        )
        SELECT 
            'MISMATCHED_ASSIGNMENTS'::VARCHAR,
            COUNT(*)::INTEGER,
            'Players assigned to wrong team based on matches'::VARCHAR
        FROM mismatched;
        
        -- Check for empty teams
        RETURN QUERY
        SELECT 
            'EMPTY_TEAMS'::VARCHAR,
            COUNT(*)::INTEGER,
            'Teams with no active players'::VARCHAR
        FROM teams t
        WHERE NOT EXISTS (
            SELECT 1 FROM players p 
            WHERE p.team_id = t.id AND p.is_active = TRUE
        );
    END;
    $$;
    """
    
    try:
        execute_query(validation_function_sql)
        print("✅ ETL validation function created successfully")
    except Exception as e:
        print(f"❌ Failed to create validation function: {e}")
        return False
    
    return True

def create_improved_etl_script():
    """Create an improved ETL script template"""
    print("3. Creating improved ETL script template...")
    
    etl_script_content = '''#!/usr/bin/env python3
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
'''
    
    try:
        with open("data/etl/database_import/improved_import_with_match_based_teams.py", "w") as f:
            f.write(etl_script_content)
        print("✅ Improved ETL script template created")
    except Exception as e:
        print(f"❌ Failed to create ETL script: {e}")
        return False
    
    return True

def test_new_functions():
    """Test the new functions to ensure they work correctly"""
    print("4. Testing new functions...")
    
    # Test the assignment function
    print("   Testing assign_player_teams_from_matches()...")
    try:
        test_results = execute_query("SELECT * FROM assign_player_teams_from_matches() LIMIT 5")
        print(f"   ✅ Function works - found {len(test_results)} potential assignments")
        
        if test_results:
            print("   Sample results:")
            for i, result in enumerate(test_results[:3]):
                print(f"     {i+1}. {result['player_name']}: {result['old_team']} → {result['new_team']} ({result['match_count']} matches, {result['assignment_confidence']} confidence)")
    
    except Exception as e:
        print(f"   ❌ Assignment function test failed: {e}")
        return False
    
    # Test the validation function
    print("   Testing validate_team_assignments()...")
    try:
        validation_results = execute_query("SELECT * FROM validate_team_assignments()")
        print(f"   ✅ Validation function works - found {len(validation_results)} validation checks")
        
        for result in validation_results:
            print(f"     {result['validation_type']}: {result['issue_count']} issues")
    
    except Exception as e:
        print(f"   ❌ Validation function test failed: {e}")
        return False
    
    return True

def create_maintenance_scripts():
    """Create ongoing maintenance scripts"""
    print("5. Creating maintenance scripts...")
    
    # Daily team validation script
    daily_script_content = '''#!/usr/bin/env python3
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
        print(f"\\nAuto-fixing {len(high_confidence_assignments)} high-confidence unassigned players...")
        
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
'''
    
    try:
        with open("scripts/daily_team_validation.py", "w") as f:
            f.write(daily_script_content)
        print("✅ Daily validation script created")
    except Exception as e:
        print(f"❌ Failed to create daily script: {e}")
        return False
    
    return True

def rebuild_etl_process():
    """Execute the complete ETL rebuild process"""
    print("Starting ETL Process Rebuild...")
    
    success = True
    
    # Step 1: Create database functions
    if not create_match_based_team_assignment_function():
        success = False
    
    if not create_etl_validation_function():
        success = False
    
    # Step 2: Create improved ETL script
    if not create_improved_etl_script():
        success = False
    
    # Step 3: Test the functions
    if not test_new_functions():
        success = False
    
    # Step 4: Create maintenance scripts
    if not create_maintenance_scripts():
        success = False
    
    return success

if __name__ == "__main__":
    print("Starting Phase 3: Rebuild ETL Process with Match-Based Team Assignment")
    print("This creates infrastructure to prevent future team assignment issues\\n")
    
    success = rebuild_etl_process()
    
    if success:
        print(f"\\n🎉 PHASE 3 COMPLETED SUCCESSFULLY!")
        print(f"   Created match-based team assignment functions")
        print(f"   Created improved ETL script template")
        print(f"   Created validation and maintenance scripts")
        print(f"   Future ETL runs will use match participation for team assignment")
        print(f"\\n📝 Next Steps:")
        print(f"   1. Update existing ETL scripts to use the new functions")
        print(f"   2. Set up daily_team_validation.py as a scheduled job")
        print(f"   3. Test the new process with a small data import")
    else:
        print(f"\\n❌ PHASE 3 FAILED")
        print(f"   Please review the errors above and try again.") 